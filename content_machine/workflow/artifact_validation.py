"""Structural validation for a human-approved final artifact.

The registry decides whether a pair may be approved and supplies every
configured limit with its measurement. This module applies those limits to the
stored segment structure; it never edits, joins for storage, or invents a
platform constraint.

Script formats also retain the repository's production cues. Generation
readiness is deliberately irrelevant here: a manually authored valid script can
be approved even when its pair reports ``can_generate=False``.
"""

from __future__ import annotations

import re

from content_machine.workflow.format_registry import (
    UnknownFormatPairError,
    resolve_pair,
)
from content_machine.workflow.schema_types import (
    Artifact,
    FinalArtifactError,
    ensure_approvable,
)

SCRIPT_CUES = ("Visual Cue", "Camera Zoom", "Pause")
_SCRIPT_CUE_PATTERNS = tuple(
    (
        cue,
        re.compile(r"\[" + re.escape(cue) + r"(?::[^\[\]]*)?\]"),
    )
    for cue in SCRIPT_CUES
)
_CODE_POINTS = "unicode_code_points"


class ArtifactValidationError(FinalArtifactError):
    """A final artifact is structurally invalid or exceeds its configured cap."""


def _reject(message: str) -> None:
    raise ArtifactValidationError(message)


def _check_limits(artifact: Artifact, capability) -> None:
    total = sum(len(segment) for segment in artifact.segments)
    for name, limit in capability.limits.items():
        if limit.measurement != _CODE_POINTS:
            _reject(
                f"unsupported measurement for {name}: {limit.measurement}"
            )
        if name == "max_chars":
            if total > limit.value:
                _reject(
                    f"{capability.destination}/{capability.format} allows "
                    f"{limit.value} characters, got {total}"
                )
        elif name == "max_chars_per_segment":
            for index, segment in enumerate(artifact.segments):
                if len(segment) > limit.value:
                    _reject(
                        f"segment {index} allows {limit.value} characters, "
                        f"got {len(segment)}"
                    )
        else:
            _reject(f"unsupported configured limit: {name}")


def _check_script_cues(artifact: Artifact, format: str) -> None:
    if not format.endswith("_script"):
        return
    joined = "\n\n".join(artifact.segments)
    missing = [
        cue
        for cue, pattern in _SCRIPT_CUE_PATTERNS
        if pattern.search(joined) is None
    ]
    if missing:
        _reject(
            "script artifact is missing production cue(s): "
            + ", ".join(missing)
        )


def validate_final_artifact(
    artifact: Artifact, destination: str, format: str
) -> None:
    """Raise :class:`ArtifactValidationError` unless approval is structurally safe."""

    try:
        capability = resolve_pair(destination, format)
    except UnknownFormatPairError as exc:
        raise ArtifactValidationError(str(exc)) from exc
    if not capability.can_approve:
        _reject(f"{destination}/{format} cannot be approved")
    try:
        ensure_approvable(artifact, destination, format)
    except FinalArtifactError as exc:
        raise ArtifactValidationError(str(exc)) from exc
    _check_limits(artifact, capability)
    _check_script_cues(artifact, format)


__all__ = [
    "ArtifactValidationError",
    "SCRIPT_CUES",
    "validate_final_artifact",
]
