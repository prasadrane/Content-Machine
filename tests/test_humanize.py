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

    def test_sanitize_text_purges_manufactured_metaphors(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = "The workflow that stops the bleeding when dealing with AI."
        cleaned, purged = sanitize_text(text)
        self.assertNotIn("stops the bleeding", cleaned.lower())
        self.assertIn("fixes the issue", cleaned.lower())
        self.assertIn("stops the bleeding", purged)

    def test_sanitize_text_normalizes_em_dashes(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = "This pattern — which is often overlooked — solves the issue."
        cleaned, _ = sanitize_text(text)
        self.assertNotIn("—", cleaned)
        self.assertIn(",", cleaned)

    def test_sanitize_text_preserves_cli_flags_and_markdown_rules(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = (
            "Run python -m content_machine --verbose --flag --output=json\n"
            "---\n"
            "This pattern -- which was verified -- works with --dry-run."
        )
        cleaned, _ = sanitize_text(text)
        self.assertIn("--verbose", cleaned)
        self.assertIn("--flag", cleaned)
        self.assertIn("--output=json", cleaned)
        self.assertIn("--dry-run", cleaned)
        self.assertIn("---", cleaned)
        self.assertNotIn(" -- ", cleaned)

    def test_split_sentences(self):
        from content_machine.humanize.sanitizer import split_sentences

        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])
        sents = split_sentences("First sentence. Second sentence! Third sentence? \nFourth line sentence.")
        self.assertEqual(len(sents), 4)
        self.assertEqual(sents[0], "First sentence.")
        self.assertEqual(sents[1], "Second sentence!")
        self.assertEqual(sents[2], "Third sentence?")
        self.assertEqual(sents[3], "Fourth line sentence.")

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


class FakeRouter:
    def __init__(self, response_text: str = ""):
        self.response_text = response_text
        self.calls = []

    def complete(self, models, prompt="", system="", **kwargs):
        self.calls.append({"models": models, "prompt": prompt, "system": system})
        if self.response_text == "RAISE":
            raise RuntimeError("LLM Failure")
        return self.response_text


class TestHumanizeTransformer(unittest.TestCase):
    def test_transform_comment_enforces_max_sentences(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        fake_reply = (
            "Here is point one. Here is point two. Here is point three. "
            "Here is point four that should be dropped."
        )
        router = FakeRouter(response_text=fake_reply)
        transformer = HumanizeTransformer(router=router, voice_guide="Author voice guide")

        res = transformer.humanize_comment("Raw comment text", max_sentences=3)
        self.assertEqual(res.channel, HumanizeChannel.LINKEDIN_COMMENT)
        self.assertEqual(res.tone, HumanizeTone.PUNCHY_DIRECT)
        self.assertEqual(res.sentence_count, 3)
        self.assertNotIn("point four", res.humanized_text)

    def test_transform_tones_and_channels(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        fake_reply = "A pragmatic take on distributed event logs. You need backpressure."
        router = FakeRouter(response_text=fake_reply)
        transformer = HumanizeTransformer(router=router)

        res = transformer.humanize_post(
            "Draft post text about distributed event logs",
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
        )
        self.assertEqual(res.channel, HumanizeChannel.LINKEDIN_POST)
        self.assertEqual(res.tone, HumanizeTone.PRAGMATIC_ARCHITECT)
        self.assertIn("backpressure", res.humanized_text)

        # Verify prompt contained tone system instructions
        last_call = router.calls[-1]
        self.assertIn("PRAGMATIC ARCHITECT", last_call["system"])

    def test_transform_fallback_on_router_failure(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        router = FakeRouter(response_text="RAISE")
        transformer = HumanizeTransformer(router=router)

        raw = "We must delve into this — it is a pivotal moment."
        res = transformer.transform(raw, channel=HumanizeChannel.GENERAL)
        # Should gracefully fall back to sanitizer output
        self.assertNotIn("delve", res.humanized_text)
        self.assertNotIn("—", res.humanized_text)
        self.assertIn("delve", res.banned_words_purged)

    def test_transform_empty_input(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        router = FakeRouter(response_text="Ignored")
        transformer = HumanizeTransformer(router=router)

        res = transformer.transform("", channel=HumanizeChannel.GENERAL)
        self.assertEqual(res.humanized_text, "")
        self.assertEqual(res.sentence_count, 0)
        self.assertFalse(res.was_modified)
        self.assertEqual(len(router.calls), 0)

    def test_transform_scrubs_llm_banned_words(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        fake_reply = "We should delve into the tapestry — it is pivotal."
        router = FakeRouter(response_text=fake_reply)
        transformer = HumanizeTransformer(router=router)

        res = transformer.transform("Clean input", channel=HumanizeChannel.GENERAL)
        self.assertNotIn("delve", res.humanized_text.lower())
        self.assertNotIn("tapestry", res.humanized_text.lower())
        self.assertNotIn("—", res.humanized_text)
        self.assertIn("delve", res.banned_words_purged)

    def test_humanize_transformer_export_in_init(self):
        from content_machine.humanize import HumanizeTransformer
        self.assertIsNotNone(HumanizeTransformer)


if __name__ == "__main__":
    unittest.main()

