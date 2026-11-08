"""Immutable operation-input migration and owner-scoped operation reads."""
from __future__ import annotations

import json
import sqlite3

from content_machine.workflow.context import (
    ActivePreference, ArtifactSnapshot, CreatorProfile, EditorialSnapshot, ItemContext, SourceEvidence,
)
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item

OPERATION_MIGRATION_STATEMENTS = (
    'CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_operations_identity'
    ' ON workflow_operations (operation_id, owner_id, item_id)',
    '''CREATE TABLE IF NOT EXISTS workflow_operation_inputs (
       operation_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, item_id TEXT NOT NULL,
       request_digest TEXT NOT NULL, editorial_snapshot_json TEXT NOT NULL,
       FOREIGN KEY (operation_id, owner_id, item_id)
         REFERENCES workflow_operations (operation_id, owner_id, item_id))''',
    '''CREATE TRIGGER IF NOT EXISTS workflow_operation_inputs_no_update
       BEFORE UPDATE ON workflow_operation_inputs BEGIN
       SELECT RAISE(ABORT, 'operation inputs are immutable'); END''',
    '''CREATE TRIGGER IF NOT EXISTS workflow_operation_inputs_no_delete
       BEFORE DELETE ON workflow_operation_inputs BEGIN
       SELECT RAISE(ABORT, 'operation inputs are immutable'); END''',
)


def decode_editorial_snapshot(value: str | dict) -> EditorialSnapshot:
    """Decode a stored snapshot without reading live settings for old inputs."""
    data = json.loads(value) if isinstance(value, str) else value
    context = data['context']
    profile = data['profile']
    return EditorialSnapshot(
        owner_id=data['owner_id'], item_id=data['item_id'], version_id=data['version_id'],
        revision=data['revision'], destination=data['destination'], format=data['format'],
        title=data.get('title'),
        context=ItemContext(notes=context['notes'], experience=context['experience'],
                            interpretation=context['interpretation'],
                            sources=tuple(SourceEvidence(**source) for source in context['sources']),
                            preference_snapshot_id=context['preference_snapshot_id']),
        artifact=ArtifactSnapshot(segments=tuple(data['artifact']['segments'])),
        profile=CreatorProfile(**profile) if profile is not None else None,
        preferences=tuple(ActivePreference(**entry) for entry in data['preferences']),
    )


def _decode(row: sqlite3.Row) -> dict:
    operation = dict(row)
    operation['context_snapshot'] = json.loads(operation.pop('context_snapshot_json'))
    for field in ('result', 'error'):
        raw = operation.pop(f'{field}_json')
        operation[field] = json.loads(raw) if raw is not None else None
    raw = operation.pop('editorial_snapshot_json')
    operation['editorial_snapshot'] = decode_editorial_snapshot(raw).as_dict() if raw is not None else None
    return operation


_SELECT = (
    'SELECT o.operation_id, o.owner_id, o.item_id, o.kind, o.input_version_id,'
    ' o.context_snapshot_json, o.state, o.request_id, o.result_json, o.error_json,'
    ' o.started_at, o.finished_at, i.editorial_snapshot_json'
    ' FROM workflow_operations o LEFT JOIN workflow_operation_inputs i'
    ' ON i.operation_id=o.operation_id AND i.owner_id=o.owner_id AND i.item_id=o.item_id'
)


def get_operation(conn: sqlite3.Connection, principal, item_id: str, operation_id: str) -> dict:
    get_item(conn, principal, item_id)
    row = conn.execute(_SELECT + ' WHERE o.owner_id=? AND o.item_id=? AND o.operation_id=?',
                       (principal.owner_id, item_id, operation_id)).fetchone()
    if row is None:
        raise WorkflowError(404, 'operation_not_found', 'Workflow operation not found')
    return _decode(row)


def list_operations(conn: sqlite3.Connection, principal, item_id: str) -> list[dict]:
    get_item(conn, principal, item_id)
    rows = conn.execute(_SELECT + ' WHERE o.owner_id=? AND o.item_id=?'
                        ' ORDER BY o.started_at DESC, o.operation_id',
                        (principal.owner_id, item_id)).fetchall()
    return [_decode(row) for row in rows]
