"""Tests for Subsystem 6: Cross-Channel Distribution Engine (plan v2 §7).

Transforms anchor post into:
1. X (Twitter) thread (hook + 6-8 cards + summary)
2. Short-form video script (60-90s with [Visual Cue] production markers)
3. Email / newsletter briefing (300-400 words executive summary)

All tests are offline — LLM calls are mocked. Follows strict TDD principles.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.storage.paths import project_dir


SAMPLE_ANCHOR_POST = """\
In March 2022, I fired our highest-performing engineer.

He wrote 4x more code than anyone else. But every commit created 3 hidden fires.
The team spent 40% of their sprint cycles reviewing his PRs and cleaning up silent outages.
When I let him go, velocity dropped for two weeks.
Then something unexpected happened: team output rose by 65% over the next quarter.

Key takeaways:
1. Individual velocity is a vanity metric if collective throughput collapses.
2. Net team drag matters more than raw output.
3. Specificity in boundaries is mercy.
"""


class TestDistributionEngine(unittest.TestCase):

    def _make_engine(self, model: str = "qwen3.8-flash", model_long: str = "qwen3.8-max"):
        from content_machine.distribution.engine import DistributionEngine
        router = MagicMock()
        return DistributionEngine(router=router, model=model, model_long=model_long), router

    def test_generate_x_thread_calls_router(self):
        """generate_x_thread calls router with anchor text and returns formatted thread."""
        engine, router = self._make_engine()
        router.complete.return_value = (
            "1/ In March 2022, I fired our highest-performing engineer.\n\n"
            "2/ He wrote 4x more code, but created 3 hidden fires per commit.\n\n"
            "3/ Net output rose 65% after."
        )
        thread = engine.generate_x_thread(SAMPLE_ANCHOR_POST)
        self.assertIn("1/", thread)
        self.assertIn("fired", thread)
        call_prompt = router.complete.call_args[1].get("prompt") or router.complete.call_args[0][1]
        self.assertIn("highest-performing engineer", call_prompt)

    def test_generate_video_script_contains_cues(self):
        """generate_video_script generates spoken word script with bracketed production cues."""
        engine, router = self._make_engine()
        router.complete.return_value = (
            "[Visual Cue: Close up on camera]\n"
            "I once fired our best engineer.\n\n"
            "[Camera Zoom]\n"
            "He wrote four times more code than anyone else. But here is the catch..."
        )
        script = engine.generate_video_script(SAMPLE_ANCHOR_POST)
        self.assertIn("[Visual Cue", script)
        self.assertIn("[Camera Zoom]", script)

    def test_generate_newsletter_digest_returns_briefing(self):
        """generate_newsletter_digest produces an executive briefing with markdown headers."""
        engine, router = self._make_engine()
        router.complete.return_value = (
            "## Executive Briefing: The Hidden Cost of Toxic High Performers\n\n"
            "In March 2022, a critical management decision shifted our engineering culture.\n\n"
            "### Core Takeaways\n"
            "- Individual velocity is secondary to collective velocity.\n"
            "- Protect sprint health over raw commits."
        )
        digest = engine.generate_newsletter_digest(SAMPLE_ANCHOR_POST)
        self.assertIn("## Executive Briefing", digest)
        self.assertIn("Core Takeaways", digest)

    def test_generate_linkedin_post_calls_router(self):
        """generate_linkedin_post calls router and returns LinkedIn formatted post."""
        engine, router = self._make_engine()
        router.complete.return_value = (
            "In March 2022, I made the hardest call of my career: I fired our 10x engineer.\n\n"
            "He wrote 4x more code than anyone else.\n"
            "Here is what happened next:\n\n"
            "1. Team throughput skyrocketed 65%.\n"
            "2. PR review latency collapsed.\n\n"
            "Individual speed is a vanity metric if collective throughput collapses.\n\n"
            "#EngineeringLeadership #SoftwareEngineering"
        )
        post = engine.generate_linkedin_post(SAMPLE_ANCHOR_POST)
        self.assertIn("In March 2022", post)
        self.assertIn("#EngineeringLeadership", post)
        call_prompt = router.complete.call_args_list[0][1].get("prompt") or router.complete.call_args_list[0][0][1]
        self.assertIn("highest-performing engineer", call_prompt)

    def test_generate_video_script_long_contains_chapters(self):
        """generate_video_script_long generates YouTube deep dive script with chapter markers and visual cues using model_long."""
        engine, router = self._make_engine(model="qwen3.8-flash", model_long="qwen3.8-max")
        router.complete.return_value = (
            "[Chapter 1: The Trap - 0:00]\n"
            "[Visual Cue: Talking head with graph overlay]\n"
            "Most engineering teams measure the wrong metric.\n\n"
            "[Chapter 2: The Root Cause - 2:30]\n"
            "[Screen Recording: Git history showing merge conflicts]\n"
            "Let's look at the actual commit history from that quarter."
        )
        script = engine.generate_video_script_long(SAMPLE_ANCHOR_POST)
        self.assertIn("[Chapter", script)
        self.assertIn("[Visual Cue", script)
        self.assertIn("[Screen Recording", script)
        call_models = router.complete.call_args[0][0]
        self.assertEqual(call_models, ["qwen3.8-max"])

    def test_generate_all_returns_bundle_dict(self):
        """generate_all() executes default platforms (linkedin, x_thread, video_script, newsletter)."""
        engine, router = self._make_engine()
        router.complete.side_effect = [
            "LinkedIn Post Content",
            "1/ X Thread",
            "[Visual Cue: Intro] Video Script",
            "## Newsletter Briefing",
        ]
        bundle = engine.generate_all(SAMPLE_ANCHOR_POST, humanize=False)
        self.assertIn("linkedin", bundle)
        self.assertIn("x_thread", bundle)
        self.assertIn("video_script", bundle)
        self.assertIn("newsletter", bundle)
        self.assertEqual(bundle["linkedin"], "LinkedIn Post Content")

    def test_generate_all_respects_custom_formats_filter(self):
        """generate_all() with explicit formats generates ONLY the requested platforms."""
        engine, router = self._make_engine()
        router.complete.side_effect = [
            "LinkedIn Only Content",
            "YouTube Long Deep Dive",
        ]
        bundle = engine.generate_all(SAMPLE_ANCHOR_POST, formats=["linkedin", "video_script_long"], humanize=False)
        self.assertEqual(len(bundle), 2)
        self.assertIn("linkedin", bundle)
        self.assertIn("video_script_long", bundle)
        self.assertNotIn("x_thread", bundle)
        self.assertNotIn("newsletter", bundle)
        self.assertEqual(router.complete.call_count, 2)


    def test_save_bundle_writes_markdown_files(self):
        """save_bundle() writes each format present in bundle to projects/{slug}/distribution/{format}.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"CONTENT_MACHINE_HOME": tmpdir}):
                from content_machine.distribution.engine import DistributionEngine
                engine = DistributionEngine(router=MagicMock())
                bundle = {
                    "linkedin": "LinkedIn content",
                    "x_thread": "1/ Test thread",
                    "video_script": "[Cue] Test video",
                    "video_script_long": "[Chapter 1] YouTube script",
                    "newsletter": "## Test news",
                }
                out_dir = engine.save_bundle(project_slug="2026-09-04_fire-engineer", bundle=bundle)
                self.assertTrue((out_dir / "linkedin.md").exists())
                self.assertTrue((out_dir / "x_thread.md").exists())
                self.assertTrue((out_dir / "video_script.md").exists())
                self.assertTrue((out_dir / "video_script_long.md").exists())
                self.assertTrue((out_dir / "newsletter.md").exists())
                self.assertEqual((out_dir / "linkedin.md").read_text(encoding="utf-8"), "LinkedIn content")
                self.assertEqual((out_dir / "x_thread.md").read_text(encoding="utf-8"), "1/ Test thread")

    def test_generate_linkedin_post_with_humanize_true(self):
        """generate_linkedin_post with humanize=True delegates to humanizer."""
        from content_machine.schemas import HumanizeResult, HumanizeTone, HumanizeChannel
        engine, router = self._make_engine()
        router.complete.return_value = "Raw LinkedIn post about firing a 10x engineer."

        mock_h_res = HumanizeResult(
            original_text="Raw LinkedIn post about firing a 10x engineer.",
            humanized_text="Humanized LinkedIn post: no fluff.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
            banned_words_purged=[],
            burstiness_score=5.0,
            sentence_count=2,
            was_modified=True,
        )
        engine.humanizer = MagicMock()
        engine.humanizer.humanize_post.return_value = mock_h_res

        res = engine.generate_linkedin_post(SAMPLE_ANCHOR_POST, humanize=True, tone=HumanizeTone.PUNCHY_DIRECT)
        self.assertEqual(res, "Humanized LinkedIn post: no fluff.")
        engine.humanizer.humanize_post.assert_called_once_with(
            "Raw LinkedIn post about firing a 10x engineer.",
            tone=HumanizeTone.PUNCHY_DIRECT,
        )

    def test_generate_x_thread_with_humanize_true(self):
        """generate_x_thread with humanize=True delegates to humanizer.transform."""
        from content_machine.schemas import HumanizeResult, HumanizeTone, HumanizeChannel
        engine, router = self._make_engine()
        router.complete.return_value = "1/ Raw X thread."

        mock_h_res = HumanizeResult(
            original_text="1/ Raw X thread.",
            humanized_text="1/ Humanized crisp thread.",
            channel=HumanizeChannel.X_THREAD,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
            banned_words_purged=[],
            burstiness_score=4.0,
            sentence_count=1,
            was_modified=True,
        )
        engine.humanizer = MagicMock()
        engine.humanizer.transform.return_value = mock_h_res

        res = engine.generate_x_thread(SAMPLE_ANCHOR_POST, humanize=True, tone=HumanizeTone.PRAGMATIC_ARCHITECT)
        self.assertEqual(res, "1/ Humanized crisp thread.")
        engine.humanizer.transform.assert_called_once_with(
            "1/ Raw X thread.",
            channel=HumanizeChannel.X_THREAD,
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
        )

    def test_generate_video_script_with_humanize_true(self):
        """generate_video_script_short with humanize=True delegates to humanizer.transform."""
        from content_machine.schemas import HumanizeResult, HumanizeTone, HumanizeChannel
        engine, router = self._make_engine()
        router.complete.return_value = "[Visual Cue] Raw video script."

        mock_h_res = HumanizeResult(
            original_text="[Visual Cue] Raw video script.",
            humanized_text="[Visual Cue] Humanized video script.",
            channel=HumanizeChannel.VIDEO_SCRIPT,
            tone=HumanizeTone.CONVERSATIONAL_PEER,
            banned_words_purged=[],
            burstiness_score=3.8,
            sentence_count=1,
            was_modified=True,
        )
        engine.humanizer = MagicMock()
        engine.humanizer.transform.return_value = mock_h_res

        res = engine.generate_video_script_short(SAMPLE_ANCHOR_POST, humanize=True, tone=HumanizeTone.CONVERSATIONAL_PEER)
        self.assertEqual(res, "[Visual Cue] Humanized video script.")
        engine.humanizer.transform.assert_called_once_with(
            "[Visual Cue] Raw video script.",
            channel=HumanizeChannel.VIDEO_SCRIPT,
            tone=HumanizeTone.CONVERSATIONAL_PEER,
        )

    def test_generate_linkedin_post_with_humanize_false(self):
        """generate_linkedin_post with humanize=False skips humanizer."""
        engine, router = self._make_engine()
        router.complete.return_value = "Raw LinkedIn post."
        engine.humanizer = MagicMock()

        res = engine.generate_linkedin_post(SAMPLE_ANCHOR_POST, humanize=False)
        self.assertEqual(res, "Raw LinkedIn post.")
        engine.humanizer.humanize_post.assert_not_called()
        engine.humanizer.transform.assert_not_called()


if __name__ == "__main__":
    unittest.main()

