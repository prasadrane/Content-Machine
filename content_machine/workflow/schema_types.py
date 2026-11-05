"""Low-level workflow value types shared by the domain schemas.

This module owns the explicit enums, constrained string primitives, the
artifact value type, its structural final-artifact guard and the UTC timestamp
helper. ``schemas.py`` reexports these names so existing imports keep working
while record and request models stay focused and readable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Sequence

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from content_machine.workflow.format_registry import (
    UnknownFormatPairError,
    resolve_pair,
)

TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
ARTIFACT_DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"

MAX_ID_CHARS = 200
MAX_TITLE_CHARS = 500
MAX_NOTES_CHARS = 200_000
MAX_SEGMENT_CHARS = 100_000
MAX_SEGMENTS = 500
MAX_SOURCES = 200
MAX_PATH_CHARS = 2_000
MAX_MODEL_CONFIG_CHARS = 200
MAX_NAME_CHARS = 200

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=MAX_ID_CHARS)]
Title = Annotated[str, StringConstraints(min_length=1, max_length=MAX_TITLE_CHARS)]
Timestamp = Annotated[str, StringConstraints(pattern=TIMESTAMP_PATTERN)]
ArtifactDigest = Annotated[str, StringConstraints(pattern=ARTIFACT_DIGEST_PATTERN)]
NoteText = Annotated[str, StringConstraints(max_length=MAX_NOTES_CHARS)]
SegmentText = Annotated[str, StringConstraints(max_length=MAX_SEGMENT_CHARS)]
PairKey = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Revision = Annotated[int, Field(ge=1)]
UrlText = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PATH_CHARS)]
ResourcePath = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PATH_CHARS)]
RequestDigest = Annotated[str, StringConstraints(min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(max_length=MAX_NAME_CHARS)]
ModelConfigText = Annotated[
    str, StringConstraints(max_length=MAX_MODEL_CONFIG_CHARS)
]


class WorkflowModel(BaseModel):
    """Base for workflow values: unknown fields are contract drift."""

    model_config = ConfigDict(extra="forbid")


class PrincipalMode(str, Enum):
    HOSTED_VERIFIED = "hosted_verified"
    TRUSTED_LOCAL = "trusted_local"


class Stage(str, Enum):
    IDEA = "idea"
    DRAFT_REVIEW = "draft_review"
    APPROVE = "approve"
    EXPORT = "export"


class VersionPurpose(str, Enum):
    REVIEW = "review"
    SKIP_REVIEW = "skip_review"
    APPROVAL = "approval"
    RESTORE = "restore"
    ADAPTATION = "adaptation"


class OperationKind(str, Enum):
    GENERATE = "generate"
    REVIEW = "review"


class OperationState(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewState(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


def validate_pair(destination: str, format: str) -> None:
    """Validate a retained pair and surface drift as a Pydantic value error."""

    try:
        resolve_pair(destination, format)
    except UnknownFormatPairError as exc:
        raise ValueError(str(exc)) from exc


class FinalArtifactError(ValueError):
    """Raised when a final artifact cannot be approved for its pair."""


class Artifact(WorkflowModel):
    """Ordered text segments.

    A post/caption/script/newsletter is exactly one segment; a thread is one
    segment per post in order. Empty is valid while an item is an idea or
    being edited. Stored text is kept exactly as supplied.
    """

    segments: list[SegmentText] = Field(
        default_factory=list, max_length=MAX_SEGMENTS
    )

    @classmethod
    def from_text(cls, text: SegmentText) -> "Artifact":
        """Store single-text content as exactly one segment."""

        return cls(segments=[text])

    @classmethod
    def from_thread(cls, segments: Sequence[SegmentText]) -> "Artifact":
        """Store thread content as ordered segments."""

        return cls(segments=list(segments))

    @property
    def is_blank(self) -> bool:
        return not any(segment.strip() for segment in self.segments)


def ensure_approvable(artifact: Artifact, destination: str, format: str) -> None:
    """Reject a final artifact that a retained pair cannot approve.

    Empty artifacts remain valid while editing. Approval requires at least one
    segment, every stored segment to contain non-whitespace text, and (except
    for thread formats) exactly one segment. Stored segments are never
    modified, and this guard states no platform length policy.
    """

    capability = resolve_pair(destination, format)
    if not artifact.segments:
        raise FinalArtifactError("final artifact has no segments")
    for index, segment in enumerate(artifact.segments):
        if not segment.strip():
            raise FinalArtifactError(f"final artifact segment {index} is blank")
    if not capability.supports_thread() and len(artifact.segments) != 1:
        raise FinalArtifactError(
            f"{destination}/{format} is a single-text format; "
            f"expected exactly one segment, got {len(artifact.segments)}"
        )


def utc_timestamp(moment: datetime | None = None) -> str:
    """Format a server timestamp as ISO-8601 UTC with milliseconds."""

    current = moment or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    return current.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current.microsecond // 1000:03d}Z"
