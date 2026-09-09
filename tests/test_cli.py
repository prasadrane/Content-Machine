"""Tests for the CLI entrypoint: python -m content_machine <subcommand>.

All tests run offline; external calls (router, connectors, subprocess) are mocked.
The tests drive the argument-parsing contract and verify the right subsystem is called.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _run_cli(*args, stdin_text: str = "") -> tuple[int, str, str]:
    """Invoke the CLI with the given argv; return (exit_code, stdout, stderr)."""
    from content_machine import __main__ as cli_module

    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    sys.argv = ["content_machine"] + list(args)
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf

    exit_code = 0
    try:
        cli_module.main()
    except SystemExit as e:
        exit_code = int(e.code) if e.code is not None else 0
    finally:
        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()


# ---------------------------------------------------------------------------
# Help / no-args
# ---------------------------------------------------------------------------

class TestCLIHelp(unittest.TestCase):

    def test_no_args_prints_usage(self):
        """Running with no arguments shows usage help."""
        code, out, err = _run_cli()
        self.assertIn("usage", (out + err).lower())

    def test_help_flag_exits_zero(self):
        """--help exits with code 0."""
        code, _, _ = _run_cli("--help")
        self.assertEqual(code, 0)

    def test_unknown_command_exits_nonzero(self):
        """Unknown subcommand exits with non-zero code."""
        code, _, _ = _run_cli("flibbertigibbet")
        self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# oracle subcommand
# ---------------------------------------------------------------------------

class TestOracleCLI(unittest.TestCase):

    def test_oracle_with_rss_url_calls_rss_connector(self):
        """oracle --rss <url> instantiates RSSConnector and runs OracleOrchestrator."""
        with patch("content_machine.__main__.RSSConnector") as MockRSS, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--rss", "https://example.com/feed")

        from unittest.mock import ANY
        MockRSS.assert_called_once_with(url="https://example.com/feed", db_conn=ANY, max_age_days=None, max_items=25)
        mock_orch_inst.run.assert_called_once()

    def test_oracle_with_idea_bank_calls_connector(self):
        """oracle --idea-bank <path> instantiates IdeaBankConnector and runs OracleOrchestrator."""
        with patch("content_machine.__main__.IdeaBankConnector") as MockIB, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--idea-bank", "path/to/bank.xlsx")

        MockIB.assert_called_once_with(file_path="path/to/bank.xlsx")
        mock_orch_inst.run.assert_called_once()


    def test_oracle_from_config_loads_rss_feeds(self):
        """oracle --from-config instantiates RSSConnector for enabled feeds in config."""
        from content_machine.config import AppConfig, FeedConfig
        fake_cfg = AppConfig(
            rss_feeds=[
                FeedConfig(url="https://feed1.com/rss", name="feed1", enabled=True),
                FeedConfig(url="https://feed2.com/rss", name="feed2", enabled=False),
            ]
        )
        with patch("content_machine.config.load_config", return_value=fake_cfg), \
             patch("content_machine.__main__.RSSConnector") as MockRSS, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_db"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--from-config")

        # Only enabled feed should be instantiated
        MockRSS.assert_called_once()
        _, kwargs = MockRSS.call_args
        self.assertEqual(kwargs.get("url"), "https://feed1.com/rss")
        self.assertEqual(kwargs.get("source_name"), "feed1")

    def test_oracle_cli_passes_max_age_days_and_max_items_per_feed(self):
        """CLI arguments --max-age-days and --max-items-per-feed are passed to RSSConnector."""
        with patch("content_machine.__main__.RSSConnector") as MockRSS, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_router"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--rss", "https://example.com/feed", "--max-age-days", "7", "--max-items-per-feed", "15")

        from unittest.mock import ANY
        MockRSS.assert_called_once_with(
            url="https://example.com/feed",
            db_conn=ANY,
            max_age_days=7,
            max_items=15,
        )

    def test_oracle_from_config_applies_category_defaults(self):
        """oracle --from-config applies category-aware default max_age_days (e.g. 30 for company blogs)."""
        from content_machine.config import AppConfig, FeedConfig
        fake_cfg = AppConfig(
            rss_feeds=[
                FeedConfig(url="https://stripe.com/blog/feed.rss", name="stripe", category="company_engineering_blog", enabled=True),
            ]
        )
        with patch("content_machine.config.load_config", return_value=fake_cfg), \
             patch("content_machine.__main__.RSSConnector") as MockRSS, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_db"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--from-config")

        MockRSS.assert_called_once()
        _, kwargs = MockRSS.call_args
        self.assertEqual(kwargs.get("max_age_days"), 30)
        self.assertEqual(kwargs.get("max_items"), 25)



    def test_oracle_prints_candidates(self):
        """oracle prints each scored idea's title and median composite score."""
        from content_machine.oracle.scorer import ScoredIdea
        from content_machine.connectors.base import ConnectorItem
        from content_machine.schemas import IdeaScore
        from datetime import datetime, timezone

        fake_item = ConnectorItem(
            title="AI is eating software",
            url="https://x.com/1",
            body="body",
            source="rss",
            fetched_at=datetime.now(tz=timezone.utc),
        )
        fake_scored = ScoredIdea(
            item=fake_item,
            samples=[],
            median_composite=8.7,
            verdict="pass",
        )

        with patch("content_machine.__main__.RSSConnector"), \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_router"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = [fake_scored]
            MockOrch.return_value = mock_orch_inst

            _, out, _ = _run_cli("oracle", "--rss", "https://example.com/feed")

        self.assertIn("AI is eating software", out)
        self.assertIn("8.7", out)

    def test_oracle_passes_limit_to_orchestrator(self):
        """oracle --limit N passes max_items=N to orch.run()."""
        with patch("content_machine.__main__.RSSConnector"), \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_router"):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--rss", "https://example.com/feed", "--limit", "5")

        mock_orch_inst.run.assert_called_once_with(include_rejected=False, max_items=5)


    def test_oracle_with_github_calls_github_connector(self):
        """oracle --github <repo> instantiates GitHubConnector."""
        with patch("content_machine.__main__.GitHubConnector") as MockGH, \
             patch("content_machine.__main__.OracleOrchestrator") as MockOrch, \
             patch("content_machine.__main__.IdeaScorer"), \
             patch("content_machine.__main__._make_router"), \
             patch.dict(os.environ, {"GITHUB_PAT": "ghp_test"}):
            mock_orch_inst = MagicMock()
            mock_orch_inst.run.return_value = []
            MockOrch.return_value = mock_orch_inst

            _run_cli("oracle", "--github", "org/repo")

        MockGH.assert_called_once()

    def test_oracle_no_sources_exits_nonzero(self):
        """oracle with no --rss or --github prints an error and exits non-zero."""
        code, _, err = _run_cli("oracle")
        self.assertNotEqual(code, 0)
        self.assertIn("source", err.lower())


# ---------------------------------------------------------------------------
# council subcommand
# ---------------------------------------------------------------------------

class TestCouncilCLI(unittest.TestCase):

    def _write_draft(self, text: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                        delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        return f.name

    def test_council_reads_draft_file(self):
        """council <file> passes the file contents to the council loop."""
        draft = self._write_draft("This is my draft post about building products.")
        try:
            with patch("content_machine.__main__.run_council") as mock_run:
                mock_run.return_value = MagicMock(
                    verdict="pass", composite_normalized=0.85,
                    required_actions=[], iteration=1
                )
                _run_cli("council", draft)
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args
            draft_text = call_kwargs[1].get("draft") or call_kwargs[0][0]
            self.assertIn("building products", draft_text)
        finally:
            os.unlink(draft)

    def test_council_missing_file_exits_nonzero(self):
        """council with a nonexistent file exits with non-zero code."""
        code, _, err = _run_cli("council", "/nonexistent/path/draft.md")
        self.assertNotEqual(code, 0)

    def test_council_prints_verdict(self):
        """council prints the final verdict and composite score."""
        draft = self._write_draft("Short draft.")
        try:
            with patch("content_machine.__main__.run_council") as mock_run:
                mock_run.return_value = MagicMock(
                    verdict="pass", composite_normalized=0.9,
                    required_actions=[], iteration=2
                )
                _, out, _ = _run_cli("council", draft)
            self.assertIn("pass", out.lower())
        finally:
            os.unlink(draft)


# ---------------------------------------------------------------------------
# transcribe subcommand
# ---------------------------------------------------------------------------

class TestTranscribeCLI(unittest.TestCase):

    def test_transcribe_calls_batch_transcriber(self):
        """transcribe <audio> calls BatchTranscriber.transcribe()."""
        with patch("content_machine.__main__.BatchTranscriber") as MockBT:
            mock_inst = MagicMock()
            mock_inst.transcribe.return_value = MagicMock(
                text="Hello world", word_count=2, model="faster-whisper/small"
            )
            MockBT.return_value = mock_inst
            _run_cli("transcribe", "/fake/audio.wav")
        mock_inst.transcribe.assert_called_once_with("/fake/audio.wav")

    def test_transcribe_model_flag_forwarded(self):
        """transcribe --model base uses BatchTranscriber(model='base')."""
        with patch("content_machine.__main__.BatchTranscriber") as MockBT:
            mock_inst = MagicMock()
            mock_inst.transcribe.return_value = MagicMock(
                text="hi", word_count=1, model="faster-whisper/base"
            )
            MockBT.return_value = mock_inst
            _run_cli("transcribe", "/fake/audio.wav", "--model", "base")
        MockBT.assert_called_once_with(model="base")

    def test_transcribe_prints_word_count(self):
        """transcribe prints the transcript word count to stdout."""
        with patch("content_machine.__main__.BatchTranscriber") as MockBT:
            mock_inst = MagicMock()
            mock_inst.transcribe.return_value = MagicMock(
                text="hello world test", word_count=3,
                model="faster-whisper/small", audio_path="/fake/audio.wav"
            )
            MockBT.return_value = mock_inst
            _, out, _ = _run_cli("transcribe", "/fake/audio.wav")
        self.assertIn("3", out)


# ---------------------------------------------------------------------------
# lessons subcommand
# ---------------------------------------------------------------------------

class TestLessonsCLI(unittest.TestCase):

    def _write_file(self, text: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                        delete=False, encoding="utf-8")
        f.write(text)
        f.close()
        return f.name

    def test_lessons_list_prints_active_rules(self):
        """lessons list prints each active rule with its ID."""
        fake_row = MagicMock()
        fake_row.__getitem__ = lambda self, k: {"id": 1, "rule_text": "End on the takeaway."}[k]
        with patch("content_machine.__main__.LessonsStore") as MockStore:
            mock_inst = MagicMock()
            mock_inst.active_rules.return_value = [fake_row]
            MockStore.return_value = mock_inst
            _, out, _ = _run_cli("lessons", "list")
        self.assertIn("takeaway", out)

    def test_lessons_approve_calls_approve(self):
        """lessons approve <id> calls LessonsStore.approve(id)."""
        with patch("content_machine.__main__.LessonsStore") as MockStore:
            mock_inst = MagicMock()
            MockStore.return_value = mock_inst
            _run_cli("lessons", "approve", "42")
        mock_inst.approve.assert_called_once_with(42)

    def test_lessons_reject_calls_reject(self):
        """lessons reject <id> calls LessonsStore.reject(id)."""
        with patch("content_machine.__main__.LessonsStore") as MockStore:
            mock_inst = MagicMock()
            MockStore.return_value = mock_inst
            _run_cli("lessons", "reject", "7")
        mock_inst.reject.assert_called_once_with(7)

    def test_lessons_diff_extracts_and_proposes(self):
        """lessons diff <draft> <published> extracts rules and proposes them."""
        draft_f = self._write_file("Generic leadership advice here.")
        pub_f = self._write_file("Specific story: March 2022, one decision.")
        try:
            with patch("content_machine.__main__.LessonsDiffer") as MockDiffer, \
                 patch("content_machine.__main__.LessonsStore") as MockStore, \
                 patch("content_machine.__main__._make_router"):
                mock_diff_inst = MagicMock()
                mock_diff_inst.extract.return_value = ["Rule A", "Rule B"]
                MockDiffer.return_value = mock_diff_inst

                mock_store_inst = MagicMock()
                mock_store_inst.propose.return_value = MagicMock(
                    is_conflict=False, merge_required=False, rule_id=1, inserted=True
                )
                MockStore.return_value = mock_store_inst

                _run_cli("lessons", "diff", draft_f, pub_f)

            self.assertEqual(mock_store_inst.propose.call_count, 2)
        finally:
            os.unlink(draft_f)
            os.unlink(pub_f)

    def test_lessons_diff_warns_on_conflict(self):
        """lessons diff prints a conflict warning when a similar rule exists."""
        draft_f = self._write_file("Draft text.")
        pub_f = self._write_file("Published text.")
        try:
            with patch("content_machine.__main__.LessonsDiffer") as MockDiffer, \
                 patch("content_machine.__main__.LessonsStore") as MockStore, \
                 patch("content_machine.__main__._make_router"):
                mock_diff_inst = MagicMock()
                mock_diff_inst.extract.return_value = ["Conflicting rule"]
                MockDiffer.return_value = mock_diff_inst

                mock_store_inst = MagicMock()
                mock_store_inst.propose.return_value = MagicMock(
                    is_conflict=True, conflict_rule_id=3,
                    merge_required=False, rule_id=5, inserted=True
                )
                MockStore.return_value = mock_store_inst

                _, out, _ = _run_cli("lessons", "diff", draft_f, pub_f)

            self.assertIn("conflict", out.lower())
        finally:
            os.unlink(draft_f)
            os.unlink(pub_f)


# ---------------------------------------------------------------------------
# comment subcommand
# ---------------------------------------------------------------------------

class TestCommentCLI(unittest.TestCase):

    def test_comment_generates_and_prints_output(self):
        """comment --post ... --angle contrarian --perspective ... invokes CommentingEngine and prints result."""
        from content_machine.schemas import CommentAngle, CommentRunResponse

        mock_resp = CommentRunResponse(
            comment_id="comment_123",
            initial_draft="Draft comment.",
            final_comment="Polished senior comment with real substance.",
            iteration=1,
            peak_score=8.75,
            verdict="PASS",
            actions=["Tighten opening"],
            judge_scores={"perell": 8.8, "purcell": 8.7},
            judge_critiques={"perell": "High punchiness and zero fluff."},
        )

        with patch("content_machine.__main__.CommentingEngine") as MockEngine, \
             patch("content_machine.__main__._make_router"), \
             patch("content_machine.__main__._make_db"), \
             patch("content_machine.config.load_config"):
            mock_inst = MagicMock()
            mock_inst.generate_comment.return_value = mock_resp
            MockEngine.return_value = mock_inst

            code, out, err = _run_cli(
                "comment",
                "--post", "Post content about distributed systems scaling limits.",
                "--angle", "contrarian",
                "--perspective", "We experienced split-brain issues at 50 nodes."
            )

        self.assertEqual(code, 0)
        MockEngine.return_value.generate_comment.assert_called_once_with(
            post_content="Post content about distributed systems scaling limits.",
            angle=CommentAngle.CONTRARIAN,
            perspective_text="We experienced split-brain issues at 50 nodes.",
        )
        self.assertIn("Polished senior comment with real substance.", out)
        self.assertIn("PASS", out)
        self.assertIn("8.75", out)
        self.assertIn("Council Breakdown:", out)
        self.assertIn("perell", out)
        self.assertIn("High punchiness", out)

    def test_comment_defaults(self):
        """comment with only --post defaults to insightful angle and None perspective."""
        from content_machine.schemas import CommentAngle, CommentRunResponse

        mock_resp = CommentRunResponse(
            comment_id="comment_456",
            initial_draft="Draft.",
            final_comment="Insightful comment.",
            iteration=1,
            peak_score=8.2,
            verdict="PASS",
            actions=[],
            judge_scores={},
            judge_critiques={},
        )

        with patch("content_machine.__main__.CommentingEngine") as MockEngine, \
             patch("content_machine.__main__._make_router"), \
             patch("content_machine.__main__._make_db"), \
             patch("content_machine.config.load_config"):
            mock_inst = MagicMock()
            mock_inst.generate_comment.return_value = mock_resp
            MockEngine.return_value = mock_inst

            code, out, _ = _run_cli("comment", "--post", "Observability matters in production.")

        self.assertEqual(code, 0)
        MockEngine.return_value.generate_comment.assert_called_once_with(
            post_content="Observability matters in production.",
            angle=CommentAngle.INSIGHTFUL,
            perspective_text=None,
        )
        self.assertIn("Insightful comment.", out)

    def test_comment_missing_post_fails(self):
        """comment without --post prints usage/error and exits non-zero."""
        code, _, err = _run_cli("comment")
        self.assertNotEqual(code, 0)

    def test_comment_short_post_fails(self):
        """comment with post < 10 chars prints error and exits 1."""
        code, _, err = _run_cli("comment", "--post", "short")
        self.assertEqual(code, 1)
        self.assertIn("--post must be at least 10 characters long", err)


# ---------------------------------------------------------------------------
# humanize subcommand
# ---------------------------------------------------------------------------

class TestHumanizeCLI(unittest.TestCase):

    def test_humanize_cli_with_inline_text(self):
        """humanize <text> runs transformer and prints humanized text and metrics."""
        from content_machine.schemas import HumanizeChannel, HumanizeResult, HumanizeTone
        mock_result = HumanizeResult(
            original_text="Delve into the multifaceted tapestry of modern systems.",
            humanized_text="Dig into modern systems.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
            banned_words_purged=["delve", "tapestry"],
            burstiness_score=5.5,
            sentence_count=1,
            was_modified=True,
        )

        with patch("content_machine.__main__.HumanizeTransformer") as MockTransformer, \
             patch("content_machine.__main__._make_router"):
            mock_inst = MagicMock()
            mock_inst.transform.return_value = mock_result
            MockTransformer.return_value = mock_inst

            code, out, err = _run_cli(
                "humanize",
                "Delve into the multifaceted tapestry of modern systems.",
                "--channel", "linkedin_post",
                "--tone", "punchy_direct",
            )

        self.assertEqual(code, 0)
        self.assertIn("Dig into modern systems.", out)
        self.assertIn("Burstiness Score: 5.50", out)
        self.assertIn("delve, tapestry", out)
        mock_inst.transform.assert_called_once_with(
            text="Delve into the multifaceted tapestry of modern systems.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
        )

    def test_humanize_cli_with_file(self):
        """humanize <file_path> reads file contents and runs transformer."""
        from content_machine.schemas import HumanizeChannel, HumanizeResult, HumanizeTone
        mock_result = HumanizeResult(
            original_text="File content to humanize.",
            humanized_text="Humanized file content.",
            channel=HumanizeChannel.GENERAL,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
            banned_words_purged=[],
            burstiness_score=4.0,
            sentence_count=1,
            was_modified=True,
        )

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md", encoding="utf-8") as f:
            f.write("File content to humanize.")
            tmp_path = f.name

        try:
            with patch("content_machine.__main__.HumanizeTransformer") as MockTransformer, \
                 patch("content_machine.__main__._make_router"):
                mock_inst = MagicMock()
                mock_inst.transform.return_value = mock_result
                MockTransformer.return_value = mock_inst

                code, out, err = _run_cli("humanize", tmp_path)

            self.assertEqual(code, 0)
            self.assertIn("Humanized file content.", out)
            mock_inst.transform.assert_called_once_with(
                text="File content to humanize.",
                channel=HumanizeChannel.GENERAL,
                tone=HumanizeTone.PRAGMATIC_ARCHITECT,
            )
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_humanize_missing_target_fails(self):
        """humanize without path/text fails with non-zero exit code."""
        code, _, err = _run_cli("humanize")
        self.assertNotEqual(code, 0)


# ---------------------------------------------------------------------------
# idea-bank subcommand
# ---------------------------------------------------------------------------

class TestIdeaBankCLI(unittest.TestCase):

    def test_idea_bank_list_calls_fetch(self):
        """idea-bank list <file> calls IdeaBankConnector.fetch()."""
        with patch("content_machine.__main__.IdeaBankConnector") as MockIB:
            mock_inst = MagicMock()
            mock_inst.fetch.return_value = MagicMock(items=[])
            MockIB.return_value = mock_inst

            code, out, err = _run_cli("idea-bank", "test.xlsx", "list")

        self.assertEqual(code, 0)
        MockIB.assert_called_once_with(file_path="test.xlsx")
        mock_inst.fetch.assert_called_once()

    def test_idea_bank_add_calls_append_idea(self):
        """idea-bank add <file> --title <title> calls append_idea()."""
        with patch("content_machine.__main__.IdeaBankConnector") as MockIB:
            mock_inst = MagicMock()
            mock_inst.append_idea.return_value = 5
            MockIB.return_value = mock_inst

            code, out, err = _run_cli("idea-bank", "test.xlsx", "add", "--title", "My Idea", "--brainstorm", "Notes")

        self.assertEqual(code, 0)
        self.assertIn("Added idea to row 5", out)
        mock_inst.append_idea.assert_called_once_with(title="My Idea", brainstorm="Notes")

    def test_idea_bank_pack_calls_append_packaging(self):
        """idea-bank pack <file> --title <title> calls append_packaging()."""
        with patch("content_machine.__main__.IdeaBankConnector") as MockIB:
            mock_inst = MagicMock()
            mock_inst.append_packaging.return_value = 4
            MockIB.return_value = mock_inst

            code, out, err = _run_cli("idea-bank", "test.xlsx", "pack", "--title", "Pack Title", "--template", "From X to Y")

        self.assertEqual(code, 0)
        self.assertIn("Added packaging entry to row 4", out)
        mock_inst.append_packaging.assert_called_once_with(
            final_title="Pack Title",
            brainstorm="",
            template_inspiration="From X to Y",
            thumbnail_rec="",
        )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestCLIHelp, TestOracleCLI, TestCouncilCLI,
                TestTranscribeCLI, TestLessonsCLI, TestCommentCLI, TestHumanizeCLI, TestIdeaBankCLI]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)

