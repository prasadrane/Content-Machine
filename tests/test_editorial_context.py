"""Tests for centralized editorial context provider and council writer context injection."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from content_machine.config import AppConfig, ModelsConfig, ThresholdsConfig
from content_machine.council.loop import run_council
from content_machine.knowledge.provider import (
    get_editorial_context,
    get_governed_rules,
    get_style_guide,
    get_voice_guide,
)
from content_machine.schemas import CouncilScores
from content_machine.storage.db import connect


def make_scores(v: float, verdict="revise", actions=("tighten the hook",)) -> CouncilScores:
    return CouncilScores(
        narrative=v, velocity=v, depth=v, slop_purity=v,
        threshold_met=v >= 9.0, verdict=verdict, required_actions=list(actions),
    )


class FakeCouncilRouter:
    def __init__(self, judge_scores: list[CouncilScores], writer_responses: list[str]):
        self.judge_scores = list(judge_scores)
        self.writer_responses = list(writer_responses)
        self.judge_calls: list[str] = []
        self.writer_calls: list[str] = []

    def complete(self, model_layer, prompt, *, system=None, schema=None):
        if schema is CouncilScores:
            self.judge_calls.append(prompt)
            return self.judge_scores.pop(0) if self.judge_scores else make_scores(9.5, "pass")
        self.writer_calls.append(prompt)
        return self.writer_responses.pop(0) if self.writer_responses else "revised draft"


class TestEditorialContextProvider(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="cm_test_knowledge_")
        os.environ["CONTENT_MACHINE_HOME"] = self.tmp_dir

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_get_style_guide_returns_golden_references_and_rules(self):
        style = get_style_guide(home_root=Path(self.tmp_dir))
        self.assertIn("Golden Reference Post #1", style)
        self.assertIn("Golden Reference Post #2", style)
        self.assertIn("Claude Code", style)
        self.assertIn("Aphorism Density Cap", style)
        self.assertIn("Ban Rhetorical Contrast Crutches", style)

    def test_get_voice_guide_returns_persona_and_invariants(self):
        voice = get_voice_guide(home_root=Path(self.tmp_dir))
        self.assertIn("Prasad Rane", voice)
        self.assertIn("Zero Company Attribution", voice)
        self.assertIn("No False Corporate Employment", voice)
        self.assertIn("Conversational Practitioner Field Notes", voice)

    def test_get_governed_rules_extracts_rules_and_syncs_to_db(self):
        conn = connect(":memory:")
        rules = get_governed_rules(conn=conn, home_root=Path(self.tmp_dir))
        self.assertGreaterEqual(len(rules), 10)
        self.assertTrue(any("Rule 1" in r for r in rules))
        self.assertTrue(any("Rule 9" in r or "Concrete Technical Specificity" in r for r in rules))
        self.assertTrue(any("Rule 10" in r or "Aphorism Density Cap" in r for r in rules))
        self.assertTrue(any("Rule 14" in r or "Natural Conversational Closers" in r for r in rules))

        # Check that rules were synced into the SQLite lessons table
        db_rules = conn.execute("SELECT rule_text FROM lessons WHERE status='active'").fetchall()
        self.assertGreaterEqual(len(db_rules), 14)
        conn.close()

    def test_get_editorial_context_assembles_full_bundle(self):
        conn = connect(":memory:")
        ctx = get_editorial_context(conn=conn, home_root=Path(self.tmp_dir))
        self.assertIn("style_guide", ctx)
        self.assertIn("voice_guide", ctx)
        self.assertIn("active_rules", ctx)
        self.assertIn("style_section", ctx)
        self.assertIn("voice_section", ctx)
        self.assertIn("rules_section", ctx)

        self.assertIn("# Author Style Guide", ctx["style_section"])
        self.assertIn("# Author Voice & Persona Guide", ctx["voice_section"])
        self.assertIn("GOVERNED EDITORIAL RULES", ctx["rules_section"])
        conn.close()

    def test_council_writer_receives_full_style_voice_and_rules(self):
        conn = connect(":memory:")
        conn.execute(
            "INSERT INTO spikes(id, category, hook_thesis) VALUES (?, ?, ?)",
            ("spike-ctx-test", "engineering", "Testing context injection"),
        )
        conn.commit()

        slots = {"perell": "m1", "puri": "m2", "housel": "m3", "slop_allergist": "m4"}
        cfg = AppConfig(
            models=ModelsConfig(writer="wm", council=slots),
            thresholds=ThresholdsConfig(council_max_iterations=2),
        )

        judge_scores = [make_scores(6.0)] * 4 + [make_scores(9.5, "pass")] * 4
        router = FakeCouncilRouter(judge_scores, ["revised draft v2"])

        result = run_council(
            spike_id="spike-ctx-test",
            draft="Initial draft for council test.",
            cfg=cfg,
            router=router,
            conn=conn,
        )

        self.assertTrue(result.threshold_met)
        self.assertEqual(len(router.writer_calls), 1)

        writer_prompt = router.writer_calls[0]
        self.assertIn("# Author Style Guide", writer_prompt)
        self.assertIn("Golden Reference Post #1", writer_prompt)
        self.assertIn("# Author Voice & Persona Guide", writer_prompt)
        self.assertIn("Zero Company Attribution", writer_prompt)
        self.assertIn("GOVERNED EDITORIAL RULES", writer_prompt)
        self.assertIn("Aphorism Density Cap", writer_prompt)
        conn.close()


if __name__ == "__main__":
    unittest.main()
