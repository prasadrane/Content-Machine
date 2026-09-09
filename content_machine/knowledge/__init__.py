"""Knowledge package: author voice, style guide, and governed rules."""

from .provider import (
    get_editorial_context,
    get_governed_rules,
    get_style_guide,
    get_voice_guide,
)

__all__ = [
    "get_editorial_context",
    "get_governed_rules",
    "get_style_guide",
    "get_voice_guide",
]
