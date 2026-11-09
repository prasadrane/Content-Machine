"""Explicit human approval of one acknowledged workflow revision.

Approval is consent, not a score. Inside one transaction it replays a matching
idempotency key, performs the revision CAS, checks the client-echoed canonical
digest and explicit consent, validates the stored final artifact, freezes or
reuses the revision snapshot, inserts an immutable approval and moves only the
item's active approval/stage/timestamp to export.

The browser never supplies a version ID. Approval never edits text or context,
bumps the content revision, creates a review or calls a model.
"""

from __future__ import annotations

import json
import sqlite3
import uuid

from content_machine.workflow.artifact_validation import (
    ArtifactValidationError,
    validate_final_artifact,
)
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.format_registry import UnknownFormatPairError
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
    Approval,
    ApproveRequest,
    ContentItem,
    Principal,
    require_request_id,
    utc_timestamp,
)
from content_machine.workflow.versions import artifact_digest, freeze_version

APPROVE_PATH = "/api/workflow/items/{item_id}/approve"
_APPROVAL_SELECT = (
    "SELECT approval_id, owner_id, item_id, version_id, artifact_digest,"
    " destination, format, approved_by, approved_at"
    " FROM workflow_approvals"
)


def _approval_from_row(row: sqlite3.Row) -> Approval:
    return Approval.model_validate(
        {
            "approval_id": row["approval_id"],
            "owner_id": row["owner_id"],
            "item_id": row["item_id"],
            "version_id": row["version_id"],
            "artifact_digest": row["artifact_digest"],
            "destination": row["destination"],
            "format": row["format"],
            "approved_by": row["approved_by"],
            "approved_at": row["approved_at"],
        }
    )


def _acknowledged(item: ContentItem) -> dict[str, object]:
    return {
        "working_revision": item.working_revision,
        "stage": item.stage.value,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _conflict(item: ContentItem, code: str, detail: str) -> WorkflowError:
    return WorkflowError(409, code, detail, current=_acknowledged(item))


def _require_request_id(request_id: str) -> None:
    require_request_id(request_id)


def _validate_artifact(item: ContentItem) -> None:
    try:
        validate_final_artifact(item.artifact, item.destination, item.format)
    except (ArtifactValidationError, UnknownFormatPairError) as exc:
        raise WorkflowError(
            422, "invalid_artifact", f"Invalid final artifact: {exc}"
        ) from exc


def _updated_item(item: ContentItem, approval_id: str, now: str) -> ContentItem:
    data = item.model_dump(mode="python")
    data.update(
        stage=Stage.EXPORT,
        active_approval_id=approval_id,
        updated_at=now,
    )
    return ContentItem.model_validate(data)


def approve_item(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
    payload: ApproveRequest,
    *,
    request_id: str,
) -> WorkflowResult:
    """Record explicit consent for the current revision's exact artifact."""

    _require_request_id(request_id)
    method = "POST"
    path = APPROVE_PATH.format(item_id=item_id)
    digest = request_digest(method, path, payload.model_dump(mode="json", exclude_none=True))
    with atomic_write(conn):
        replay = find_idempotent(
            conn,
            principal.owner_id,
            request_id,
            method=method,
            resource_path=path,
            digest=digest,
        )
        if replay is not None:
            return replay

        item = get_item(conn, principal, item_id)
        if item.working_revision != payload.expected_revision:
            raise _conflict(
                item,
                "revision_conflict",
                "The item revision changed before this approval",
            )
        if payload.expected_updated_at is not None and payload.expected_updated_at != item.updated_at:
            raise _conflict(
                item,
                "revision_conflict",
                "The item changed in another session before this approval",
            )
        if not payload.consent:
            raise _conflict(
                item,
                "approval_conflict",
                "Explicit consent is required before approval",
            )
        actual_digest = artifact_digest(
            item.destination, item.format, item.artifact
        )
        if actual_digest != payload.artifact_digest:
            raise _conflict(
                item,
                "artifact_digest_mismatch",
                "The acknowledged artifact digest does not match the item",
            )
        _validate_artifact(item)

        version = freeze_version(
            conn,
            principal,
            item_id,
            expected_revision=item.working_revision,
            purpose=VersionPurpose.APPROVAL,
        )
        if (
            version.artifact != item.artifact
            or version.destination != item.destination
            or version.format != item.format
            or version.artifact_digest != actual_digest
        ):
            raise _conflict(
                item,
                "artifact_digest_mismatch",
                "The frozen snapshot does not match the acknowledged artifact",
            )

        now = utc_timestamp()
        approval = Approval(
            approval_id=f"apr_{uuid.uuid4().hex}",
            owner_id=item.owner_id,
            item_id=item.item_id,
            version_id=version.version_id,
            artifact_digest=actual_digest,
            destination=item.destination,
            format=item.format,
            approved_by=principal.owner_id,
            approved_at=now,
        )
        conn.execute(
            "INSERT INTO workflow_approvals("
            " approval_id, owner_id, item_id, version_id, artifact_digest,"
            " destination, format, approved_by, approved_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                approval.approval_id,
                approval.owner_id,
                approval.item_id,
                approval.version_id,
                approval.artifact_digest,
                approval.destination,
                approval.format,
                approval.approved_by,
                approval.approved_at,
            ),
        )
        cursor = conn.execute(
            "UPDATE workflow_items SET active_approval_id = ?, stage = ?,"
            " updated_at = ? WHERE item_id = ? AND owner_id = ?"
            " AND working_revision = ?"
            + (" AND updated_at = ?" if payload.expected_updated_at is not None else ""),
            (
                approval.approval_id,
                Stage.EXPORT.value,
                now,
                item.item_id,
                item.owner_id,
                item.working_revision,
            )
            + ((payload.expected_updated_at,) if payload.expected_updated_at is not None else ()),
        )
        if cursor.rowcount != 1:
            raise _conflict(
                item,
                "revision_conflict",
                "The item revision changed during approval",
            )
        updated = _updated_item(item, approval.approval_id, now)
        body = {
            "item": updated.model_dump(mode="json"),
            "approval": approval.model_dump(mode="json"),
            "version": version.model_dump(mode="json"),
        }
        record_idempotent(
            conn,
            principal.owner_id,
            request_id,
            method=method,
            resource_path=path,
            digest=digest,
            response_status=200,
            body=body,
            created_at=now,
        )
        return WorkflowResult(200, body)


def list_approvals(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str | None = None,
) -> list[Approval]:
    """List historical approvals, optionally bound to one owned item."""

    if item_id is not None:
        get_item(conn, principal, item_id)
        rows = conn.execute(
            f"{_APPROVAL_SELECT} WHERE owner_id = ? AND item_id = ?"
            " ORDER BY approved_at DESC, approval_id ASC",
            (principal.owner_id, item_id),
        ).fetchall()
    else:
        rows = conn.execute(
            f"{_APPROVAL_SELECT} WHERE owner_id = ?"
            " ORDER BY approved_at DESC, approval_id ASC",
            (principal.owner_id,),
        ).fetchall()
    return [_approval_from_row(row) for row in rows]


def get_approval(
    conn: sqlite3.Connection,
    principal: Principal,
    approval_id: str,
    item_id: str | None = None,
) -> Approval:
    """Return an owned historical approval, binding the item when supplied."""

    if item_id is not None:
        get_item(conn, principal, item_id)
        row = conn.execute(
            f"{_APPROVAL_SELECT}"
            " WHERE approval_id = ? AND item_id = ? AND owner_id = ?",
            (approval_id, item_id, principal.owner_id),
        ).fetchone()
    else:
        row = conn.execute(
            f"{_APPROVAL_SELECT} WHERE approval_id = ? AND owner_id = ?",
            (approval_id, principal.owner_id),
        ).fetchone()
    if row is None:
        raise WorkflowError(
            404, "approval_not_found", "Workflow approval not found"
        )
    return _approval_from_row(row)


__all__ = [
    "APPROVE_PATH",
    "approve_item",
    "get_approval",
    "list_approvals",
]
