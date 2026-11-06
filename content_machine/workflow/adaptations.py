"""Linked workflow adaptations from an approved source version.

An adaptation is a new owned item, never a mutation of its source. The exact
source version must pass the accepted historical export integrity and approval
checks. Its frozen context becomes the target's context, its version ID becomes
the target's parent, and the target starts at revision 1 with an empty artifact,
no active approval and no review or operation success.

The initial target revision is frozen with the ``adaptation`` purpose in the
same transaction as the item and idempotency record. A failure therefore leaves
the source and its approval untouched and creates no partial target.
"""

from __future__ import annotations

import sqlite3
import uuid

from content_machine.workflow.exports import export_version
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
    AdaptRequest,
    Artifact,
    ContentItem,
    Principal,
    utc_timestamp,
)
from content_machine.workflow.versions import freeze_version, get_version

ADAPT_PATH = "/api/workflow/items/{item_id}/adapt"


def _require_request_id(request_id: str) -> None:
    if not isinstance(request_id, str) or not request_id.strip():
        raise WorkflowError(422, "invalid_request", "Idempotency-Key is required")


def adapt_version(
    conn: sqlite3.Connection,
    principal: Principal,
    source_item_id: str,
    payload: AdaptRequest,
    *,
    request_id: str,
) -> WorkflowResult:
    """Create an independent unapproved item from one approved source version.

    Matching idempotent requests replay before ownership or approval checks.
    The source item's current working text is never copied: only the frozen
    source version's context and ancestry are retained.
    """

    _require_request_id(request_id)
    method = "POST"
    path = ADAPT_PATH.format(item_id=source_item_id)
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

        source_item = get_item(conn, principal, source_item_id)
        source_version = get_version(
            conn,
            principal,
            payload.source_version_id,
            item_id=source_item_id,
        )
        export_version(
            conn,
            principal,
            source_item_id,
            source_version.version_id,
        )

        now = utc_timestamp()
        target = ContentItem(
            item_id=f"itm_{uuid.uuid4().hex}",
            owner_id=principal.owner_id,
            title=source_item.title,
            destination=payload.destination,
            format=payload.format,
            stage=Stage.DRAFT_REVIEW,
            working_revision=1,
            context=source_version.context.model_copy(deep=True),
            artifact=Artifact(),
            parent_version_id=source_version.version_id,
            active_approval_id=None,
            created_at=now,
            updated_at=now,
        )
        conn.execute(
            "INSERT INTO workflow_items("
            " item_id, owner_id, title, destination, format, stage,"
            " working_revision, context_json, artifact_json,"
            " parent_version_id, active_approval_id, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                target.item_id,
                target.owner_id,
                target.title,
                target.destination,
                target.format,
                target.stage.value,
                target.working_revision,
                canonical_json(target.context.model_dump(mode="json")),
                canonical_json(target.artifact.model_dump(mode="json")),
                target.parent_version_id,
                target.active_approval_id,
                target.created_at,
                target.updated_at,
            ),
        )
        freeze_version(
            conn,
            principal,
            target.item_id,
            expected_revision=1,
            purpose=VersionPurpose.ADAPTATION,
        )

        body = {"item": target.model_dump(mode="json")}
        record_idempotent(
            conn,
            principal.owner_id,
            request_id,
            method=method,
            resource_path=path,
            digest=digest,
            response_status=201,
            body=body,
            created_at=now,
        )
        return WorkflowResult(201, body)


__all__ = ["ADAPT_PATH", "adapt_version"]
