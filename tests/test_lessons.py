"""Tests for Lessons Loop subsystem (plan v2 §6).

Covers:
- LessonsDiffer: extract declarative rules from draft-vs-published diff
- LessonsStore: append with conflict detection, provenance, decay, cap/merge
- Human-approval gate enforced (auto-append blocked)

All offline; DB uses :memory:.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.storage.db import connect


# ---------------------------------------------------------------------------
# LessonsDiffer tests
# ---------------------------------------------------------------------------

DRAFT = """\
The best leaders communicate clearly. Trust your team members. Work smarter, not harder.
Always be authentic. Leverage synergies for maximum impact.
"""

PUBLISHED = """\
In March 2022, I fired my best engineer. Here is what I learned.
The memo had one sentence. It named the person. It said why. Nothing else.
I sent it Tuesday. By Thursday, the team had moved on.
Specificity is mercy.
"""


class TestLessonsDiffer(unittest.TestCase):

    def _make_differ(self):
        from content_machine.lessons.differ import LessonsDiffer
        router = MagicMock()
        return LessonsDiffer(router=router, model="qwen3.8-flash")

    def test_differ_calls_router_with_both_texts(self):
        """Router prompt includes both the draft text and the published text."""
        differ = self._make_differ()
        differ.router.complete.return_value = MagicMock(
            rules=["Never open with abstract leadership wisdom."]
        )
        differ.extract(draft=DRAFT, published=PUBLISHED, project_id="proj-1")
        call_args = differ.router.complete.call_args
        prompt = call_args[1].get("prompt") or call_args[0][1]
        self.assertIn("smarter", prompt)   # something from draft
        self.assertIn("Specificity", prompt)  # something from published

    def test_differ_returns_list_of_rule_strings(self):
        """extract() returns a list of plain-string declarative rules."""
        differ = self._make_differ()
        differ.router.complete.return_value = MagicMock(
            rules=[
                "Open with a specific date and event, not a platitude.",
                "Use sentence-length as a pacing signal: short = impact.",
            ]
        )
        rules = differ.extract(draft=DRAFT, published=PUBLISHED, project_id="p1")
        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)
        self.assertIsInstance(rules[0], str)

    def test_differ_caps_rules_at_three(self):
        """extract() returns at most 3 rules per diff (plan v2 §6)."""
        differ = self._make_differ()
        differ.router.complete.return_value = MagicMock(
            rules=["r1", "r2", "r3", "r4", "r5"]
        )
        rules = differ.extract(draft=DRAFT, published=PUBLISHED, project_id="p1")
        self.assertLessEqual(len(rules), 3)

    def test_differ_uses_correct_schema(self):
        """Router is called with a Pydantic schema for structured rule extraction."""
        differ = self._make_differ()
        differ.router.complete.return_value = MagicMock(rules=[])
        differ.extract(draft=DRAFT, published=PUBLISHED, project_id="p1")
        call_args = differ.router.complete.call_args
        schema = call_args[1].get("schema")
        self.assertIsNotNone(schema)


# ---------------------------------------------------------------------------
# LessonsStore tests
# ---------------------------------------------------------------------------

class TestLessonsStore(unittest.TestCase):

    def _make_fake_embed_model(self):
        """Fast deterministic fake embedder: bag-of-word token hashes → L2-normalised."""
        import numpy as np

        class FakeEmbedder:
            DIM = 64

            def encode(self, text: str, normalize_embeddings: bool = True) -> np.ndarray:
                vec = np.zeros(self.DIM, dtype=np.float32)
                for word in text.lower().split():
                    idx = hash(word) % self.DIM
                    vec[idx] += 1.0
                norm = np.linalg.norm(vec)
                if norm > 0 and normalize_embeddings:
                    vec /= norm
                return vec

        return FakeEmbedder()

    def _make_store(self):
        from content_machine.lessons.store import LessonsStore
        conn = connect(":memory:")
        return LessonsStore(db_conn=conn, embed_model=self._make_fake_embed_model()), conn


    def test_propose_adds_rule_as_pending(self):
        """propose() inserts a rule with status='pending' (not 'active')."""
        store, conn = self._make_store()
        store.propose(rule="Open with a concrete date.", project_id="p1")
        row = conn.execute("SELECT status FROM lessons").fetchone()
        self.assertEqual(row["status"], "pending")

    def test_approve_makes_rule_active(self):
        """approve(rule_id) sets status='active' — the human approval gate."""
        store, conn = self._make_store()
        store.propose(rule="Use one-sentence paragraphs for impact.", project_id="p1")
        rule_id = conn.execute("SELECT id FROM lessons").fetchone()["id"]
        store.approve(rule_id)
        row = conn.execute("SELECT status FROM lessons WHERE id=?", (rule_id,)).fetchone()
        self.assertEqual(row["status"], "active")

    def test_propose_stores_provenance(self):
        """propose() persists the project_id as provenance on the row."""
        store, conn = self._make_store()
        store.propose(rule="End on the operational takeaway.", project_id="proj-42")
        row = conn.execute("SELECT provenance_project FROM lessons").fetchone()
        self.assertEqual(row["provenance_project"], "proj-42")

    def test_propose_detects_near_duplicate(self):
        """Proposing a semantically similar rule returns conflict signal."""
        store, conn = self._make_store()
        # First rule goes in cleanly
        rule_a = "End the post on the operational takeaway for the reader."
        store.propose(rule=rule_a, project_id="p1")
        rule_id = conn.execute("SELECT id FROM lessons").fetchone()["id"]
        store.approve(rule_id)

        # Near-duplicate: same key tokens, slightly reworded — fake embedder will
        # score this high because it shares most bag-of-words components.
        rule_b = "End the post on the operational takeaway for the reader always."
        result = store.propose(rule=rule_b, project_id="p2")
        self.assertTrue(result.is_conflict)


    def test_propose_no_conflict_for_distinct_rule(self):
        """Proposing a clearly different rule returns no conflict."""
        store, conn = self._make_store()
        store.propose(rule="Open with a concrete date.", project_id="p1")
        rule_id = conn.execute("SELECT id FROM lessons").fetchone()["id"]
        store.approve(rule_id)

        result = store.propose(
            rule="Use active voice in every sentence.", project_id="p2"
        )
        self.assertFalse(result.is_conflict)

    def test_active_rules_returns_only_active(self):
        """active_rules() returns only status='active' rules."""
        store, conn = self._make_store()
        store.propose(rule="Rule A", project_id="p1")
        store.propose(rule="Rule B", project_id="p2")
        id_a = conn.execute("SELECT id FROM lessons WHERE rule_text='Rule A'").fetchone()["id"]
        store.approve(id_a)

        active = store.active_rules()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["rule_text"], "Rule A")

    def test_reject_sets_status_rejected(self):
        """reject(rule_id) sets status='rejected' (operator vetoed it)."""
        store, conn = self._make_store()
        store.propose(rule="Bad rule.", project_id="p1")
        rule_id = conn.execute("SELECT id FROM lessons").fetchone()["id"]
        store.reject(rule_id)
        row = conn.execute("SELECT status FROM lessons WHERE id=?", (rule_id,)).fetchone()
        self.assertEqual(row["status"], "rejected")

    def test_hard_cap_enforced(self):
        """When active rule count reaches cap, propose() returns a merge_required signal."""
        store, _ = self._make_store()
        store.cap = 3  # override for test
        for i in range(3):
            store.propose(rule=f"Rule {i}", project_id="p")
            conn2 = store.db_conn
            rid = conn2.execute(
                "SELECT id FROM lessons WHERE rule_text=?", (f"Rule {i}",)
            ).fetchone()["id"]
            store.approve(rid)

        result = store.propose(rule="One more rule", project_id="p")
        self.assertTrue(result.merge_required)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestLessonsDiffer, TestLessonsStore]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)
