"""Shared editorial constraints for all generation prompts.

Re-exports the rule constants from :mod:`content_machine.editorial.rules`.
"""

from .rules import (
    ANTI_FINGERPRINT_RULES,
    RULES_BLOCK,
    VOICE_RULE,
    WORD_COUNT_MAX,
    WORD_COUNT_MIN,
    WORD_COUNT_RULE,
)

__all__ = [
    "ANTI_FINGERPRINT_RULES",
    "RULES_BLOCK",
    "VOICE_RULE",
    "WORD_COUNT_MAX",
    "WORD_COUNT_MIN",
    "WORD_COUNT_RULE",
]
