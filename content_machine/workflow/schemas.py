"""Workflow record and request schemas from the frozen workflow contract.

Design rules enforced here:

* String contents are never stripped, normalized or reformatted.
* Ownership and timestamps are server-assigned; client input models neither
  declare nor accept them.
* Destination/format combinations are explicit retained pairs.
* Revisions are positive integers and immutable records are frozen.
* A content version owns deep snapshots of its context and artifact, so later
  working-object mutation cannot rewrite stored history or approved text.

Enums, constrained primitives, artifact values and time helpers live in
:mod:`content_machine.workflow.schema_types` and stay reexported here.
"""

from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from content_machine.workflow.schema_types import (
    ARTIFACT_DIGEST_PATTERN, MAX_ID_CHARS, MAX_MODEL_CONFIG_CHARS,
    MAX_NAME_CHARS, MAX_NOTES_CHARS, MAX_PATH_CHARS, MAX_SEGMENT_CHARS,
    MAX_SEGMENTS, MAX_SOURCES, MAX_TITLE_CHARS, TIMESTAMP_PATTERN,
    Artifact, ArtifactDigest, FinalArtifactError, Identifier,
    ModelConfigText, NoteText, OperationKind, OperationState,
    PairKey, PrincipalMode, RequestDigest, ResourcePath,
    ReviewState, Revision, SegmentText, ShortText,
    Stage, Timestamp, Title, UrlText,
    VersionPurpose, WorkflowModel, ensure_approvable,
    utc_timestamp, validate_pair,
)


class Principal(WorkflowModel):
    """Authenticated creator identity resolved by the deployment adapter."""

    owner_id: Identifier
    mode: PrincipalMode
    display_name: ShortText | None = None


class SourceRef(WorkflowModel):
    """One real ingested source attached to an item's context."""

    source_id: Identifier
    url: UrlText
    title: Title
    excerpt: NoteText
    fetched_at: Timestamp


class Context(WorkflowModel):
    """Item context; nested on the item and frozen into each version."""

    notes: NoteText = ""
    experience: NoteText | None = None
    interpretation: NoteText | None = None
    sources: list[SourceRef] = Field(default_factory=list, max_length=MAX_SOURCES)
    preference_snapshot_id: Identifier | None = None


class ContentItem(WorkflowModel):
    """Working item with nested context and artifact."""

    item_id: Identifier
    owner_id: Identifier
    title: Title
    destination: PairKey
    format: PairKey
    stage: Stage = Stage.IDEA
    working_revision: Revision = 1
    context: Context = Field(default_factory=Context)
    artifact: Artifact = Field(default_factory=Artifact)
    parent_version_id: Identifier | None = None
    active_approval_id: Identifier | None = None
    created_at: Timestamp
    updated_at: Timestamp

    @model_validator(mode="after")
    def _check_pair(self) -> "ContentItem":
        validate_pair(self.destination, self.format)
        return self

    @classmethod
    def new(
        cls,
        *,
        item_id: str,
        principal: Principal,
        payload: "ItemCreate",
        now: str,
    ) -> "ContentItem":
        """Build a new item with server-assigned ownership and timestamps."""

        return cls(
            item_id=item_id,
            owner_id=principal.owner_id,
            title=payload.title,
            destination=payload.destination,
            format=payload.format,
            stage=Stage.IDEA,
            working_revision=1,
            context=Context(),
            artifact=Artifact(),
            parent_version_id=None,
            active_approval_id=None,
            created_at=now,
            updated_at=now,
        )


class ContentVersion(WorkflowModel):
    """Immutable owned snapshot of one item revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version_id: Identifier
    item_id: Identifier
    owner_id: Identifier
    revision: Revision
    context: Context
    artifact: Artifact
    destination: PairKey
    format: PairKey
    artifact_digest: ArtifactDigest
    purpose: VersionPurpose
    created_by: Identifier
    created_at: Timestamp

    @model_validator(mode="before")
    @classmethod
    def _deep_snapshot_nested_inputs(cls, data: Any) -> Any:
        """Take defensive copies of nested inputs so no caller can alias them."""

        if isinstance(data, ContentVersion):
            data = data.model_dump()
        if not isinstance(data, dict):
            return data
        snapshot = dict(data)
        for key in ("context", "artifact"):
            if key in snapshot:
                snapshot[key] = copy.deepcopy(snapshot[key])
        return snapshot

    @model_validator(mode="after")
    def _check_pair(self) -> "ContentVersion":
        validate_pair(self.destination, self.format)
        return self


class Operation(WorkflowModel):
    """Server-created generate/review envelope bound to a frozen version."""

    operation_id: Identifier
    owner_id: Identifier
    item_id: Identifier
    kind: OperationKind
    input_version_id: Identifier
    context_snapshot: Context
    state: OperationState = OperationState.PENDING
    request_id: Identifier
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    started_at: Timestamp | None = None
    finished_at: Timestamp | None = None


class Proposal(WorkflowModel):
    """One proposed wording change, outside the scored input."""

    segment: int = Field(ge=0)
    current: SegmentText
    proposed: SegmentText
    provenance: Literal['model_rewrite', 'deterministic_cleanup', 'unknown'] = 'unknown'


class Review(WorkflowModel):
    """Review state, score basis and wording proposals for one version."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    review_id: Identifier
    owner_id: Identifier
    item_id: Identifier
    input_version_id: Identifier
    request_id: Identifier
    state: ReviewState
    actions: dict[str, Any] = Field(default_factory=dict)
    score_basis: dict[str, Any] | None = None
    proposals: list[Proposal] = Field(default_factory=list)
    llm_config: ModelConfigText | None = Field(
        default=None,
        alias="model_config",
        serialization_alias="model_config",
    )
    started_at: Timestamp | None = None
    finished_at: Timestamp | None = None


class Approval(WorkflowModel):
    """Immutable approval of one exact owned version and artifact digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: Identifier
    owner_id: Identifier
    item_id: Identifier
    version_id: Identifier
    artifact_digest: ArtifactDigest
    destination: PairKey
    format: PairKey
    approved_by: Identifier
    approved_at: Timestamp

    @model_validator(mode="after")
    def _check_pair(self) -> "Approval":
        validate_pair(self.destination, self.format)
        return self


class IdempotencyRecord(WorkflowModel):
    """Recorded response for one owner-scoped idempotency key."""

    owner_id: Identifier
    request_id: Identifier
    method: Literal["POST", "PATCH", "PUT", "DELETE"]
    resource_path: ResourcePath
    request_digest: RequestDigest
    response_status: int = Field(ge=100, le=599)
    response_body: dict[str, Any]
    created_at: Timestamp


class ItemCreate(WorkflowModel):
    """Create input. Ownership and timestamps are never client-supplied."""

    title: Title
    destination: PairKey
    format: PairKey

    @model_validator(mode="after")
    def _check_pair(self) -> "ItemCreate":
        validate_pair(self.destination, self.format)
        return self


class ItemPatch(WorkflowModel):
    """Save/stage input with compare-and-set revision."""

    expected_revision: Revision
    title: Title | None = None
    destination: PairKey | None = None
    format: PairKey | None = None
    stage: Stage | None = None
    context: Context | None = None
    artifact: Artifact | None = None

    @model_validator(mode="after")
    def _check_pair(self) -> "ItemPatch":
        if self.destination is not None and self.format is not None:
            validate_pair(self.destination, self.format)
        return self


class GenerateRequest(WorkflowModel):
    expected_revision: Revision


class ReviewRequest(WorkflowModel):
    expected_revision: Revision


class SkipReviewRequest(WorkflowModel):
    expected_revision: Revision


class ApproveRequest(WorkflowModel):
    expected_revision: Revision
    artifact_digest: ArtifactDigest
    consent: bool


class RestoreRequest(WorkflowModel):
    expected_revision: Revision
    version_id: Identifier


class AdaptRequest(WorkflowModel):
    source_version_id: Identifier
    destination: PairKey
    format: PairKey

    @model_validator(mode="after")
    def _check_pair(self) -> "AdaptRequest":
        validate_pair(self.destination, self.format)
        return self
