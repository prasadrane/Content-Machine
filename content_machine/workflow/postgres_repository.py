"""Unmounted PostgreSQL workflow repository with explicit transaction boundaries.

The caller provides a dedicated, idle psycopg3 connection and a verified hosted
principal. Each method owns and completes its transaction before returning.
Integration with authentication, pooling and hosted routes is a separate gate.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import hmac
import json
import uuid

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import _acknowledged, _conflict, _invalid_item, _patch_value, _reject_explicit_nulls
from content_machine.workflow.persistence import WorkflowResult, canonical_json, request_digest
from content_machine.workflow.schema_types import Stage, VersionPurpose
from content_machine.workflow.schemas import ContentItem, ContentVersion, Principal, utc_timestamp
from content_machine.workflow.versions import artifact_digest

_ITEMS = (
    'SELECT item_id, owner_id, title, destination, format, stage, working_revision, '
    'context_json, artifact_json, parent_version_id, active_approval_id, created_at, updated_at '
    'FROM public.workflow_items'
)
_VERSIONS = (
    'SELECT version_id, item_id, owner_id, revision, context_json, artifact_json, '
    'destination, format, artifact_digest, purpose, created_by, created_at '
    'FROM public.workflow_versions'
)


def _mapping(cursor, row):
    if row is None or isinstance(row, Mapping):
        return row
    return {column.name: value for column, value in zip(cursor.description, row)}


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def _timestamp(value):
    return utc_timestamp(value) if isinstance(value, datetime) else value


def _item(row):
    data = dict(row)
    data['owner_id'] = str(data['owner_id'])
    data['context'] = _json(data.pop('context_json'))
    data['artifact'] = _json(data.pop('artifact_json'))
    data['created_at'] = _timestamp(data['created_at'])
    data['updated_at'] = _timestamp(data['updated_at'])
    return ContentItem.model_validate(data)


def _version(row):
    data = dict(row)
    data['owner_id'] = str(data['owner_id'])
    data['created_by'] = str(data['created_by'])
    data['context'] = _json(data.pop('context_json'))
    data['artifact'] = _json(data.pop('artifact_json'))
    data['created_at'] = _timestamp(data['created_at'])
    return ContentVersion.model_validate(data)


class PostgresWorkflowRepository:
    """Owned Postgres item and immutable version operations; not yet mounted."""

    def __init__(self, conn):
        self.conn = conn

    def _check(self, principal):
        if not isinstance(principal, Principal) or principal.mode.value != 'hosted_verified':
            raise WorkflowError(401, 'unauthenticated', 'A verified hosted identity is required')
        try:
            if str(uuid.UUID(principal.owner_id)) != principal.owner_id:
                raise ValueError('noncanonical owner')
        except (ValueError, AttributeError) as exc:
            raise WorkflowError(401, 'unauthenticated', 'A verified hosted identity is required') from exc
        if self.conn.info.transaction_status != 0:
            raise WorkflowError(409, 'operation_transaction_open', 'A dedicated idle connection is required')

    def _lock_request(self, principal, key):
        if not isinstance(key, str) or not key.strip():
            raise WorkflowError(422, 'invalid_request', 'Idempotency-Key is required')
        self.conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s::text || ':' || %s::text, 0))",
            (principal.owner_id, key),
        )

    def _replay(self, principal, key, method, path, digest):
        cursor = self.conn.execute(
            'SELECT method, resource_path, request_digest, response_status, response_body_json '
            'FROM public.workflow_idempotency WHERE owner_id = %s AND request_id = %s',
            (principal.owner_id, key),
        )
        row = _mapping(cursor, cursor.fetchone())
        if row is None:
            return None
        if (row['method'] != method or row['resource_path'] != path
                or not hmac.compare_digest(row['request_digest'], digest)):
            raise WorkflowError(409, 'idempotency_conflict', 'Idempotency-Key was already used for a different request')
        return WorkflowResult(row['response_status'], _json(row['response_body_json']))

    def _record(self, principal, key, method, path, digest, status, body):
        self.conn.execute(
            'INSERT INTO public.workflow_idempotency '
            '(owner_id, request_id, method, resource_path, request_digest, response_status, response_body_json, created_at) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (principal.owner_id, key, method, path, digest, status, canonical_json(body), utc_timestamp()),
        )

    def _owned(self, principal, item_id, *, lock=False):
        sql = _ITEMS + ' WHERE item_id = %s AND owner_id = %s' + (' FOR UPDATE' if lock else '')
        cursor = self.conn.execute(sql, (item_id, principal.owner_id))
        row = _mapping(cursor, cursor.fetchone())
        if row is None:
            raise WorkflowError(404, 'item_not_found', 'Workflow item not found')
        return _item(row)

    def get_item(self, principal, item_id):
        self._check(principal)
        with self.conn.transaction():
            result = self._owned(principal, item_id)
        return result

    def list_items(self, principal):
        self._check(principal)
        with self.conn.transaction():
            cursor = self.conn.execute(_ITEMS + ' WHERE owner_id = %s ORDER BY updated_at DESC, item_id ASC',
                                       (principal.owner_id,))
            result = [_item(_mapping(cursor, row)) for row in cursor.fetchall()]
        return result

    def create_item(self, principal, payload, *, request_id):
        self._check(principal)
        if not isinstance(request_id, str) or not request_id.strip():
            raise WorkflowError(422, 'invalid_request', 'Idempotency-Key is required')
        path = '/api/workflow/items'
        digest = request_digest('POST', path, payload.model_dump(mode='json'))
        with self.conn.transaction():
            self._lock_request(principal, request_id)
            replay = self._replay(principal, request_id, 'POST', path, digest)
            if replay is not None:
                result = replay
            else:
                now = utc_timestamp()
                item = ContentItem.new(item_id=f'itm_{uuid.uuid4().hex}', principal=principal, payload=payload, now=now)
                self.conn.execute(
                    'INSERT INTO public.workflow_items '
                    '(item_id, owner_id, title, destination, format, stage, working_revision, context_json, artifact_json, '
                    'parent_version_id, active_approval_id, created_at, updated_at) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (item.item_id, principal.owner_id, item.title, item.destination, item.format, item.stage.value,
                     item.working_revision, canonical_json(item.context.model_dump(mode='json')),
                     canonical_json(item.artifact.model_dump(mode='json')), None, None, now, now),
                )
                body = {'item': item.model_dump(mode='json')}
                self._record(principal, request_id, 'POST', path, digest, 201, body)
                result = WorkflowResult(201, body)
        return result

    def save_item(self, principal, item_id, patch, *, request_id):
        self._check(principal)
        if not isinstance(request_id, str) or not request_id.strip():
            raise WorkflowError(422, 'invalid_request', 'Idempotency-Key is required')
        path = f'/api/workflow/items/{item_id}'
        digest = request_digest('PATCH', path, patch.model_dump(mode='json', exclude_unset=True))
        with self.conn.transaction():
            self._lock_request(principal, request_id)
            replay = self._replay(principal, request_id, 'PATCH', path, digest)
            if replay is not None:
                result = replay
            else:
                _reject_explicit_nulls(patch)
                item = self._owned(principal, item_id, lock=True)
                if item.working_revision != patch.expected_revision:
                    raise _conflict(item)
                destination = _patch_value(patch, 'destination', item.destination)
                format = _patch_value(patch, 'format', item.format)
                context = _patch_value(patch, 'context', item.context)
                artifact = _patch_value(patch, 'artifact', item.artifact)
                changed = (destination != item.destination or format != item.format
                           or context != item.context or artifact != item.artifact)
                data = item.model_dump(mode='python')
                data.update(title=_patch_value(patch, 'title', item.title), destination=destination, format=format,
                            stage=_patch_value(patch, 'stage', None) or (Stage.DRAFT_REVIEW if changed else item.stage),
                            context=context, artifact=artifact, working_revision=item.working_revision + int(changed),
                            active_approval_id=None if changed else item.active_approval_id, updated_at=utc_timestamp())
                try:
                    merged = ContentItem.model_validate(data)
                except ValueError as exc:
                    raise _invalid_item(exc) from exc
                if merged.stage == Stage.EXPORT and not self._approved(principal, merged):
                    raise WorkflowError(409, 'approval_required', 'An approval for this item revision is required before export')
                cursor = self.conn.execute(
                    'UPDATE public.workflow_items SET title = %s, destination = %s, format = %s, stage = %s, '
                    'working_revision = %s, context_json = %s, artifact_json = %s, '
                    'active_approval_id = %s, updated_at = %s '
                    'WHERE item_id = %s AND owner_id = %s AND working_revision = %s',
                    (merged.title, merged.destination, merged.format, merged.stage.value, merged.working_revision,
                     canonical_json(merged.context.model_dump(mode='json')), canonical_json(merged.artifact.model_dump(mode='json')),
                     merged.active_approval_id, merged.updated_at, item_id, principal.owner_id, patch.expected_revision),
                )
                if cursor.rowcount != 1:
                    raise _conflict(item)
                body = {'item': merged.model_dump(mode='json')}
                self._record(principal, request_id, 'PATCH', path, digest, 200, body)
                result = WorkflowResult(200, body)
        return result

    def _approved(self, principal, item):
        if item.active_approval_id is None:
            return False
        cursor = self.conn.execute(
            'SELECT 1 FROM public.workflow_approvals a JOIN public.workflow_versions v '
            'ON v.version_id = a.version_id AND v.owner_id = a.owner_id AND v.item_id = a.item_id '
            'WHERE a.approval_id = %s AND a.owner_id = %s AND a.item_id = %s AND v.revision = %s '
            'AND a.destination = %s AND a.format = %s',
            (item.active_approval_id, principal.owner_id, item.item_id, item.working_revision, item.destination, item.format),
        )
        return cursor.fetchone() is not None

    def freeze_version(self, principal, item_id, expected_revision, purpose):
        self._check(principal)
        try:
            purpose = VersionPurpose(purpose)
        except (TypeError, ValueError) as exc:
            raise WorkflowError(422, 'invalid_version_purpose', 'A valid version purpose is required') from exc
        with self.conn.transaction():
            item = self._owned(principal, item_id, lock=True)
            if item.working_revision != expected_revision:
                raise WorkflowError(409, 'revision_conflict', 'The item revision changed before this freeze', current=_acknowledged(item))
            cursor = self.conn.execute(_VERSIONS + ' WHERE owner_id = %s AND item_id = %s AND revision = %s',
                                       (principal.owner_id, item_id, expected_revision))
            existing = _mapping(cursor, cursor.fetchone())
            if existing is not None:
                result = _version(existing)
            else:
                version = ContentVersion(
                    version_id=f'ver_{uuid.uuid4().hex}', item_id=item_id, owner_id=principal.owner_id,
                    revision=item.working_revision, context=item.context, artifact=item.artifact,
                    destination=item.destination, format=item.format,
                    artifact_digest=artifact_digest(item.destination, item.format, item.artifact),
                    purpose=purpose, created_by=principal.owner_id, created_at=utc_timestamp(),
                )
                self.conn.execute(
                    'INSERT INTO public.workflow_versions '
                    '(version_id, item_id, owner_id, revision, context_json, artifact_json, destination, format, '
                    'artifact_digest, purpose, created_by, created_at) '
                    'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (version.version_id, item_id, principal.owner_id, version.revision,
                     canonical_json(version.context.model_dump(mode='json')), canonical_json(version.artifact.model_dump(mode='json')),
                     version.destination, version.format, version.artifact_digest, version.purpose.value,
                     principal.owner_id, version.created_at),
                )
                result = version
        return result

    def get_version(self, principal, item_id, version_id):
        self._check(principal)
        with self.conn.transaction():
            self._owned(principal, item_id)
            cursor = self.conn.execute(_VERSIONS + ' WHERE version_id = %s AND item_id = %s AND owner_id = %s',
                                       (version_id, item_id, principal.owner_id))
            row = _mapping(cursor, cursor.fetchone())
            if row is None:
                raise WorkflowError(404, 'version_not_found', 'Workflow version not found')
            result = _version(row)
        return result

    def list_versions(self, principal, item_id):
        self._check(principal)
        with self.conn.transaction():
            self._owned(principal, item_id)
            cursor = self.conn.execute(_VERSIONS + ' WHERE owner_id = %s AND item_id = %s '
                                       'ORDER BY revision DESC, created_at DESC, version_id ASC',
                                       (principal.owner_id, item_id))
            result = [_version(_mapping(cursor, row)) for row in cursor.fetchall()]
        return result

