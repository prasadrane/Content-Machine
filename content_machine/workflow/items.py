"""Owned working-item persistence for the creator workflow.

All reads and writes filter on the explicit ``Principal.owner_id``; storage
never reads request headers or infers an owner. Titles are labels, not keys, so
different owners (or the same owner) may use identical titles.

Create and save return :class:`WorkflowResult` containing the complete item in
``{"item": ...}``. Their status/body pair is stored for matching idempotent
replays. Read helpers return ``ContentItem`` values for the route layer.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import (
    WorkflowResult, atomic_write, canonical_json, find_idempotent,
    record_idempotent, request_digest,
)
from content_machine.workflow.schema_types import Stage
from content_machine.workflow.schemas import (
    ContentItem, ItemCreate, ItemPatch, Principal, require_request_id, utc_timestamp,
)

ITEMS_PATH = "/api/workflow/items"
_PATCH_FIELDS = ("title", "destination", "format", "stage", "context", "artifact")
_ROW_FIELDS = (
    "item_id", "owner_id", "title", "destination", "format", "stage",
    "working_revision", "parent_version_id", "active_approval_id",
    "created_at", "updated_at",
)
_ITEM_SELECT = (
    "SELECT item_id, owner_id, title, destination, format, stage,"
    " working_revision, context_json, artifact_json, parent_version_id,"
    " active_approval_id, created_at, updated_at FROM workflow_items"
)


def _require_request_id(request_id: str) -> None:
    require_request_id(request_id)


def _invalid_item(exc: ValueError) -> WorkflowError:
    return WorkflowError(422, "invalid_item", f"Invalid workflow item: {exc}")


def _reject_explicit_nulls(patch: ItemPatch) -> None:
    nulls = [name for name in _PATCH_FIELDS
             if name in patch.model_fields_set and getattr(patch, name) is None]
    if nulls:
        raise WorkflowError(422, "invalid_item", f"These fields cannot be null: {', '.join(nulls)}")


def _item_from_row(row: sqlite3.Row) -> ContentItem:
    data = {name: row[name] for name in _ROW_FIELDS}
    data["context"] = json.loads(row["context_json"])
    data["artifact"] = json.loads(row["artifact_json"])
    return ContentItem.model_validate(data)


def _get_owned(
    conn: sqlite3.Connection, owner_id: str, item_id: str
) -> ContentItem:
    row = conn.execute(
        f"{_ITEM_SELECT} WHERE item_id = ? AND owner_id = ?",
        (item_id, owner_id),
    ).fetchone()
    if row is None:
        raise WorkflowError(404, "item_not_found", "Workflow item not found")
    return _item_from_row(row)


def _acknowledged(item: ContentItem) -> dict[str, Any]:
    return {
        "working_revision": item.working_revision,
        "stage": item.stage.value,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _patch_value(patch: ItemPatch, name: str, current: Any) -> Any:
    return getattr(patch, name) if name in patch.model_fields_set else current


def _conflict(item: ContentItem) -> WorkflowError:
    return WorkflowError(
        409, "revision_conflict", "The item revision changed before this save",
        current=_acknowledged(item),
    )


def _replay(
    conn: sqlite3.Connection, owner_id: str, request_id: str, *,
    method: str, path: str, digest: str,
) -> WorkflowResult | None:
    return find_idempotent(
        conn, owner_id, request_id,
        method=method, resource_path=path, digest=digest,
    )


def _record(
    conn: sqlite3.Connection, owner_id: str, request_id: str, *,
    method: str, path: str, digest: str, status: int,
    body: dict[str, Any], now: str,
) -> None:
    record_idempotent(
        conn, owner_id, request_id,
        method=method, resource_path=path, digest=digest,
        response_status=status, body=body, created_at=now,
    )


def _has_current_approval(
    conn: sqlite3.Connection, item: ContentItem, merged: ContentItem
) -> bool:
    if merged.active_approval_id is None:
        return False
    return conn.execute(
        "SELECT 1 FROM workflow_approvals AS a"
        " JOIN workflow_versions AS v ON v.version_id = a.version_id"
        " AND v.owner_id = a.owner_id AND v.item_id = a.item_id"
        " WHERE a.approval_id = ? AND a.owner_id = ? AND a.item_id = ?"
        " AND v.revision = ? AND a.destination = ? AND a.format = ?",
        (merged.active_approval_id, item.owner_id, item.item_id,
         merged.working_revision, merged.destination, merged.format),
    ).fetchone() is not None


def get_item(
    conn: sqlite3.Connection, principal: Principal, item_id: str
) -> ContentItem:
    """Return an owned item; missing and cross-owner IDs are both 404."""

    return _get_owned(conn, principal.owner_id, item_id)


def list_items(
    conn: sqlite3.Connection, principal: Principal
) -> list[ContentItem]:
    """List only the principal's items, most recently updated first."""

    rows = conn.execute(
        f"{_ITEM_SELECT} WHERE owner_id = ? ORDER BY updated_at DESC, item_id ASC",
        (principal.owner_id,),
    ).fetchall()
    return [_item_from_row(row) for row in rows]


def create_item(
    conn: sqlite3.Connection, principal: Principal, payload: ItemCreate, *,
    request_id: str,
) -> WorkflowResult:
    """Create an owned revision-1 item and record the replayable response."""

    _require_request_id(request_id)
    method, resource_path = "POST", ITEMS_PATH
    digest = request_digest(method, resource_path, payload.model_dump(mode="json"))
    with atomic_write(conn):
        replay = _replay(
            conn, principal.owner_id, request_id,
            method=method, path=resource_path, digest=digest,
        )
        if replay is not None:
            return replay
        now = utc_timestamp()
        try:
            item = ContentItem.new(
                item_id=f"itm_{uuid.uuid4().hex}", principal=principal,
                payload=payload, now=now,
            )
        except ValueError as exc:
            raise _invalid_item(exc) from exc
        conn.execute(
            "INSERT INTO workflow_items("
            " item_id, owner_id, title, destination, format, stage,"
            " working_revision, context_json, artifact_json, parent_version_id,"
            " active_approval_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item.item_id, item.owner_id, item.title, item.destination,
             item.format, item.stage.value, item.working_revision,
             canonical_json(item.context.model_dump(mode="json")),
             canonical_json(item.artifact.model_dump(mode="json")),
             item.parent_version_id, item.active_approval_id,
             item.created_at, item.updated_at),
        )
        body = {"item": item.model_dump(mode="json")}
        _record(
            conn, principal.owner_id, request_id,
            method=method, path=resource_path, digest=digest,
            status=201, body=body, now=now,
        )
        return WorkflowResult(201, body)


def save_item(
    conn: sqlite3.Connection, principal: Principal, item_id: str,
    patch: ItemPatch, *, request_id: str,
) -> WorkflowResult:
    """Apply a CAS patch, merge it over acknowledged state and validate the result."""

    _require_request_id(request_id)
    method, resource_path = "PATCH", f"{ITEMS_PATH}/{item_id}"
    digest = request_digest(
        method, resource_path, patch.model_dump(mode="json", exclude_unset=True)
    )
    with atomic_write(conn):
        replay = _replay(
            conn, principal.owner_id, request_id,
            method=method, path=resource_path, digest=digest,
        )
        if replay is not None:
            return replay
        _reject_explicit_nulls(patch)
        item = _get_owned(conn, principal.owner_id, item_id)
        if item.working_revision != patch.expected_revision:
            raise _conflict(item)
        if patch.expected_updated_at is not None and patch.expected_updated_at != item.updated_at:
            raise _conflict(item)

        title = _patch_value(patch, "title", item.title)
        destination = _patch_value(patch, "destination", item.destination)
        format = _patch_value(patch, "format", item.format)
        context = _patch_value(patch, "context", item.context)
        artifact = _patch_value(patch, "artifact", item.artifact)
        content_changed = (
            destination != item.destination or format != item.format
            or context != item.context or artifact != item.artifact
        )
        requested_stage = _patch_value(patch, "stage", None)
        next_stage = requested_stage or (Stage.DRAFT_REVIEW if content_changed else item.stage)
        next_revision = item.working_revision + (1 if content_changed else 0)
        next_approval = None if content_changed else item.active_approval_id
        now = utc_timestamp()

        data = item.model_dump(mode="python")
        data.update(
            title=title, destination=destination, format=format, stage=next_stage,
            working_revision=next_revision, context=context, artifact=artifact,
            active_approval_id=next_approval, updated_at=now,
        )
        try:
            merged = ContentItem.model_validate(data)
        except ValueError as exc:
            raise _invalid_item(exc) from exc

        if merged.stage == Stage.EXPORT and not _has_current_approval(conn, item, merged):
            raise WorkflowError(
                409, "approval_required",
                "An approval for this item revision is required before export",
            )

        cursor = conn.execute(
            "UPDATE workflow_items SET title = ?, destination = ?, format = ?,"
            " stage = ?, working_revision = ?, context_json = ?,"
            " artifact_json = ?, active_approval_id = ?, updated_at = ?"
            " WHERE item_id = ? AND owner_id = ? AND working_revision = ?"
            + (" AND updated_at = ?" if patch.expected_updated_at is not None else ""),
            (merged.title, merged.destination, merged.format, merged.stage.value,
             merged.working_revision,
             canonical_json(merged.context.model_dump(mode="json")),
             canonical_json(merged.artifact.model_dump(mode="json")),
             merged.active_approval_id, merged.updated_at, item.item_id,
             item.owner_id, patch.expected_revision)
            + ((patch.expected_updated_at,) if patch.expected_updated_at is not None else ()),
        )
        if cursor.rowcount != 1:
            raise _conflict(_get_owned(conn, principal.owner_id, item_id))

        body = {"item": merged.model_dump(mode="json")}
        _record(
            conn, principal.owner_id, request_id,
            method=method, path=resource_path, digest=digest,
            status=200, body=body, now=now,
        )
        return WorkflowResult(200, body)


__all__ = ["create_item", "get_item", "list_items", "save_item"]
