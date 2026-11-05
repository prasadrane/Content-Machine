"""Initial backend capability registry for the creator workflow.

This module is the single source of truth for which destination/format pairs
the workflow accepts and what each pair may do. Readiness is always explicit:
a pair never implies generation support from its name, and an unimplemented
generation adapter reports ``can_generate=False``.

Platform limits are attached only where a configured adapter supplies them,
with their measurement and source metadata. No account-specific limit is
invented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


class UnknownFormatPairError(ValueError):
    """Raised when a destination/format pair is not a retained capability."""


@dataclass(frozen=True)
class FormatLimit:
    """One configured platform limit with its source and measurement."""

    value: int
    source: str = "configured_adapter"
    measurement: str = "unicode_code_points"

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "source": self.source,
            "measurement": self.measurement,
        }


@dataclass(frozen=True)
class FormatCapability:
    """One retained destination/format pair and its explicit readiness."""

    destination: str
    format: str
    can_edit: bool
    can_generate: bool
    can_approve: bool
    limits: Mapping[str, FormatLimit] = field(default_factory=dict)

    def supports_thread(self) -> bool:
        return is_thread_format(self.format)

    def as_payload(self) -> dict[str, Any]:
        return {
            "destination": self.destination,
            "format": self.format,
            "can_edit": self.can_edit,
            "can_generate": self.can_generate,
            "can_approve": self.can_approve,
            "limits": {
                name: limit.as_dict() for name, limit in self.limits.items()
            },
        }


# Formats whose artifact is an ordered list of thread segments.
THREAD_FORMATS = frozenset({"x_thread"})

_EMPTY_LIMITS: Mapping[str, FormatLimit] = MappingProxyType({})
_X_THREAD_LIMITS: Mapping[str, FormatLimit] = MappingProxyType(
    {"max_chars_per_segment": FormatLimit(280)}
)
_INSTAGRAM_CAPTION_LIMITS: Mapping[str, FormatLimit] = MappingProxyType(
    {"max_chars": FormatLimit(2200)}
)

# Retained in the approved order: platform rows first, generic last.
_CAPABILITIES: tuple[FormatCapability, ...] = (
    FormatCapability(
        destination="linkedin",
        format="linkedin_post",
        can_edit=True,
        can_generate=True,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
    FormatCapability(
        destination="x",
        format="x_thread",
        can_edit=True,
        can_generate=True,
        can_approve=True,
        limits=_X_THREAD_LIMITS,
    ),
    FormatCapability(
        destination="youtube",
        format="youtube_short_script",
        can_edit=True,
        can_generate=False,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
    FormatCapability(
        destination="youtube",
        format="youtube_long_script",
        can_edit=True,
        can_generate=True,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
    FormatCapability(
        destination="instagram",
        format="instagram_caption",
        can_edit=True,
        can_generate=False,
        can_approve=True,
        limits=_INSTAGRAM_CAPTION_LIMITS,
    ),
    FormatCapability(
        destination="instagram",
        format="instagram_reel_script",
        can_edit=True,
        can_generate=False,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
    FormatCapability(
        destination="newsletter",
        format="newsletter_draft",
        can_edit=True,
        can_generate=True,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
    FormatCapability(
        destination="generic_video",
        format="generic_short_video_script",
        can_edit=True,
        can_generate=True,
        can_approve=True,
        limits=_EMPTY_LIMITS,
    ),
)

CANONICAL_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (capability.destination, capability.format) for capability in _CAPABILITIES
)

_BY_PAIR: Mapping[tuple[str, str], FormatCapability] = MappingProxyType(
    {
        (capability.destination, capability.format): capability
        for capability in _CAPABILITIES
    }
)

# Legacy format ids stay readable; each expands to exactly one retained pair.
LEGACY_FORMAT_ALIASES: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "linkedin": ("linkedin", "linkedin_post"),
        "x_thread": ("x", "x_thread"),
        "video_script_long": ("youtube", "youtube_long_script"),
        "video_script_short": ("generic_video", "generic_short_video_script"),
        "video_script": ("generic_video", "generic_short_video_script"),
        "newsletter": ("newsletter", "newsletter_draft"),
    }
)


def resolve_pair(destination: str, format: str) -> FormatCapability:
    """Return the capability for a retained pair or raise.

    Only canonical pairs resolve here. Legacy ids flow through
    :func:`resolve_legacy_format`, which never guesses a missing mapping.
    """

    try:
        return _BY_PAIR[(destination, format)]
    except KeyError:
        raise UnknownFormatPairError(
            f"unknown destination/format pair: {destination!r}/{format!r}"
        ) from None


def get_capability(destination: str, format: str) -> FormatCapability:
    """Alias for :func:`resolve_pair` used by read surfaces."""

    return resolve_pair(destination, format)


def capability_payloads() -> list[dict[str, Any]]:
    """Return the API-ready capability rows in retained order."""

    return [capability.as_payload() for capability in _CAPABILITIES]


def is_thread_format(format: str) -> bool:
    """Return whether a format stores ordered thread segments."""

    return format in THREAD_FORMATS


def supports_thread(destination: str, format: str) -> bool:
    """Return whether a retained pair stores ordered thread segments."""

    return resolve_pair(destination, format).supports_thread()


def resolve_legacy_format(
    legacy_format: str, destination: str | None = None
) -> tuple[str, str]:
    """Expand a retained legacy format id to its canonical pair.

    A conflicting known destination is rejected rather than remapped, because
    the contract forbids guessing a mapping.
    """

    try:
        pair = LEGACY_FORMAT_ALIASES[legacy_format]
    except KeyError:
        raise UnknownFormatPairError(
            f"unknown legacy format: {legacy_format!r}"
        ) from None

    if destination is not None and destination != pair[0]:
        raise UnknownFormatPairError(
            f"legacy format {legacy_format!r} has no retained mapping "
            f"for destination {destination!r}"
        )
    return pair
