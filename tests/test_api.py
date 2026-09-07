"""Tests for the FastAPI backend (plan v2 §1, Step 8).

Uses FastAPI's built-in TestClient (synchronous, no real server needed).
All subsystem calls are mocked so tests run fully offline.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient


def _make_client():
    """Import app fresh (needed because patches must happen before import)."""
    from content_machine.api.app import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth(unittest.TestCase):

    def test_health_returns_200(self):
        """/api/health returns HTTP 200 with status ok."""
        client = _make_client()
        r = client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")


# ---------------------------------------------------------------------------
# Oracle
# ---------------------------------------------------------------------------

class TestOracleAPI(unittest.TestCase):

    def _mock_scored(self, title="Test idea", score=8.5, verdict="pass"):
        from content_machine.oracle.scorer import ScoredIdea
        from content_machine.connectors.base import ConnectorItem
        from datetime import datetime, timezone
        item = ConnectorItem(
            title=title, url="https://x.com/1", body="body",
            source="rss", fetched_at=datetime.now(tz=timezone.utc),
        )
        return ScoredIdea(item=item, samples=[], median_composite=score, verdict=verdict)

    def test_oracle_run_returns_candidates(self):
        """POST /api/oracle/run returns a list of scored ideas."""
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = [self._mock_scored()]
            MockOrch.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/oracle/run", json={
                "rss_urls": ["https://example.com/feed"],
                "github_repos": [],
                "no_persist": True,
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("candidates", data)
        self.assertEqual(len(data["candidates"]), 1)
        self.assertEqual(data["candidates"][0]["title"], "Test idea")

    def test_oracle_run_no_sources_returns_422(self):
        """POST /api/oracle/run with no sources returns 422 Unprocessable."""
        client = _make_client()
        r = client.post("/api/oracle/run", json={
            "rss_urls": [],
            "github_repos": [],
            "no_persist": True,
        })
        self.assertEqual(r.status_code, 422)

    def test_oracle_run_response_shape(self):
        """Each candidate has title, url, score, verdict, source fields."""
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = [self._mock_scored("My idea", 9.1, "pass")]
            MockOrch.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/oracle/run", json={
                "rss_urls": ["https://x.com/feed"],
                "github_repos": [],
                "no_persist": True,
            })

        c = r.json()["candidates"][0]
        for field in ("title", "url", "score", "verdict", "source"):
            self.assertIn(field, c)

    def test_candidate_out_includes_snippet_and_dimensions(self):
        from content_machine.api.app import CandidateOut
        c = CandidateOut(
            title="Test Title",
            url="https://example.com/1",
            score=8.5,
            verdict="pass",
            source="dev.to",
            body_snippet="First 250 characters of engineering signal...",
            dimension_scores={"relevance": 9.0, "novelty": 8.0, "lived_experience": 8.5},
        )
        self.assertEqual(c.body_snippet, "First 250 characters of engineering signal...")
        self.assertEqual(c.dimension_scores["relevance"], 9.0)


    def test_oracle_run_passes_limit_to_orchestrator(self):
        """POST /api/oracle/run with limit passes max_items to orch.run()."""
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = [self._mock_scored()]
            MockOrch.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/oracle/run", json={
                "rss_urls": ["https://example.com/feed"],
                "limit": 5,
                "no_persist": True,
            })

        self.assertEqual(r.status_code, 200)
        mock_inst.run.assert_called_once_with(include_rejected=False, max_items=5)

    def test_oracle_run_passes_date_and_items_limit_to_rss_connector(self):
        """POST /api/oracle/run forwards max_age_days and max_items_per_feed to RSSConnector."""
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector") as MockRSS, \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = []
            MockOrch.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/oracle/run", json={
                "rss_urls": ["https://example.com/feed"],
                "max_age_days": 14,
                "max_items_per_feed": 20,
                "no_persist": True,
            })

        self.assertEqual(r.status_code, 200)
        MockRSS.assert_called_once_with(
            url="https://example.com/feed",
            db_conn=None,
            max_age_days=14,
            max_items=20,
        )

    def test_oracle_history_returns_items_with_topic_tags(self):
        """GET /api/oracle/history returns historical spikes with topic_tag and filters."""
        from content_machine.storage.db import connect
        test_conn = connect(":memory:")
        test_conn.execute(
            "INSERT INTO spikes(id, category, hook_thesis, scores_json, status, topic_tag, source_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spk-1", "blog", "Rust Memory Allocators", json.dumps({"median_composite": 8.7, "verdict": "pass"}), "pass", "⚡ Systems & Architecture", "https://example.com/rust"),
        )
        test_conn.execute(
            "INSERT INTO spikes(id, category, hook_thesis, scores_json, status, topic_tag, source_url) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("spk-2", "news", "Engineering Leadership Tips", json.dumps({"median_composite": 6.2, "verdict": "reject"}), "reject", "📈 Engineering Leadership", "https://example.com/lead"),
        )
        test_conn.commit()

        with patch("content_machine.api.app._make_db", return_value=test_conn):
            client = _make_client()
            r_all = client.get("/api/oracle/history")
            self.assertEqual(r_all.status_code, 200)
            data = r_all.json()
            self.assertEqual(data["total"], 2)
            tags = {item["topic_tag"] for item in data["items"]}
            self.assertIn("⚡ Systems & Architecture", tags)
            self.assertIn("📈 Engineering Leadership", tags)

            # Filter by topic
            r_topic = client.get("/api/oracle/history", params={"topic": "⚡ Systems & Architecture"})
            self.assertEqual(r_topic.status_code, 200)
            self.assertEqual(len(r_topic.json()["items"]), 1)
            self.assertEqual(r_topic.json()["items"][0]["title"], "Rust Memory Allocators")

            # Filter by verdict
            r_verdict = client.get("/api/oracle/history", params={"verdict": "reject"})
            self.assertEqual(r_verdict.status_code, 200)
            self.assertEqual(len(r_verdict.json()["items"]), 1)
            self.assertEqual(r_verdict.json()["items"][0]["title"], "Engineering Leadership Tips")

    def test_oracle_scan_stream_endpoint_yields_sse_events(self):
        client = _make_client()
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = []
            MockOrch.return_value = mock_inst

            r = client.get("/api/oracle/scan-stream?rss_urls=https://dev.to/feed")
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            assert "event: phase" in r.text or "event: complete" in r.text

    def test_oracle_scan_stream_yields_candidates_and_progress(self):
        client = _make_client()
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = [self._mock_scored("Streaming idea", 8.8, "pass")]
            MockOrch.return_value = mock_inst

            r = client.get("/api/oracle/scan-stream?rss_urls=https://example.com/feed")
            self.assertEqual(r.status_code, 200)
            self.assertIn("text/event-stream", r.headers["content-type"])
            self.assertIn("event: phase", r.text)
            self.assertIn("event: source_fetched", r.text)
            self.assertIn("event: dedup", r.text)
            self.assertIn("event: scoring_progress", r.text)
            self.assertIn("event: candidate", r.text)
            self.assertIn("event: complete", r.text)
            self.assertIn("Streaming idea", r.text)

    def test_oracle_scan_stream_post_support(self):
        client = _make_client()
        with patch("content_machine.api.app.OracleOrchestrator") as MockOrch, \
             patch("content_machine.api.app.IdeaScorer"), \
             patch("content_machine.api.app.RSSConnector"), \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.run.return_value = [self._mock_scored("Post Stream Idea", 9.0, "pass")]
            MockOrch.return_value = mock_inst

            r = client.post("/api/oracle/scan-stream", json={
                "rss_urls": ["https://example.com/feed"],
                "no_persist": True,
            })
            self.assertEqual(r.status_code, 200)
            self.assertIn("text/event-stream", r.headers["content-type"])
            self.assertIn("event: candidate", r.text)
            self.assertIn("Post Stream Idea", r.text)

    def test_oracle_scan_stream_no_sources_returns_422(self):
        client = _make_client()
        r = client.get("/api/oracle/scan-stream")
        self.assertEqual(r.status_code, 422)


# ---------------------------------------------------------------------------
# Council
# ---------------------------------------------------------------------------


class TestCouncilAPI(unittest.TestCase):

    def test_council_run_returns_result(self):
        """POST /api/council/run returns verdict and normalized score."""
        with patch("content_machine.api.app.run_council") as mock_rc, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_rc.return_value = MagicMock(
                verdict="pass",
                composite_normalized=0.88,
                required_actions=["Tighten the opening."],
                iteration=1,
            )
            client = _make_client()
            r = client.post("/api/council/run", json={
                "draft": "This is my draft post.",
                "spike_id": "test-spike",
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("verdict", data)
        self.assertEqual(data["verdict"], "pass")
        self.assertIn("score", data)
        self.assertIn("actions", data)

    def test_council_run_empty_draft_returns_422(self):
        """POST /api/council/run with blank draft returns 422."""
        client = _make_client()
        r = client.post("/api/council/run", json={"draft": "", "spike_id": "x"})
        self.assertEqual(r.status_code, 422)

    def test_council_run_passes_max_iterations_and_returns_draft(self):
        """POST /api/council/run forwards max_iterations and returns draft content."""
        with patch("content_machine.api.app.run_council") as mock_rc, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_rc.return_value = MagicMock(
                verdict="revise",
                composite_normalized=0.75,
                composite_raw=7.5,
                required_actions=["Add metrics."],
                iteration=1,
                draft="Revised draft content.",
            )
            client = _make_client()
            r = client.post("/api/council/run", json={
                "draft": "Initial draft.",
                "spike_id": "test-spike",
                "max_iterations": 1,
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["draft"], "Revised draft content.")
        self.assertEqual(data["iteration"], 1)
        mock_rc.assert_called_once()
        _, kwargs = mock_rc.call_args
        self.assertEqual(kwargs.get("max_iterations"), 1)

    def test_council_run_translates_council_error_to_422(self):
        """CouncilError raises HTTPException(422)."""
        from content_machine.council.loop import CouncilError
        with patch("content_machine.api.app.run_council", side_effect=CouncilError("Quorum not met")), \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            client = _make_client()
            r = client.post("/api/council/run", json={
                "draft": "Initial draft.",
                "spike_id": "test-spike",
            })
        self.assertEqual(r.status_code, 422)
        self.assertIn("Quorum not met", r.json()["detail"])

    def test_council_run_translates_all_routes_failed_to_503(self):
        """AllRoutesFailed raises HTTPException(503)."""
        from content_machine.router.base import AllRoutesFailed
        with patch("content_machine.api.app.run_council", side_effect=AllRoutesFailed([("m", "r", "timeout")])), \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            client = _make_client()
            r = client.post("/api/council/run", json={
                "draft": "Initial draft.",
                "spike_id": "test-spike",
            })
        self.assertEqual(r.status_code, 503)
        self.assertIn("Model routing failed", r.json()["detail"])

    def test_council_run_translates_timeout_to_504(self):
        """anthropic.APITimeoutError raises HTTPException(504)."""
        import httpx
        import anthropic
        with patch("content_machine.api.app.run_council", side_effect=anthropic.APITimeoutError(request=httpx.Request("POST", "http://test"))), \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            client = _make_client()
            r = client.post("/api/council/run", json={
                "draft": "Initial draft.",
                "spike_id": "test-spike",
            })
        self.assertEqual(r.status_code, 504)
        self.assertIn("timed out", r.json()["detail"])


# ---------------------------------------------------------------------------
# Lessons
# ---------------------------------------------------------------------------

class TestLessonsAPI(unittest.TestCase):

    def _mock_row(self, rule_id=1, text="End on the takeaway.", project="p1", status="active"):
        row = MagicMock()
        row.keys.return_value = ["id", "rule_text", "provenance_project",
                                  "created_at", "status"]
        row.__getitem__ = lambda self, k: {
            "id": rule_id,
            "rule_text": text,
            "provenance_project": project,
            "created_at": "2026-09-04T10:00:00Z",
            "status": status,
        }[k]
        return row

    def test_lessons_list_returns_active_rules(self):
        """GET /api/lessons returns all active rules and pending review queue."""
        with patch("content_machine.api.app.LessonsStore") as MockStore, \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.active_rules.return_value = [self._mock_row()]
            mock_inst.pending_rules.return_value = [self._mock_row(rule_id=2, status="pending")]
            MockStore.return_value = mock_inst

            client = _make_client()
            r = client.get("/api/lessons")

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("rules", data)
        self.assertEqual(len(data["rules"]), 1)
        self.assertEqual(data["rules"][0]["rule_text"], "End on the takeaway.")
        self.assertIn("pending", data)
        self.assertEqual(len(data["pending"]), 1)
        self.assertEqual(data["pending"][0]["status"], "pending")

    def test_lessons_approve_returns_200(self):
        """POST /api/lessons/{id}/approve calls approve and returns 200."""
        with patch("content_machine.api.app.LessonsStore") as MockStore, \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            MockStore.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/lessons/5/approve")

        self.assertEqual(r.status_code, 200)
        mock_inst.approve.assert_called_once_with(5)

    def test_lessons_reject_returns_200(self):
        """POST /api/lessons/{id}/reject calls reject and returns 200."""
        with patch("content_machine.api.app.LessonsStore") as MockStore, \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            MockStore.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/lessons/3/reject")

        self.assertEqual(r.status_code, 200)
        mock_inst.reject.assert_called_once_with(3)

    def test_lessons_diff_returns_proposed_rules(self):
        """POST /api/lessons/diff extracts rules and returns proposals."""
        with patch("content_machine.api.app.LessonsDiffer") as MockDiff, \
             patch("content_machine.api.app.LessonsStore") as MockStore, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_diff = MagicMock()
            mock_diff.extract.return_value = ["Rule A", "Rule B"]
            MockDiff.return_value = mock_diff

            mock_store = MagicMock()
            mock_store.propose.return_value = MagicMock(
                rule_id=1, is_conflict=False, merge_required=False, inserted=True
            )
            MockStore.return_value = mock_store

            client = _make_client()
            r = client.post("/api/lessons/diff", json={
                "draft": "Generic advice.",
                "published": "Specific story with dates.",
                "project_id": "proj-1",
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("rules", data)
        self.assertEqual(len(data["rules"]), 2)

    def test_lessons_custom_create_active_rule(self):
        """POST /api/lessons/custom creates and approves a custom rule."""
        with patch("content_machine.api.app.LessonsStore") as MockStore, \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.propose.return_value = MagicMock(
                rule_id=42, is_conflict=False, conflict_rule_id=None, merge_required=False, inserted=True
            )
            MockStore.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/lessons/custom", json={
                "rule_text": "Never use buzzwords or corporate jargon.",
                "provenance_project": "manual",
                "auto_approve": True,
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["rule_id"], 42)
        mock_inst.propose.assert_called_once_with(rule="Never use buzzwords or corporate jargon.", project_id="manual")
        mock_inst.approve.assert_called_once_with(42)

    def test_lessons_custom_empty_rule_returns_422(self):
        """POST /api/lessons/custom with empty rule_text returns 422."""
        client = _make_client()
        r = client.post("/api/lessons/custom", json={"rule_text": ""})
        self.assertEqual(r.status_code, 422)



# ---------------------------------------------------------------------------
# Distribute
# ---------------------------------------------------------------------------

class TestDistributeAPI(unittest.TestCase):

    def test_distribute_run_returns_bundle(self):
        """POST /api/distribute/run returns linkedin, x_thread, video_script, and newsletter."""
        with patch("content_machine.api.app.DistributionEngine") as MockEng, \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.generate_all.return_value = {
                "linkedin": "LinkedIn Post",
                "x_thread": "1/ Thread",
                "video_script": "[Cue] Video",
                "newsletter": "## Newsletter",
            }
            MockEng.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/distribute/run", json={
                "anchor_post": "In March 2022, I fired our highest-performing engineer.",
                "project_slug": "proj-1",
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["linkedin"], "LinkedIn Post")
        self.assertEqual(data["x_thread"], "1/ Thread")
        self.assertEqual(data["video_script"], "[Cue] Video")
        self.assertEqual(data["newsletter"], "## Newsletter")

    def test_distribute_run_passes_enabled_formats(self):
        """POST /api/distribute/run passes enabled_formats list to engine.generate_all."""
        with patch("content_machine.api.app.DistributionEngine") as MockEng, \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.generate_all.return_value = {
                "linkedin": "LinkedIn Post",
                "video_script_long": "[Chapter 1] Deep Dive",
            }
            MockEng.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/distribute/run", json={
                "anchor_post": "In March 2022, I fired our highest-performing engineer.",
                "project_slug": "proj-1",
                "enabled_formats": ["linkedin", "video_script_long"],
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["linkedin"], "LinkedIn Post")
        self.assertEqual(data["video_script_long"], "[Chapter 1] Deep Dive")
        self.assertIsNone(data.get("x_thread"))
        from content_machine.schemas import HumanizeTone
        mock_inst.generate_all.assert_called_once_with(
            "In March 2022, I fired our highest-performing engineer.",
            formats=["linkedin", "video_script_long"],
            humanize=True,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
        )


    def test_distribute_run_forwards_humanize_params(self):
        """POST /api/distribute/run forwards humanize and tone params to engine.generate_all."""
        from content_machine.schemas import HumanizeTone
        with patch("content_machine.api.app.DistributionEngine") as MockEng, \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.generate_all.return_value = {"linkedin": "Polished"}
            MockEng.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/distribute/run", json={
                "anchor_post": "In March 2022, I fired our highest-performing engineer.",
                "humanize": False,
                "tone": "conversational_peer",
            })

        self.assertEqual(r.status_code, 200)
        mock_inst.generate_all.assert_called_once_with(
            "In March 2022, I fired our highest-performing engineer.",
            formats=None,
            humanize=False,
            tone=HumanizeTone.CONVERSATIONAL_PEER,
        )



class TestLinkedInAPI(unittest.TestCase):
    def test_linkedin_status_authenticated(self):
        with patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.get_saved_cookie", return_value="cookie-123"), \
             patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.is_valid", return_value=True), \
             patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.get_session_metadata", return_value={"li_at": "cookie-123", "saved_at": "2026-09-05T20:00:00Z"}):
            client = _make_client()
            r = client.get("/api/linkedin/status")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertTrue(data["session_valid"])
            self.assertEqual(data["mode"], "authenticated")
            self.assertEqual(data["saved_at"], "2026-09-05T20:00:00Z")

    def test_linkedin_status_public_bridge_mode(self):
        with patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.get_saved_cookie", return_value=None), \
             patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.is_valid", return_value=False), \
             patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.get_session_metadata", return_value={}):
            client = _make_client()
            r = client.get("/api/linkedin/status")
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertFalse(data["session_valid"])
            self.assertEqual(data["mode"], "public_bridge")
            self.assertIsNone(data["saved_at"])

    def test_linkedin_sync_success(self):
        with patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.sync_from_browser", return_value="synced-cookie-abc"), \
             patch("content_machine.connectors.linkedin_session.LinkedInSessionManager.is_valid", return_value=True):
            client = _make_client()
            r = client.post("/api/linkedin/sync", json={"headless": True})
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["mode"], "authenticated")


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestCommentsAPI(unittest.TestCase):

    def test_comments_generate_success(self):
        from content_machine.schemas import CommentRunResponse
        mock_response = CommentRunResponse(
            comment_id="comment-123",
            initial_draft="Draft comment.",
            final_comment="Final insightful comment about indexes.",
            iteration=1,
            peak_score=8.7,
            verdict="pass",
            actions=[],
            judge_scores={"narrative": 8.5},
            judge_critiques={},
        )
        with patch("content_machine.api.app.CommentingEngine") as MockEngine, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.generate_comment.return_value = mock_response
            MockEngine.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/comments/generate", json={
                "post_content": "A high quality engineering post about database index structures.",
                "angle": "insightful",
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["comment_id"], "comment-123")
        self.assertEqual(data["final_comment"], "Final insightful comment about indexes.")
        self.assertEqual(data["peak_score"], 8.7)
        self.assertEqual(data["verdict"], "pass")
        mock_inst.generate_comment.assert_called_once()

    def test_comments_generate_validation_error(self):
        client = _make_client()
        r = client.post("/api/comments/generate", json={"post_content": "short"})
        self.assertEqual(r.status_code, 422)

    def test_comments_history(self):
        from content_machine.schemas import CommentHistoryItem
        mock_items = [
            CommentHistoryItem(
                id="comment-123",
                post_content="A high quality engineering post about database index structures.",
                angle="insightful",
                perspective_text=None,
                final_comment="Final insightful comment about indexes.",
                iteration_count=1,
                peak_score=8.7,
                verdict="pass",
                created_at="2026-09-06T00:00:00Z",
            )
        ]
        with patch("content_machine.api.app.CommentingEngine") as MockEngine, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.get_history.return_value = mock_items
            MockEngine.return_value = mock_inst

            client = _make_client()
            r = client.get("/api/comments/history")

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], "comment-123")
        self.assertEqual(data["items"][0]["final_comment"], "Final insightful comment about indexes.")

    def test_comments_generate_server_error(self):
        with patch("content_machine.api.app.CommentingEngine") as MockEngine, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.generate_comment.side_effect = RuntimeError("Relay failed")
            MockEngine.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/comments/generate", json={
                "post_content": "A high quality engineering post about database index structures.",
                "angle": "insightful",
            })

        self.assertEqual(r.status_code, 500)
        self.assertIn("Comment generation failed: Relay failed", r.json()["detail"])

    def test_comments_history_limit_and_validation(self):
        with patch("content_machine.api.app.CommentingEngine") as MockEngine, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.get_history.return_value = []
            MockEngine.return_value = mock_inst

            client = _make_client()
            r = client.get("/api/comments/history?limit=10")
            self.assertEqual(r.status_code, 200)
            mock_inst.get_history.assert_called_once_with(limit=10)

            # limit > 200 fails validation
            r_invalid = client.get("/api/comments/history?limit=500")
            self.assertEqual(r_invalid.status_code, 422)

    def test_post_comment_forwards_humanize_params(self):
        """POST /api/comments/generate forwards humanize and tone to CommentingEngine."""
        from content_machine.schemas import CommentAngle, CommentRunResponse, HumanizeTone
        mock_resp = CommentRunResponse(
            comment_id="comment-123",
            initial_draft="Draft",
            final_comment="Final comment",
            iteration=1,
            peak_score=8.5,
            verdict="PASS",
            actions=[],
            judge_scores={},
            judge_critiques={},
            humanized=True,
            humanize_tone="punchy_direct",
            burstiness_score=4.2,
        )
        with patch("content_machine.api.app.CommentingEngine") as MockEngine, \
             patch("content_machine.api.app._make_router"), \
             patch("content_machine.api.app._make_db"):
            mock_inst = MagicMock()
            mock_inst.generate_comment.return_value = mock_resp
            MockEngine.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/comments/generate", json={
                "post_content": "A high quality engineering post about database index structures.",
                "angle": "insightful",
                "humanize": True,
                "tone": "punchy_direct",
            })

        self.assertEqual(r.status_code, 200)
        mock_inst.generate_comment.assert_called_once_with(
            post_content="A high quality engineering post about database index structures.",
            angle=CommentAngle.INSIGHTFUL,
            perspective_text=None,
            humanize=True,
            tone=HumanizeTone.PUNCHY_DIRECT,
        )



# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class TestProfileAPI(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.env_patch = patch.dict(os.environ, {"CONTENT_MACHINE_HOME": self.temp_dir})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_profile(self):
        """GET /api/profile returns 200 with ProfileData schema."""
        client = _make_client()
        r = client.get("/api/profile")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["name"], "Prasad Rane")
        self.assertIsInstance(data["hard_invariants"], list)
        self.assertGreater(len(data["hard_invariants"]), 0)

    def test_post_profile_update(self):
        """POST /api/profile updates profile and returns 200 with updated focus."""
        client = _make_client()
        r = client.post("/api/profile", json={"current_focus": "Fine-tuning agentic workflows"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["current_focus"], "Fine-tuning agentic workflows")

    def test_post_profile_update_mocked(self):
        """POST /api/profile calls ProfileManager.update_profile."""
        with patch("content_machine.api.app.ProfileManager") as MockManager:
            mock_inst = MagicMock()
            from content_machine.schemas import ProfileData
            mock_inst.update_profile.return_value = ProfileData(
                name="Prasad Rane",
                headline="Senior Software & AI Systems Engineer",
                current_focus="Fine-tuning agentic workflows",
                technical_domains=[".NET Core", "Agentic AI"],
                hard_invariants=["Zero Company Attribution"],
                full_markdown="# Voice Guide",
            )
            MockManager.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/profile", json={"current_focus": "Fine-tuning agentic workflows"})
            self.assertEqual(r.status_code, 200)
            data = r.json()
            self.assertEqual(data["current_focus"], "Fine-tuning agentic workflows")
            mock_inst.update_profile.assert_called_once()


# ---------------------------------------------------------------------------
# Humanize
# ---------------------------------------------------------------------------

class TestHumanizeAPI(unittest.TestCase):

    def test_post_humanize_endpoint(self):
        """POST /api/humanize transforms text and returns HumanizeResult."""
        from content_machine.schemas import HumanizeChannel, HumanizeResult, HumanizeTone
        mock_result = HumanizeResult(
            original_text="Delve into this tapestry of ideas.",
            humanized_text="Dig into these ideas.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
            banned_words_purged=["delve", "tapestry"],
            burstiness_score=4.5,
            sentence_count=1,
            was_modified=True,
        )
        with patch("content_machine.humanize.HumanizeTransformer") as MockTransformer, \
             patch("content_machine.api.app._make_router"):
            mock_inst = MagicMock()
            mock_inst.transform.return_value = mock_result
            MockTransformer.return_value = mock_inst

            client = _make_client()
            r = client.post("/api/humanize", json={
                "text": "Delve into this tapestry of ideas.",
                "channel": "linkedin_post",
                "tone": "pragmatic_architect",
            })

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["humanized_text"], "Dig into these ideas.")
        self.assertEqual(data["channel"], "linkedin_post")
        self.assertEqual(data["tone"], "pragmatic_architect")
        self.assertEqual(data["banned_words_purged"], ["delve", "tapestry"])
        self.assertEqual(data["burstiness_score"], 4.5)
        self.assertTrue(data["was_modified"])
        mock_inst.transform.assert_called_once_with(
            text="Delve into this tapestry of ideas.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
            max_sentences=None,
        )

    def test_post_humanize_short_text_fails(self):
        """POST /api/humanize requires text of at least 10 chars."""
        client = _make_client()
        r = client.post("/api/humanize", json={"text": "short"})
        self.assertEqual(r.status_code, 422)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestHealth, TestOracleAPI, TestCouncilAPI, TestLessonsAPI, TestDistributeAPI, TestLinkedInAPI, TestCommentsAPI, TestProfileAPI, TestHumanizeAPI]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)

