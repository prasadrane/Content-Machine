"""Record an explicit decision to skip review of a saved revision."""

import sqlite3
import uuid

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item
from content_machine.workflow.persistence import (
    WorkflowResult,
    atomic_write,
    find_idempotent,
    record_idempotent,
    request_digest,
)
from content_machine.workflow.schema_types import Stage, VersionPurpose
from content_machine.workflow.schemas import (
    Principal,
    Review,
    SkipReviewRequest,
    require_request_id,
    utc_timestamp,
)
from content_machine.workflow.versions import freeze_version


def skip_review(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
    payload: SkipReviewRequest,
    *,
    request_id: str,
) -> WorkflowResult:
    """Freeze the current revision and record a skipped review atomically."""
    require_request_id(request_id)
    path = f"/api/workflow/items/{item_id}/skip-review"
    digest = request_digest("POST", path, payload.model_dump(mode="json", exclude_none=True))
    with atomic_write(conn):
        replay = find_idempotent(
            conn,
            principal.owner_id,
            request_id,
            method="POST",
            resource_path=path,
            digest=digest,
        )
        if replay is not None:
            return replay
        item = get_item(conn, principal, item_id)
        if item.working_revision != payload.expected_revision or (
            payload.expected_updated_at is not None
            and payload.expected_updated_at != item.updated_at
        ):
            raise WorkflowError(
                409,
                "revision_conflict",
                "The item revision changed before review was skipped",
                current={
                    "working_revision": item.working_revision,
                    "stage": item.stage.value,
                    "updated_at": item.updated_at,
                    "active_approval_id": item.active_approval_id,
                },
            )
        version = freeze_version(
            conn, principal, item_id, item.working_revision, VersionPurpose.SKIP_REVIEW
        )
        now = utc_timestamp()
        review = Review(
            review_id=f"rev_{uuid.uuid4().hex}",
            owner_id=principal.owner_id,
            item_id=item_id,
            input_version_id=version.version_id,
            request_id=request_id,
            state="skipped",
            started_at=now,
            finished_at=now,
        )
        conn.execute(
            "INSERT INTO workflow_reviews (review_id, owner_id, item_id, input_version_id,"
            " request_id, state, actions_json, score_basis_json, proposals_json, model_config,"
            " started_at, finished_at) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?, ?)",
            (
                review.review_id,
                review.owner_id,
                item_id,
                version.version_id,
                request_id,
                review.state.value,
                "{}",
                "[]",
                now,
                now,
            ),
        )
        cursor = conn.execute(
            "UPDATE workflow_items SET stage = ?, updated_at = ?"
            " WHERE item_id = ? AND owner_id = ? AND working_revision = ?"
            + (" AND updated_at = ?" if payload.expected_updated_at is not None else ""),
            (
                Stage.APPROVE.value,
                now,
                item_id,
                principal.owner_id,
                payload.expected_revision,
            )
            + ((payload.expected_updated_at,) if payload.expected_updated_at is not None else ()),
        )
        if cursor.rowcount != 1:
            raise WorkflowError(
                409, "revision_conflict", "The item revision changed during skip"
            )
        updated = get_item(conn, principal, item_id)
        body = {
            "review": review.model_dump(mode="json", by_alias=True),
            "item": updated.model_dump(mode="json"),
        }
        record_idempotent(
            conn,
            principal.owner_id,
            request_id,
            method="POST",
            resource_path=path,
            digest=digest,
            response_status=200,
            body=body,
            created_at=now,
        )
        return WorkflowResult(200, body)
