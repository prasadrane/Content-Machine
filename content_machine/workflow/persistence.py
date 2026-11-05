"""Shared SQLite persistence helpers for workflow services.

Workflow mutations are acknowledged with :class:`WorkflowResult`, whose body is
stored verbatim for idempotent replay. Request digests cover the concrete HTTP
method, concrete resource path and canonical request body.

``atomic_write`` opens an immediate transaction when the caller has none, or a
savepoint when the caller already owns a larger transaction. It never commits a
caller-owned transaction. Public operations that use it return only after their
own transaction commits.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator

from content_machine.workflow.errors import WorkflowError

SAVEPOINT_NAME = "workflow_atomic_write"


@dataclass(frozen=True)
class WorkflowResult:
    """A committed mutation acknowledgement or an idempotent replay.

    Top-level operations return after their own transaction commits. When a
    composed operation runs inside a caller-owned transaction, the enclosing
    caller must commit before the HTTP layer acknowledges success.
    """

    status_code: int
    body: dict[str, Any]


def canonical_json(value: Any) -> str:
    """Serialize JSON deterministically while preserving every string character."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def request_digest(method: str, resource_path: str, body: Any) -> str:
    """Return the canonical digest of a concrete request."""

    material = canonical_json(
        {"method": method, "resource_path": resource_path, "body": body}
    )
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def find_idempotent(
    conn: sqlite3.Connection,
    owner_id: str,
    request_id: str,
    *,
    method: str,
    resource_path: str,
    digest: str,
) -> WorkflowResult | None:
    """Replay an owner-scoped success or reject a changed request under its key."""

    row = conn.execute(
        "SELECT method, resource_path, request_digest, response_status,"
        " response_body_json FROM workflow_idempotency"
        " WHERE owner_id = ? AND request_id = ?",
        (owner_id, request_id),
    ).fetchone()
    if row is None:
        return None
    stored_method, stored_path, stored_digest, status, body_json = row
    if (
        stored_method != method
        or stored_path != resource_path
        or not hmac.compare_digest(stored_digest, digest)
    ):
        raise WorkflowError(
            409,
            "idempotency_conflict",
            "Idempotency-Key was already used for a different request",
        )
    return WorkflowResult(int(status), json.loads(body_json))


def record_idempotent(
    conn: sqlite3.Connection,
    owner_id: str,
    request_id: str,
    *,
    method: str,
    resource_path: str,
    digest: str,
    response_status: int,
    body: dict[str, Any],
    created_at: str,
) -> None:
    """Record a successful response inside the caller's current transaction."""

    conn.execute(
        "INSERT INTO workflow_idempotency("
        " owner_id, request_id, method, resource_path, request_digest,"
        " response_status, response_body_json, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            owner_id,
            request_id,
            method,
            resource_path,
            digest,
            response_status,
            canonical_json(body),
            created_at,
        ),
    )


def _rollback(conn: sqlite3.Connection, nested: bool) -> None:
    if nested:
        conn.execute(f"ROLLBACK TO SAVEPOINT {SAVEPOINT_NAME}")
        conn.execute(f"RELEASE SAVEPOINT {SAVEPOINT_NAME}")
    else:
        conn.rollback()


@contextmanager
def atomic_write(conn: sqlite3.Connection) -> Iterator[None]:
    """Serialize a workflow mutation atomically without committing caller work.

    Body failures and finalization failures (a top-level COMMIT or a nested
    RELEASE) both roll back before propagating, so a commit error cannot leave
    a rejected mutation or its success record pending on the connection.
    """

    nested = conn.in_transaction
    if nested:
        conn.execute(f"SAVEPOINT {SAVEPOINT_NAME}")
    else:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        _rollback(conn, nested)
        raise
    try:
        if nested:
            conn.execute(f"RELEASE SAVEPOINT {SAVEPOINT_NAME}")
        else:
            conn.commit()
    except BaseException:
        _rollback(conn, nested)
        raise


__all__ = [
    "WorkflowResult",
    "atomic_write",
    "canonical_json",
    "find_idempotent",
    "record_idempotent",
    "request_digest",
]
