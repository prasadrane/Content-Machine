"""Tests for Humanize Transformer schemas, constants, sanitizer, and engine."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.schemas import (
    HumanizeTone,
    HumanizeChannel,
    HumanizeRequest,
    HumanizeResult,
)
from content_machine.humanize.constants import (
    BANNED_AI_WORDS,
    BANNED_AI_PHRASES,
    TONE_SYSTEM_PROMPTS,
    CHANNEL_PROMPTS,
)


class TestHumanizeSchemasAndConstants(unittest.TestCase):
    def test_humanize_enums(self):
        self.assertEqual(HumanizeTone.PUNCHY_DIRECT.value, "punchy_direct")
        self.assertEqual(HumanizeTone.PRAGMATIC_ARCHITECT.value, "pragmatic_architect")
        self.assertEqual(HumanizeTone.CONVERSATIONAL_PEER.value, "conversational_peer")

        self.assertEqual(HumanizeChannel.LINKEDIN_COMMENT.value, "linkedin_comment")
        self.assertEqual(HumanizeChannel.LINKEDIN_POST.value, "linkedin_post")
        self.assertEqual(HumanizeChannel.X_THREAD.value, "x_thread")
        self.assertEqual(HumanizeChannel.VIDEO_SCRIPT.value, "video_script")
        self.assertEqual(HumanizeChannel.GENERAL.value, "general")

    def test_humanize_request_and_result(self):
        req = HumanizeRequest(
            text="This is a test post that needs to be humanized.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
        )
        self.assertEqual(req.channel, HumanizeChannel.LINKEDIN_POST)
        self.assertEqual(req.tone, HumanizeTone.PUNCHY_DIRECT)

        res = HumanizeResult(
            original_text=req.text,
            humanized_text="Test post rewritten.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
            banned_words_purged=["delve"],
            burstiness_score=4.2,
            sentence_count=1,
            was_modified=True,
        )
        self.assertEqual(res.burstiness_score, 4.2)
        self.assertEqual(res.banned_words_purged, ["delve"])

    def test_banned_constants_presence(self):
        self.assertIn("delve", BANNED_AI_WORDS)
        self.assertIn("tapestry", BANNED_AI_WORDS)
        self.assertIn("pivotal", BANNED_AI_WORDS)
        self.assertIn("testament", BANNED_AI_WORDS)
        self.assertIn("cornerstone", BANNED_AI_WORDS)
        self.assertIn("robust", BANNED_AI_WORDS)
        self.assertTrue(len(BANNED_AI_WORDS) >= 25)

        # Check phrases
        phrases_str = " ".join(BANNED_AI_PHRASES).lower()
        self.assertIn("stands as a testament", phrases_str)
        self.assertIn("evolving landscape", phrases_str)

        # Check prompts
        self.assertIn(HumanizeTone.PUNCHY_DIRECT, TONE_SYSTEM_PROMPTS)
        self.assertIn(HumanizeChannel.LINKEDIN_COMMENT, CHANNEL_PROMPTS)


if __name__ == "__main__":
    unittest.main()
