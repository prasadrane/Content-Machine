"""Tests for content_machine.editorial — single source of truth for the shared
editorial constraints previously copy-pasted into 4 generation prompts.

Contract task-1:
- exact word-count constants (120 / 280)
- RULES_BLOCK contains both numbers and every anti-fingerprint ban category
- all 4 prompts (interview _SYNTHESIZE_SYSTEM, council REVISE_PROMPT,
  distribution _LINKEDIN_SYSTEM, humanize CHANNEL_PROMPTS[LINKEDIN_POST])
  carry the shared constraints, none carries the stale 120-250 drift,
  and every pre-existing prompt constraint survives the refactor.
"""

from content_machine.editorial import (
    ANTI_FINGERPRINT_RULES,
    RULES_BLOCK,
    VOICE_RULE,
    WORD_COUNT_MAX,
    WORD_COUNT_MIN,
    WORD_COUNT_RULE,
)
from content_machine.schemas import HumanizeChannel


# --- shared constants --------------------------------------------------------


def test_word_count_constants_exact():
    assert WORD_COUNT_MIN == 120
    assert WORD_COUNT_MAX == 280
    assert isinstance(WORD_COUNT_MIN, int)
    assert isinstance(WORD_COUNT_MAX, int)


def test_word_count_rule_mentions_both_bounds():
    assert "120" in WORD_COUNT_RULE
    assert "280" in WORD_COUNT_RULE
    assert "words" in WORD_COUNT_RULE.lower()


def test_voice_rule_practitioner_cadence():
    low = VOICE_RULE.lower()
    assert "conversational" in low
    assert "practitioner" in low
    # first-person field-note exemplars preserved from all 4 original prompts
    assert "I've started treating" in VOICE_RULE
    assert "What works better for me" in VOICE_RULE


def test_anti_fingerprint_rules_cover_every_ban_category():
    low = ANTI_FINGERPRINT_RULES.lower()
    # aphorism cap, max 1 takeaway
    assert "aphorism" in low
    assert "one takeaway" in low
    # rhetorical contrast formulas ban
    assert "contrast" in low
    assert "feels fast until" in low
    # manufactured metaphors / drama ban
    assert "metaphor" in low
    assert "stops the bleeding" in low
    assert "pure velocity" in low
    # broetry staccato ban
    assert "broetry" in low
    assert "staccato" in low
    # engagement bait + formulaic closers ban
    assert "engagement bait" in low
    assert "comment below" in low
    assert "fortune-cookie" in low


def test_rules_block_assembled_from_all_parts():
    assert "120" in RULES_BLOCK
    assert "280" in RULES_BLOCK
    assert WORD_COUNT_RULE in RULES_BLOCK
    assert VOICE_RULE in RULES_BLOCK
    assert ANTI_FINGERPRINT_RULES in RULES_BLOCK
    low = RULES_BLOCK.lower()
    for kw in ("aphorism", "contrast", "metaphor", "broetry", "engagement bait"):
        assert kw in low


# --- prompt integration --------------------------------------------------------


def _linkedin_channel_prompt():
    from content_machine.humanize.constants import CHANNEL_PROMPTS

    return CHANNEL_PROMPTS[HumanizeChannel.LINKEDIN_POST]


def _all_shared_prompts():
    from content_machine.council.loop import REVISE_PROMPT
    from content_machine.distribution.engine import _LINKEDIN_SYSTEM
    from content_machine.interview.engine import _SYNTHESIZE_SYSTEM

    return {
        "_SYNTHESIZE_SYSTEM": _SYNTHESIZE_SYSTEM,
        "REVISE_PROMPT": REVISE_PROMPT,
        "_LINKEDIN_SYSTEM": _LINKEDIN_SYSTEM,
        "CHANNEL_PROMPTS[LINKEDIN_POST]": _linkedin_channel_prompt(),
    }


def _assert_shared_rules(text):
    """Every prompt must carry the live word bounds plus anti-fingerprint bans."""
    assert "120" in text
    assert "280" in text
    assert "words" in text.lower()
    low = text.lower()
    assert "aphorism" in low
    assert "one takeaway" in low or "max 1 takeaway" in low
    assert "contrast" in low
    assert "feels fast until" in low
    assert "metaphor" in low
    assert "broetry" in low
    assert "engagement bait" in low or "comment below" in text


def test_all_four_prompts_carry_shared_rules():
    for name, text in _all_shared_prompts().items():
        assert isinstance(text, str) and text, name
        try:
            _assert_shared_rules(text)
        except AssertionError:  # pragma: no cover - test failure path only
            raise AssertionError(f"prompt {name} missing shared editorial rules")


def test_no_prompt_contains_stale_word_count_drift():
    for name, text in _all_shared_prompts().items():
        assert "120 and 250" not in text, name
        assert "120-250" not in text, name
        assert "120–250" not in text, name


# --- pre-existing constraints must survive the refactor ------------------------


def test_synthesize_system_keeps_pre_existing_constraints():
    from content_machine.interview.engine import _SYNTHESIZE_SYSTEM

    t = _SYNTHESIZE_SYSTEM
    assert "Ground every single claim" in t
    assert "HTTP 429s" in t
    assert "schema drift" in t
    assert "3 AM payment" in t  # fabricated-outage ban
    assert "mocks staying green" in t  # mechanics-connection rule
    assert "2-3 hyper-relevant technical hashtags" in t  # hashtag hygiene
    assert "delve" in t  # buzzword negative constraint
    assert "leverage" in t
    assert "game-changer" in t
    assert "authentic developer field note" in t


def test_revise_prompt_keeps_placeholders_and_constraints():
    from content_machine.council.loop import REVISE_PROMPT

    t = REVISE_PROMPT
    for ph in ("{style_section}", "{voice_section}", "{rules_section}",
               "{rubric}", "{draft}", "{critiques}"):
        assert ph in t, ph
    assert "RUBRIC" in t
    assert "COUNCIL CRITIQUES" in t
    assert "master drafter" in t
    assert "Address critiques concisely" in t
    assert "Mechanical specificity" in t
    assert "HTTP 429s" in t
    assert "3 AM payment" in t  # grounding ban
    assert "Hashtags: exactly 2-3" in t
    assert "No preamble, no commentary, no code fences" in t
    # format() contract still intact after refactor
    out = REVISE_PROMPT.format(
        style_section="STYLE", voice_section="VOICE", rules_section="RULES",
        rubric="RUB", draft="DRAFT", critiques="CRIT",
    )
    assert "STYLE" in out and "RUB" in out and "DRAFT" in out
    assert "120" in out and "280" in out
    assert "{" not in out  # no unsubstituted placeholders


def test_linkedin_system_keeps_pre_existing_constraints():
    from content_machine.distribution.engine import _LINKEDIN_SYSTEM

    t = _LINKEDIN_SYSTEM
    assert "Strictly anchor in the source text" in t
    assert "NEVER fabricate corporate production crashes" in t
    assert "Hook (first 1-2 lines)" in t
    assert "see more" in t  # cutoff-aware hook
    assert "mocks fail" in t  # body mechanics-connection rule
    assert "Return plain text" in t


def test_humanize_linkedin_post_keeps_pre_existing_constraints():
    t = _linkedin_channel_prompt()
    assert "Transform this into an authentic, concise LinkedIn post" in t
    assert "HTTP 429s" in t
    assert "contract drift" in t
    assert "debugging edge cases" in t
    assert "senior engineer's personal field note" in t
    assert "2-3 hashtags" in t


def test_editorial_imports_have_no_side_effects():
    # rules module must be pure constants (stdlib-only), safe to import anywhere
    import sys
    import importlib

    mod = importlib.import_module("content_machine.editorial.rules")
    assert sys.modules["content_machine.editorial"].RULES_BLOCK == mod.RULES_BLOCK
    src = mod.__file__
    with open(src, encoding="utf-8") as f:
        body = f.read()
    assert "import " not in body.split('"""')[2]  # no imports after the docstring
    assert body.isascii(), "rules.py must stay ASCII for Windows safety"
