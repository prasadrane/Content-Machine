"""Read-only workflow history and restoration services.

History exposes the immutable versions and approvals of one owned item. It is
strictly read-only and derives approval status only from the item's current
``active_approval_id``.

Restoration copies a version bound to the same owned item into a new working
revision. It first freezes any unsnapshotted current work, keeps the current
title, clears the active approval, and records the restored revision with the
``restore`` purpose. Historical approvals and snapshots are never mutated.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from content_machine.workflow.approvals import list_approvals
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item
from content_machine.workflow.persistence import (
    WorkflowResult,
    atomic_write,
    canonical_json,
    find_idempotent,
    record_idempotent,
    request_digest,
)
from content_machine.workflow.schema_types import Stage, VersionPurpose
from content_machine.workflow.schemas import (
    require_request_id,
    ContentItem,
    Principal,
    RestoreRequest,
    utc_timestamp,
)
from content_machine.workflow.versions import (
    freeze_version,
    get_version,
    list_versions,
)

RESTORE_PATH = "/api/workflow/items/{item_id}/restore"


def _require_request_id(request_id: str) -> None:
    require_request_id(request_id)


def _acknowledged(item: ContentItem) -> dict[str, object]:
    return {
        "working_revision": item.working_revision,
        "stage": item.stage.value,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _conflict(item: ContentItem, detail: str) -> WorkflowError:
    return WorkflowError(
        409,
        "revision_conflict",
        detail,
        current=_acknowledged(item),
    )


def get_history(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Return owned version summaries and active/historical approvals.

    No item, version, approval, review or idempotency row is written.
    """

    item = get_item(conn, principal, item_id)
    version_rows = [
        {
            "version_id": version.version_id,
            "revision": version.revision,
            "purpose": version.purpose.value,
            "artifact_digest": version.artifact_digest,
            "destination": version.destination,
            "format": version.format,
            "created_at": version.created_at,
        }
        for version in list_versions(conn, principal, item_id=item_id)
    ]
    approval_rows = [
        {
            "approval_id": approval.approval_id,
            "version_id": approval.version_id,
            "status": (
                "active"
                if approval.approval_id == item.active_approval_id
                else "historical"
            ),
            "approved_at": approval.approved_at,
        }
        for approval in list_approvals(conn, principal, item_id=item_id)
    ]
    return {"versions": version_rows, "approvals": approval_rows}


def restore_version(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
    payload: RestoreRequest,
    *,
    request_id: str,
) -> WorkflowResult:
    """Restore one same-item owned version into a new working revision.

    Matching idempotent requests replay before CAS. The acknowledged current
    revision is frozen first when it has no snapshot, so restore never destroys
    unsaved history. The new revision is unapproved and linked to the source
    version through ``parent_version_id``.
    """

    _require_request_id(request_id)
    method = "POST"
    path = RESTORE_PATH.format(item_id=item_id)
    digest = request_digest(method, path, payload.model_dump(mode="json"))

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
        source = get_version(
            conn, principal, payload.version_id, item_id=item_id
        )
        if item.working_revision != payload.expected_revision:
            raise _conflict(
                item,
                "The item revision changed before this restore",
            )

        freeze_version(
            conn,
            principal,
            item_id,
            expected_revision=item.working_revision,
            purpose=VersionPurpose.RESTORE,
        )

        now = utc_timestamp()
        next_revision = item.working_revision + 1
        data = item.model_dump(mode="python")
        data.update(
            destination=source.destination,
            format=source.format,
            stage=Stage.DRAFT_REVIEW,
            working_revision=next_revision,
            context=source.context.model_copy(deep=True),
            artifact=source.artifact.model_copy(deep=True),
            parent_version_id=source.version_id,
            active_approval_id=None,
            updated_at=now,
        )
        try:
            restored = ContentItem.model_validate(data)
        except ValueError as exc:
            raise WorkflowError(
                422,
                "invalid_restore",
                f"Invalid restored item: {exc}",
            ) from exc

        cursor = conn.execute(
            "UPDATE workflow_items SET destination = ?, format = ?,"
            " stage = ?, working_revision = ?, context_json = ?,"
            " artifact_json = ?, parent_version_id = ?,"
            " active_approval_id = NULL, updated_at = ?"
            " WHERE item_id = ? AND owner_id = ? AND working_revision = ?",
            (
                restored.destination,
                restored.format,
                restored.stage.value,
                restored.working_revision,
                canonical_json(restored.context.model_dump(mode="json")),
                canonical_json(restored.artifact.model_dump(mode="json")),
                restored.parent_version_id,
                restored.updated_at,
                item.item_id,
                item.owner_id,
                payload.expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise _conflict(
                get_item(conn, principal, item_id),
                "The item revision changed during this restore",
            )

        version = freeze_version(
            conn,
            principal,
            item_id,
            expected_revision=next_revision,
            purpose=VersionPurpose.RESTORE,
        )
        body = {
            "item": restored.model_dump(mode="json"),
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


__all__ = [
    "RESTORE_PATH",
    "get_history",
    "restore_version",
]
