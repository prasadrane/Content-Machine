"""Immutable owned content snapshots for the workflow.

A freeze reads the acknowledged working item inside one short write
transaction, returns the existing version for its revision or inserts a
server-identified snapshot of the full context, exact artifact, destination and
format. It never edits the working item, its approval, stage or review state,
and storage triggers keep version rows immutable.

Version reads are owner-filtered. When an item ID is supplied, both the item
and version IDs are bound in the lookup so another item's version cannot
satisfy a nested read. Cross-item adaptation ancestry belongs to C08.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item
from content_machine.workflow.persistence import atomic_write, canonical_json
from content_machine.workflow.schema_types import VersionPurpose
from content_machine.workflow.schemas import (
    Artifact,
    ContentItem,
    ContentVersion,
    Principal,
    utc_timestamp,
)

_VERSION_SELECT = (
    "SELECT version_id, item_id, owner_id, revision, context_json,"
    " artifact_json, destination, format, artifact_digest, purpose,"
    " created_by, created_at FROM workflow_versions"
)


def artifact_digest(
    destination: str, format: str, artifact: Artifact
) -> str:
    """Return the contract digest of the exact segment sequence."""

    payload = {
        "destination": destination,
        "format": format,
        "segments": artifact.segments,
    }
    encoded = canonical_json(payload).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _version_from_row(row: sqlite3.Row) -> ContentVersion:
    return ContentVersion.model_validate(
        {
            "version_id": row["version_id"],
            "item_id": row["item_id"],
            "owner_id": row["owner_id"],
            "revision": row["revision"],
            "context": json.loads(row["context_json"]),
            "artifact": json.loads(row["artifact_json"]),
            "destination": row["destination"],
            "format": row["format"],
            "artifact_digest": row["artifact_digest"],
            "purpose": row["purpose"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
        }
    )


def _acknowledged(item: ContentItem) -> dict[str, object]:
    return {
        "working_revision": item.working_revision,
        "stage": item.stage.value,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _find_version(
    conn: sqlite3.Connection,
    owner_id: str,
    item_id: str,
    revision: int,
) -> ContentVersion | None:
    row = conn.execute(
        f"{_VERSION_SELECT} WHERE owner_id = ? AND item_id = ? AND revision = ?",
        (owner_id, item_id, revision),
    ).fetchone()
    return _version_from_row(row) if row is not None else None


def freeze_version(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
    expected_revision: int,
    purpose: VersionPurpose,
) -> ContentVersion:
    """Freeze the acknowledged revision or return its existing snapshot."""

    try:
        snapshot_purpose = VersionPurpose(purpose)
    except (TypeError, ValueError) as exc:
        raise WorkflowError(
            422,
            "invalid_version_purpose",
            "A valid version purpose is required",
        ) from exc

    with atomic_write(conn):
        item = get_item(conn, principal, item_id)
        if item.working_revision != expected_revision:
            raise WorkflowError(
                409,
                "revision_conflict",
                "The item revision changed before this freeze",
                current=_acknowledged(item),
            )

        existing = _find_version(
            conn, item.owner_id, item.item_id, item.working_revision
        )
        if existing is not None:
            return existing

        version = ContentVersion(
            version_id=f"ver_{uuid.uuid4().hex}",
            item_id=item.item_id,
            owner_id=item.owner_id,
            revision=item.working_revision,
            context=item.context,
            artifact=item.artifact,
            destination=item.destination,
            format=item.format,
            artifact_digest=artifact_digest(
                item.destination, item.format, item.artifact
            ),
            purpose=snapshot_purpose,
            created_by=principal.owner_id,
            created_at=utc_timestamp(),
        )
        conn.execute(
            "INSERT INTO workflow_versions("
            " version_id, item_id, owner_id, revision, context_json,"
            " artifact_json, destination, format, artifact_digest, purpose,"
            " created_by, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                version.version_id,
                version.item_id,
                version.owner_id,
                version.revision,
                canonical_json(version.context.model_dump(mode="json")),
                canonical_json(version.artifact.model_dump(mode="json")),
                version.destination,
                version.format,
                version.artifact_digest,
                version.purpose.value,
                version.created_by,
                version.created_at,
            ),
        )
        return version


def list_versions(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str | None = None,
) -> list[ContentVersion]:
    """List owned versions, optionally bound to one owned item."""

    if item_id is not None:
        get_item(conn, principal, item_id)
        rows = conn.execute(
            f"{_VERSION_SELECT} WHERE owner_id = ? AND item_id = ?"
            " ORDER BY revision DESC, created_at DESC, version_id ASC",
            (principal.owner_id, item_id),
        ).fetchall()
    else:
        rows = conn.execute(
            f"{_VERSION_SELECT} WHERE owner_id = ?"
            " ORDER BY created_at DESC, version_id ASC",
            (principal.owner_id,),
        ).fetchall()
    return [_version_from_row(row) for row in rows]


def get_version(
    conn: sqlite3.Connection,
    principal: Principal,
    version_id: str,
    item_id: str | None = None,
) -> ContentVersion:
    """Return an owned version, binding both IDs when an item is supplied."""

    if item_id is not None:
        get_item(conn, principal, item_id)
        row = conn.execute(
            f"{_VERSION_SELECT}"
            " WHERE version_id = ? AND item_id = ? AND owner_id = ?",
            (version_id, item_id, principal.owner_id),
        ).fetchone()
    else:
        row = conn.execute(
            f"{_VERSION_SELECT} WHERE version_id = ? AND owner_id = ?",
            (version_id, principal.owner_id),
        ).fetchone()
    if row is None:
        raise WorkflowError(404, "version_not_found", "Workflow version not found")
    return _version_from_row(row)


__all__ = [
    "artifact_digest",
    "freeze_version",
    "get_version",
    "list_versions",
]
