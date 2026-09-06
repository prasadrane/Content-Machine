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


class TestHumanizeSanitizer(unittest.TestCase):
    def test_sanitize_text_purges_banned_words(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = (
            "We must delve into this tapestry of ideas. "
            "It stands as a testament to our robust architecture, marking a pivotal moment."
        )
        cleaned, purged = sanitize_text(text)
        self.assertNotIn("delve", cleaned.lower())
        self.assertNotIn("tapestry", cleaned.lower())
        self.assertNotIn("stands as a testament", cleaned.lower())
        self.assertIn("delve", purged)
        self.assertIn("tapestry", purged)

    def test_sanitize_text_normalizes_em_dashes(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = "This pattern — which is often overlooked — solves the issue."
        cleaned, _ = sanitize_text(text)
        self.assertNotIn("—", cleaned)
        self.assertIn(",", cleaned)

    def test_calculate_burstiness_variance(self):
        from content_machine.humanize.sanitizer import calculate_burstiness

        # Monotone AI text: every sentence is exactly 5 words
        monotone = "One two three four five. Six seven eight nine ten. Eleven twelve thirteen fourteen fifteen."
        score_monotone = calculate_burstiness(monotone)
        self.assertEqual(score_monotone, 0.0)

        # Bursty human text: 2 words, then 14 words, then 4 words
        bursty = "It broke. The entire distributed cluster failed because the queue dropped partition messages under load. We fixed it."
        score_bursty = calculate_burstiness(bursty)
        self.assertTrue(score_bursty > 4.0)

    def test_calculate_burstiness_edge_cases(self):
        from content_machine.humanize.sanitizer import calculate_burstiness

        self.assertEqual(calculate_burstiness(""), 0.0)
        self.assertEqual(calculate_burstiness("Only one sentence here."), 0.0)

    def test_check_author_invariants(self):
        from content_machine.humanize.sanitizer import check_author_invariants

        clean_text = "Kafka partition lag spikes when consumer threads block on database I/O."
        self.assertEqual(check_author_invariants(clean_text), [])

        # Prohibited company mention
        dirty_text = "When I was building microservices at Rocket Mortgage, we used Kafka."
        violations = check_author_invariants(dirty_text)
        self.assertTrue(any("Rocket Mortgage" in v for v in violations))

        # Prohibited current corporate employment claim
        corp_text = "My team at work today just migrated our cluster."
        violations_corp = check_author_invariants(corp_text)
        self.assertTrue(any("team at work" in v for v in violations_corp))

        # Other prohibited companies
        for company in ["London Computer Systems", "EXFO", "Tanish Infotech"]:
            v = check_author_invariants(f"I worked at {company} on backend services.")
            self.assertTrue(any(company in msg for msg in v))


if __name__ == "__main__":
    unittest.main()

