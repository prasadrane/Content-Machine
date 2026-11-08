"""Explicit local import of supplied legacy records, without source discovery.

Run against an authorized backed-up workspace. This module neither reads legacy
paths nor deletes/rewrites source tables. An operator supplies classification,
evidence and per-record owner mappings; names/content never establish lineage.
Original payloads (including comments and unverified historical approvals) are
kept in an immutable archive. Only proven actual work becomes a new unapproved
working item. Unknown and proven synthetic records remain quarantined. No HTTP
route or application startup/migration hook is installed by this module.
"""
from collections.abc import Mapping
import hashlib
import json
import sqlite3
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import create_item, save_item
from content_machine.workflow.persistence import atomic_write
from content_machine.workflow.schemas import Artifact, Context, ItemCreate, ItemPatch, Principal, utc_timestamp

MAX_BATCH = 200
MAX_RECORD_BYTES = 5_000_000


class LegacyRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    legacy_id: str = Field(min_length=1, max_length=200)
    provenance: Literal['actual', 'proven_synthetic', 'unknown']
    provenance_evidence: str | None = Field(default=None, max_length=20_000)
    title: str = Field(min_length=1, max_length=500)
    destination: str
    format: str
    context: Context = Field(default_factory=Context)
    artifact: Artifact = Field(default_factory=Artifact)
    legacy_payload: dict[str, Any]

    @model_validator(mode='after')
    def validate_record(self):
        if not self.legacy_id.strip() or not self.title.strip():
            raise ValueError('Legacy identifier and title must be nonblank')
        if self.provenance != 'unknown' and not (self.provenance_evidence or '').strip():
            raise ValueError('Classified provenance requires explicit evidence')
        ItemCreate(title=self.title, destination=self.destination, format=self.format)
        return self


IMPORT_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS workflow_legacy_imports (
      source_namespace TEXT NOT NULL, legacy_id TEXT NOT NULL,
      input_digest TEXT NOT NULL, record_json TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN ('imported','synthetic_quarantined','unknown_quarantined')),
      owner_id TEXT, item_id TEXT, imported_at TEXT NOT NULL,
      historical_approval TEXT NOT NULL DEFAULT 'unknown' CHECK(historical_approval='unknown'),
      PRIMARY KEY(source_namespace, legacy_id), UNIQUE(item_id, owner_id),
      FOREIGN KEY(item_id, owner_id) REFERENCES workflow_items(item_id, owner_id),
      CHECK((state='imported' AND owner_id IS NOT NULL AND item_id IS NOT NULL)
         OR (state!='imported' AND owner_id IS NULL AND item_id IS NULL))
    )""",
    """CREATE TRIGGER IF NOT EXISTS workflow_legacy_imports_no_update
       BEFORE UPDATE ON workflow_legacy_imports BEGIN
         SELECT RAISE(ABORT, 'legacy import archive is immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS workflow_legacy_imports_no_delete
       BEFORE DELETE ON workflow_legacy_imports BEGIN
         SELECT RAISE(ABORT, 'legacy import archive is immutable'); END""",
)


def initialize_import_schema(conn: sqlite3.Connection) -> None:
    """Explicit additive archive setup; caller chooses the backed-up database."""
    with atomic_write(conn):
        for statement in IMPORT_SCHEMA:
            conn.execute(statement)


def _invalid(detail='Supply valid classified records and explicit owner mappings'):
    return WorkflowError(422, 'legacy_import_invalid', detail)


def _namespace(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise _invalid('An explicit source namespace of at most 200 characters is required')
    return value


def _json_value(value):
    # Do not let JSON coercion silently turn numeric mapping keys into strings,
    # or encode arbitrary application objects in historical records.
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise _invalid('Archived JSON object keys must be strings')
        for child in value.values():
            _json_value(child)
    elif isinstance(value, list):
        for child in value:
            _json_value(child)
    elif value is not None and type(value) not in (str, int, float, bool):
        raise _invalid('Archived payloads must contain JSON values only')


def _prepared(record):
    try:
        # Revalidate even a caller-provided model copy; model_copy(update=...)
        # and mutable nested values must not bypass the import contract.
        raw = record.model_dump(mode='python') if isinstance(record, LegacyRecord) else record
        model = LegacyRecord.model_validate(raw)
        value = model.model_dump(mode='python')
        _json_value(value)
        if model.provenance == 'actual':
            json.dumps({'title': model.title, 'context': value['context'], 'artifact': value['artifact']},
                       ensure_ascii=False).encode('utf-8')
        encoded = json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':'))
        if len(encoded.encode('ascii')) > MAX_RECORD_BYTES:
            raise _invalid('One archived record exceeds the supported size')
        return model, encoded, 'sha256:' + hashlib.sha256(encoded.encode('ascii')).hexdigest()
    except WorkflowError:
        raise
    except (ValidationError, TypeError, ValueError, RecursionError):
        raise _invalid() from None


def _read(conn, namespace, legacy_id):
    try:
        return conn.execute('SELECT source_namespace, legacy_id, input_digest, record_json, state, owner_id, '
            'item_id, imported_at, historical_approval FROM workflow_legacy_imports '
            'WHERE source_namespace=? AND legacy_id=?', (namespace, legacy_id)).fetchone()
    except sqlite3.OperationalError as exc:
        if 'no such table: workflow_legacy_imports' in str(exc):
            raise WorkflowError(503, 'legacy_import_unavailable', 'Initialize the explicit import archive first') from None
        raise


def _summary(row):
    return {key: row[key] for key in ('source_namespace', 'legacy_id', 'state', 'owner_id', 'item_id', 'historical_approval')}


def inspect_import(conn, source_namespace: str, legacy_id: str) -> dict:
    """Trusted local operator inspection, including recoverable original data.

    This is not an authenticated public API: quarantine entries have no owner.
    Never mount it as a browser route without a separately reviewed policy.
    """
    namespace = _namespace(source_namespace)
    if not isinstance(legacy_id, str) or not legacy_id.strip():
        raise _invalid('A legacy record identifier is required')
    row = _read(conn, namespace, legacy_id)
    if row is None:
        raise WorkflowError(404, 'legacy_import_not_found', 'Archived import record not found')
    return {**_summary(row), 'record': json.loads(row['record_json']),
            'input_digest': row['input_digest'], 'imported_at': row['imported_at']}


def import_legacy_records(conn, source_namespace: str, records: list, *, owner_mapping: Mapping) -> list[dict]:
    """Atomically archive supplied records and import explicitly mapped actual work.

    The mapping keys are legacy IDs in this namespace, and values are trusted
    operator-supplied Principals. Extra mappings are rejected. Changed payload,
    provenance or owner never overwrites an earlier import. Repeat calls return
    the original mapping without recreating, seeding or replacing edited work.
    Historical approved/published flags stay opaque archive data, never authority.
    """
    namespace = _namespace(source_namespace)
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_BATCH or not isinstance(owner_mapping, Mapping):
        raise _invalid('Supply 1-200 explicit records and an owner mapping')
    prepared = [_prepared(record) for record in records]
    identifiers = [entry[0].legacy_id for entry in prepared]
    if len(set(identifiers)) != len(identifiers) or set(owner_mapping) - set(identifiers):
        raise _invalid('Duplicate record identifiers or unrelated owner mappings')
    for model, _, _ in prepared:
        principal = owner_mapping.get(model.legacy_id)
        if model.provenance == 'actual':
            if not isinstance(principal, Principal) or not principal.owner_id.strip():
                raise _invalid('Actual legacy work requires an explicit verified owner mapping')
        elif principal is not None or model.legacy_id in owner_mapping:
            raise _invalid('Unknown or synthetic lineage cannot be assigned to a creator by this import')
    result = []
    with atomic_write(conn):
        for model, encoded, digest in prepared:
            principal = owner_mapping.get(model.legacy_id)
            owner = principal.owner_id if principal is not None else None
            existing = _read(conn, namespace, model.legacy_id)
            if existing is not None:
                if existing['input_digest'] != digest or existing['owner_id'] != owner:
                    raise WorkflowError(409, 'legacy_import_conflict',
                                        'This legacy identifier already has a different immutable import')
                result.append(_summary(existing))
                continue
            item_id = None
            state = 'synthetic_quarantined' if model.provenance == 'proven_synthetic' else 'unknown_quarantined'
            if model.provenance == 'actual':
                created = create_item(conn, principal, ItemCreate(title=model.title,
                    destination=model.destination, format=model.format), request_id='legacy-create-' + uuid.uuid4().hex).body['item']
                item_id = created['item_id']
                save_item(conn, principal, item_id, ItemPatch(expected_revision=1,
                    context=model.context, artifact=model.artifact), request_id='legacy-save-' + uuid.uuid4().hex)
                state = 'imported'
            conn.execute('INSERT INTO workflow_legacy_imports (source_namespace,legacy_id,input_digest,record_json,'
                'state,owner_id,item_id,imported_at,historical_approval) VALUES (?,?,?,?,?,?,?,?,?)',
                (namespace, model.legacy_id, digest, encoded, state, owner, item_id, utc_timestamp(), 'unknown'))
            result.append(_summary(_read(conn, namespace, model.legacy_id)))
    return result


__all__ = ['LegacyRecord', 'initialize_import_schema', 'import_legacy_records', 'inspect_import']
