"""Short, committed operation claims around external provider work.

Only the caller receiving ``created=True`` may invoke a provider. Replays return
the existing pending or terminal operation and never cause a second invocation.
"""
from __future__ import annotations

import json
import sqlite3
import uuid

from content_machine.workflow.context import build_editorial_snapshot
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.operation_storage import (
    OPERATION_MIGRATION_STATEMENTS, decode_editorial_snapshot, get_operation, list_operations,
)
from content_machine.workflow.persistence import (
    atomic_write, canonical_json, find_idempotent, record_idempotent, request_digest,
)
from content_machine.workflow.schema_types import VersionPurpose
from content_machine.workflow.schemas import Principal, utc_timestamp
from content_machine.workflow.versions import freeze_version


def begin_operation(conn: sqlite3.Connection, principal: Principal, item_id: str,
                    expected_revision: int, kind: str, request_id: str) -> tuple[dict, bool]:
    """Freeze and commit a request before returning permission to call a provider."""
    if conn.in_transaction:
        raise WorkflowError(409, 'operation_transaction_open',
                            'An operation must begin outside an existing transaction.')
    if kind not in ('generate', 'review') or type(expected_revision) is not int or expected_revision < 1:
        raise WorkflowError(422, 'invalid_request', 'A valid operation kind and revision are required')
    if not isinstance(request_id, str) or not request_id.strip():
        raise WorkflowError(422, 'invalid_request', 'Idempotency-Key is required')
    path = f'/api/workflow/items/{item_id}/{kind}'
    digest = request_digest('POST', path, {'expected_revision': expected_revision})
    with atomic_write(conn):
        replay = find_idempotent(conn, principal.owner_id, request_id,
                                 method='POST', resource_path=path, digest=digest)
        if replay is not None:
            return get_operation(conn, principal, item_id, replay.body['operation_id']), False
        # The frozen version enum predates generation and uses REVIEW as its
        # generic AI-input purpose. Only operation.kind/state records whether
        # review or generation was requested and whether it completed.
        version = freeze_version(conn, principal, item_id, expected_revision, VersionPurpose.REVIEW)
        snapshot = build_editorial_snapshot(conn, principal, item_id, version.version_id)
        operation_id = f'op_{uuid.uuid4().hex}'
        now = utc_timestamp()
        conn.execute(
            'INSERT INTO workflow_operations'
            ' (operation_id, owner_id, item_id, kind, input_version_id, context_snapshot_json,'
            ' state, request_id, result_json, error_json, started_at, finished_at)'
            " VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, NULL, NULL, ?, NULL)",
            (operation_id, principal.owner_id, item_id, kind, version.version_id,
             canonical_json(version.context.model_dump(mode='json')), request_id, now),
        )
        conn.execute(
            'INSERT INTO workflow_operation_inputs'
            ' (operation_id, owner_id, item_id, request_digest, editorial_snapshot_json) VALUES (?, ?, ?, ?, ?)',
            (operation_id, principal.owner_id, item_id, digest, snapshot.to_json()),
        )
        record_idempotent(conn, principal.owner_id, request_id, method='POST', resource_path=path,
                          digest=digest, response_status=202, body={'operation_id': operation_id}, created_at=now)
        result = get_operation(conn, principal, item_id, operation_id)
    return result, True


def _finish(conn: sqlite3.Connection, principal: Principal, item_id: str,
            operation_id: str, state: str, value: dict) -> dict:
    if conn.in_transaction:
        raise WorkflowError(409, 'operation_transaction_open',
                            'An operation must finish outside an existing transaction.')
    if not isinstance(value, dict):
        raise WorkflowError(422, 'invalid_request', 'Operation result must be an object')
    try:
        encoded = canonical_json(value)
        # Require valid JSON values, not JavaScript-invalid NaN or infinity.
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise WorkflowError(422, 'invalid_request', 'Operation result must be valid JSON') from error
    with atomic_write(conn):
        operation = get_operation(conn, principal, item_id, operation_id)
        field = 'result' if state == 'completed' else 'error'
        if operation['state'] != 'pending':
            if operation['state'] == state and operation[field] == value:
                return operation
            raise WorkflowError(409, 'operation_state_conflict', 'This operation already has a different outcome.')
        conn.execute('UPDATE workflow_operations SET state=?, result_json=?, error_json=?, finished_at=?'
                     ' WHERE owner_id=? AND item_id=? AND operation_id=? AND state=?',
                     (state, encoded if state == 'completed' else None,
                      encoded if state == 'failed' else None, utc_timestamp(),
                      principal.owner_id, item_id, operation_id, 'pending'))
        result = get_operation(conn, principal, item_id, operation_id)
    return result


def complete_operation(conn: sqlite3.Connection, principal: Principal, item_id: str,
                       operation_id: str, result: dict) -> dict:
    return _finish(conn, principal, item_id, operation_id, 'completed', result)


def fail_operation(conn: sqlite3.Connection, principal: Principal, item_id: str,
                   operation_id: str, error: dict) -> dict:
    return _finish(conn, principal, item_id, operation_id, 'failed', error)


__all__ = [
    'OPERATION_MIGRATION_STATEMENTS', 'begin_operation', 'complete_operation',
    'fail_operation', 'get_operation', 'list_operations', 'decode_editorial_snapshot',
]
