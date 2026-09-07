"""Tests for Oracle subsystem: IdeaScorer + OracleOrchestrator (plan v2 §2.2).

All offline; network + LLM calls are mocked.
Set CONTENT_MACHINE_LIVE=1 to run live smoke.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.schemas import IdeaScore
from content_machine.connectors.base import ConnectorItem, ConnectorResult

# ---------------------------------------------------------------------------
# Helpers — build a mock IdeaScore
# ---------------------------------------------------------------------------

def _score(composite: float = 8.5, generic: bool = False) -> IdeaScore:
    return IdeaScore(
        pov=8.0,
        lived_experience=8.0,
        specificity=8.0,
        counter_intuitive=7.0,
        generic_penalty_applied=generic,
        composite=composite,
        rationale="test rationale",
    )


def _make_item(title: str = "Test idea", idx: int = 0) -> ConnectorItem:
    return ConnectorItem(
        title=title,
        url=f"https://example.com/{idx}",
        body="A concrete story about something that happened to me on 2025-03-12.",
        source="rss",
        fetched_at=datetime.now(tz=timezone.utc),
        guid=f"guid-{idx}",
    )


# ---------------------------------------------------------------------------
# IdeaScorer tests
# ---------------------------------------------------------------------------

class TestIdeaScorer(unittest.TestCase):

    def _make_scorer(self):
        from content_machine.oracle.scorer import IdeaScorer
        router = MagicMock()
        return IdeaScorer(router=router, scanner_model="qwen3.8-flash", n_samples=3)

    def test_score_item_calls_router_n_times(self):
        """Scorer calls router.complete exactly n_samples times per item."""
        scorer = self._make_scorer()
        scorer.router.complete.return_value = _score(8.0)
        scorer.score_item(_make_item())
        self.assertEqual(scorer.router.complete.call_count, 3)

    def test_score_item_returns_median_composite(self):
        """score_item returns the median composite across all samples."""
        scorer = self._make_scorer()
        # Three samples: 7.0, 8.0, 9.0 → median 8.0
        scorer.router.complete.side_effect = [
            _score(7.0),
            _score(9.0),
            _score(8.0),
        ]
        result = scorer.score_item(_make_item())
        self.assertAlmostEqual(result.median_composite, 8.0)

    def test_score_item_records_all_samples(self):
        """All individual sample composites are stored for audit."""
        scorer = self._make_scorer()
        scorer.router.complete.side_effect = [_score(7.0), _score(8.5), _score(9.0)]
        result = scorer.score_item(_make_item())
        self.assertEqual(len(result.samples), 3)
        self.assertIn(7.0, [s.composite for s in result.samples])

    def test_score_item_pass_when_above_gate(self):
        """Verdict is 'pass' when median composite >= idea_gate."""
        scorer = self._make_scorer()
        scorer.router.complete.return_value = _score(8.5)  # gate default 8.0
        result = scorer.score_item(_make_item())
        self.assertEqual(result.verdict, "pass")

    def test_score_item_reject_when_below_gate_minus_margin(self):
        """Verdict is 'reject' when median composite < gate - margin."""
        scorer = self._make_scorer()
        # gate=8.0, margin=0.5 → reject < 7.5
        scorer.router.complete.return_value = _score(6.0)
        result = scorer.score_item(_make_item())
        self.assertEqual(result.verdict, "reject")

    def test_score_item_review_in_margin_band(self):
        """Verdict is 'review' when median is within ±margin of the gate."""
        scorer = self._make_scorer()
        # gate=8.0, margin=0.5 → review in [7.5, 8.0)
        scorer.router.complete.return_value = _score(7.7)
        result = scorer.score_item(_make_item())
        self.assertEqual(result.verdict, "review")

    def test_score_item_uses_idea_gate_and_margin_from_params(self):
        """gate and margin can be customised at construction time."""
        from content_machine.oracle.scorer import IdeaScorer
        router = MagicMock()
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1,
                            idea_gate=7.0, idea_margin=0.0)
        router.complete.return_value = _score(7.0)
        result = scorer.score_item(_make_item())
        self.assertEqual(result.verdict, "pass")

    def test_score_item_prompt_contains_item_title_and_body(self):
        """The prompt sent to the router includes the item title and body."""
        scorer = self._make_scorer()
        scorer.router.complete.return_value = _score(8.0)
        item = _make_item("My concrete idea")
        scorer.score_item(item)
        # Inspect the prompt argument in any call
        call_kwargs = scorer.router.complete.call_args_list[0]
        prompt = call_kwargs[1].get("prompt") or call_kwargs[0][1]
        self.assertIn("My concrete idea", prompt)

    def test_score_item_schema_is_idea_score(self):
        """Router is called with schema=IdeaScore so output is validated."""
        scorer = self._make_scorer()
        scorer.router.complete.return_value = _score(8.0)
        scorer.score_item(_make_item())
        call_kwargs = scorer.router.complete.call_args_list[0]
        schema = call_kwargs[1].get("schema") or (call_kwargs[0][3] if len(call_kwargs[0]) > 3 else None)
        self.assertIs(schema, IdeaScore)

    def test_score_prompt_incorporates_storytelling_pov_and_examples(self):
        """The scoring rubric includes storytelling elements, opinionated POV, and concrete examples."""
        scorer = self._make_scorer()
        scorer.router.complete.return_value = _score(8.0)
        scorer.score_item(_make_item("Testing Rubric Dimensions"))
        call_kwargs = scorer.router.complete.call_args_list[0]
        prompt = call_kwargs[1].get("prompt") or call_kwargs[0][1]

        self.assertIn("personal anecdote or specific narrative", prompt)
        self.assertIn("opinionated stance rather than neutral information", prompt)
        self.assertIn("concrete details, use cases, or evidence", prompt)


# ---------------------------------------------------------------------------
# ScoredIdea result object tests
# ---------------------------------------------------------------------------

class TestScoredIdea(unittest.TestCase):

    def test_scored_idea_has_item_and_samples(self):
        """ScoredIdea bundles the original item, samples, median, and verdict."""
        from content_machine.oracle.scorer import ScoredIdea
        item = _make_item("hello")
        samples = [_score(7.0), _score(9.0)]
        si = ScoredIdea(item=item, samples=samples, median_composite=8.0, verdict="pass")
        self.assertEqual(si.item.title, "hello")
        self.assertEqual(len(si.samples), 2)
        self.assertEqual(si.verdict, "pass")

    def test_scored_idea_body_snippet(self):
        """ScoredIdea extracts first ~250 characters as body_snippet."""
        from content_machine.oracle.scorer import ScoredIdea
        item = _make_item("Long body item")
        item.body = "A" * 300
        si = ScoredIdea(item=item, samples=[], median_composite=8.0, verdict="pass")
        self.assertEqual(len(si.body_snippet), 250)
        self.assertEqual(si.body_snippet, "A" * 250)

    def test_scored_idea_dimension_scores(self):
        """ScoredIdea computes median dimension scores across samples."""
        from content_machine.oracle.scorer import ScoredIdea
        item = _make_item("Sample")
        s1 = IdeaScore(
            pov=8.0, lived_experience=7.0, specificity=6.0,
            counter_intuitive=9.0, generic_penalty_applied=False,
            composite=7.5, rationale="r1"
        )
        s2 = IdeaScore(
            pov=9.0, lived_experience=8.0, specificity=7.0,
            counter_intuitive=8.0, generic_penalty_applied=False,
            composite=8.0, rationale="r2"
        )
        si = ScoredIdea(item=item, samples=[s1, s2], median_composite=7.75, verdict="review")
        dims = si.dimension_scores
        self.assertEqual(dims["relevance"], 8.5)
        self.assertEqual(dims["lived_experience"], 7.5)
        self.assertEqual(dims["novelty"], 8.5)



# ---------------------------------------------------------------------------
# OracleOrchestrator tests
# ---------------------------------------------------------------------------

class TestOracleOrchestrator(unittest.TestCase):

    def _make_orchestrator(self, items=None):
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1,
                            idea_gate=8.0, idea_margin=0.5)
        router.complete.return_value = _score(9.0)  # all pass by default

        connectors = []
        if items is not None:
            mock_conn = MagicMock()
            mock_conn.fetch.return_value = ConnectorResult(
                source="test", items=items
            )
            connectors = [mock_conn]

        return OracleOrchestrator(connectors=connectors, scorer=scorer), router

    def test_run_returns_scored_ideas(self):
        """run() returns a list of ScoredIdea for each item fetched."""
        items = [_make_item("A", 0), _make_item("B", 1)]
        orch, _ = self._make_orchestrator(items=items)
        results = orch.run()
        self.assertEqual(len(results), 2)

    def test_iter_run_yields_scored_ideas(self):
        """iter_run() yields (scored_idea, is_cached) dynamically as evaluated."""
        items = [_make_item("A", 0), _make_item("B", 1)]
        orch, _ = self._make_orchestrator(items=items)
        yielded = list(orch.iter_run())
        self.assertEqual(len(yielded), 2)
        self.assertEqual(yielded[0][0].item.title, "A")
        self.assertFalse(yielded[0][1])  # is_cached is False

    def test_run_calls_all_connectors(self):
        """run() calls fetch() on every registered connector."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        router.complete.return_value = _score(9.0)
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)

        conn_a = MagicMock()
        conn_a.fetch.return_value = ConnectorResult(source="a", items=[_make_item("X", 0)])
        conn_b = MagicMock()
        conn_b.fetch.return_value = ConnectorResult(source="b", items=[_make_item("Y", 1)])

        orch = OracleOrchestrator(connectors=[conn_a, conn_b], scorer=scorer)
        results = orch.run()

        conn_a.fetch.assert_called_once()
        conn_b.fetch.assert_called_once()
        self.assertEqual(len(results), 2)

    def test_run_deduplicates_by_url(self):
        """Items with the same URL from different connectors are deduplicated."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        router.complete.return_value = _score(9.0)
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)

        item = _make_item("Dup", 0)
        conn_a = MagicMock()
        conn_a.fetch.return_value = ConnectorResult(source="a", items=[item])
        conn_b = MagicMock()
        conn_b.fetch.return_value = ConnectorResult(source="b", items=[item])

        orch = OracleOrchestrator(connectors=[conn_a, conn_b], scorer=scorer)
        results = orch.run()
        self.assertEqual(len(results), 1)

    def test_run_filters_rejected_ideas(self):
        """run() excludes items with verdict='reject' from the returned list."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        router.complete.return_value = _score(4.0)  # will be rejected
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1,
                            idea_gate=8.0, idea_margin=0.5)

        conn = MagicMock()
        conn.fetch.return_value = ConnectorResult(source="x", items=[_make_item("Bad", 0)])
        orch = OracleOrchestrator(connectors=[conn], scorer=scorer)
        results = orch.run(include_rejected=False)
        self.assertEqual(results, [])

    def test_run_include_rejected_returns_all(self):
        """include_rejected=True returns passing, review, and rejected items."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        # Two items: one pass, one reject
        router.complete.side_effect = [_score(9.0), _score(4.0)]
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1,
                            idea_gate=8.0, idea_margin=0.5)

        conn = MagicMock()
        conn.fetch.return_value = ConnectorResult(
            source="x", items=[_make_item("Good", 0), _make_item("Bad", 1)]
        )
        orch = OracleOrchestrator(connectors=[conn], scorer=scorer)
        results = orch.run(include_rejected=True)
        self.assertEqual(len(results), 2)

    def test_run_sorted_by_median_descending(self):
        """Results are sorted highest median_composite first."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        router.complete.side_effect = [_score(8.2), _score(9.5)]
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)

        conn = MagicMock()
        conn.fetch.return_value = ConnectorResult(
            source="x", items=[_make_item("Lower", 0), _make_item("Higher", 1)]
        )
        orch = OracleOrchestrator(connectors=[conn], scorer=scorer)
        results = orch.run(include_rejected=True)
        self.assertGreaterEqual(results[0].median_composite, results[1].median_composite)

    def test_run_respects_max_items_limit(self):
        """run(max_items=N) limits the number of items scored."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer

        router = MagicMock()
        router.complete.return_value = _score(8.5)
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)

        conn = MagicMock()
        conn.fetch.return_value = ConnectorResult(
            source="x", items=[_make_item(f"Item {i}", i) for i in range(10)]
        )
        orch = OracleOrchestrator(connectors=[conn], scorer=scorer)
        results = orch.run(include_rejected=True, max_items=3)
        self.assertEqual(len(results), 3)
        self.assertEqual(router.complete.call_count, 3)


    def test_run_persists_scores_to_db(self):
        """Scored ideas are persisted into the spikes table in the DB."""
        from content_machine.oracle.oracle import OracleOrchestrator
        from content_machine.oracle.scorer import IdeaScorer
        from content_machine.storage.db import connect

        conn_db = connect(":memory:")
        router = MagicMock()
        router.complete.return_value = _score(9.0)
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)

        conn = MagicMock()
        conn.fetch.return_value = ConnectorResult(
            source="rss", items=[_make_item("Persisted idea", 99)]
        )
        orch = OracleOrchestrator(connectors=[conn], scorer=scorer, db_conn=conn_db)
        orch.run()

        row = conn_db.execute("SELECT * FROM spikes").fetchone()
        self.assertIsNotNone(row)
        scores = json.loads(row["scores_json"])
        self.assertIn("samples", scores)
        self.assertIn("median_composite", scores)

    def test_feed_config_parsing(self):
        """AppConfig parses rss_feeds configuration with FeedConfig."""
        from content_machine.config import AppConfig, FeedConfig
        cfg = AppConfig.model_validate({
            "rss_feeds": [
                {
                    "url": "https://blog.example.com/rss",
                    "name": "tech_blog",
                    "category": "engineering",
                    "enabled": True,
                },
                {
                    "url": "https://rss.app/feeds/linkedin_proxy.xml",
                    "name": "linkedin:lead",
                    "category": "leadership",
                    "enabled": False,
                }
            ]
        })
        self.assertEqual(len(cfg.rss_feeds), 2)
        self.assertEqual(cfg.rss_feeds[0].name, "tech_blog")
        self.assertEqual(cfg.rss_feeds[0].category, "engineering")
        self.assertTrue(cfg.rss_feeds[0].enabled)
        self.assertFalse(cfg.rss_feeds[1].enabled)

    def test_config_json_loads_substacks_and_podcasts(self):
        """Root config.json should configure newsletters, podcasts, and engineering blogs."""
        import json
        from pathlib import Path
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        categories = {f.get("category") for f in data.get("rss_feeds", [])}
        self.assertIn("engineering_newsletter", categories)
        self.assertIn("tech_podcast", categories)
        self.assertIn("company_engineering_blog", categories)

    def test_category_aware_max_age_days_resolution(self):
        """Category-aware resolution returns 30 for company blogs, 14 for newsletters, 7 for aggregators."""
        from content_machine.config import get_category_default_max_age_days, FeedConfig
        self.assertEqual(get_category_default_max_age_days("company_engineering_blog"), 30)
        self.assertEqual(get_category_default_max_age_days("engineering_newsletter"), 14)
        self.assertEqual(get_category_default_max_age_days("tech_podcast"), 14)
        self.assertEqual(get_category_default_max_age_days("developer_community"), 7)
        self.assertEqual(get_category_default_max_age_days("tech"), 7)

        feed = FeedConfig(url="https://stripe.com/rss", category="company_engineering_blog", max_age_days=45, max_items=10)
        self.assertEqual(feed.max_age_days, 45)
        self.assertEqual(feed.max_items, 10)



    def test_pull_all_concurrent(self):
        """OracleOrchestrator pulls from multiple connectors concurrently."""
        from content_machine.oracle.scorer import IdeaScorer
        from content_machine.oracle.oracle import OracleOrchestrator
        router = MagicMock()
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)
        conn1 = MagicMock()
        conn1.fetch.return_value = ConnectorResult(source="feed1", items=[_make_item("Item 1", 1)])
        conn2 = MagicMock()
        conn2.fetch.return_value = ConnectorResult(source="feed2", items=[_make_item("Item 2", 2)])

        orch = OracleOrchestrator(connectors=[conn1, conn2], scorer=scorer)
        items = orch._pull_all()
        self.assertEqual(len(items), 2)
        urls = {it.url for it in items}
        self.assertEqual(urls, {"https://example.com/1", "https://example.com/2"})

    def test_pull_all_handles_connector_error_gracefully(self):
        """OracleOrchestrator continues pulling even if one connector fails."""
        from content_machine.oracle.scorer import IdeaScorer
        from content_machine.oracle.oracle import OracleOrchestrator
        router = MagicMock()
        scorer = IdeaScorer(router=router, scanner_model="m", n_samples=1)
        conn_ok = MagicMock()
        conn_ok.fetch.return_value = ConnectorResult(source="good", items=[_make_item("Good Item", 1)])
        conn_bad = MagicMock()
        conn_bad.fetch.side_effect = RuntimeError("Network timeout")

        orch = OracleOrchestrator(connectors=[conn_bad, conn_ok], scorer=scorer)
        items = orch._pull_all()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Good Item")




if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestScoredIdea, TestIdeaScorer, TestOracleOrchestrator]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)
