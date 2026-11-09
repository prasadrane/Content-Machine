"""Owner-scoped preferences with explicit activation and governed changes."""
from __future__ import annotations

import sqlite3
import uuid

from content_machine.lessons.store import CONFLICT_THRESHOLD, DEFAULT_CAP, DefaultEmbedder, _cosine
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import (
    WorkflowResult, atomic_write, find_idempotent, record_idempotent, request_digest,
)
from content_machine.workflow.schemas import Principal, require_request_id, utc_timestamp

# Integrators add these statements to the existing atomic workflow migration.
# Legacy rows stay in ``lessons`` until explicitly mapped in trusted-local mode.
MIGRATION_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS workflow_preferences (
      preference_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, text TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('active','pending','stopped','rejected')),
      origin TEXT NOT NULL CHECK(origin IN ('manual','item','legacy')),
      origin_ref TEXT, conflict_preference_id TEXT, revision INTEGER NOT NULL CHECK(revision >= 1),
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(preference_id, owner_id),
      FOREIGN KEY(conflict_preference_id, owner_id)
        REFERENCES workflow_preferences(preference_id, owner_id)
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS workflow_preferences_legacy_source
       ON workflow_preferences(origin_ref) WHERE origin = 'legacy'""",
    """CREATE INDEX IF NOT EXISTS workflow_preferences_owner_status
       ON workflow_preferences(owner_id, status)""",
    """CREATE TABLE IF NOT EXISTS workflow_preference_events (
      event_id TEXT PRIMARY KEY, preference_id TEXT NOT NULL, owner_id TEXT NOT NULL,
      revision INTEGER NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL,
      event TEXT NOT NULL, created_at TEXT NOT NULL,
      UNIQUE(preference_id, revision),
      FOREIGN KEY(preference_id, owner_id)
        REFERENCES workflow_preferences(preference_id, owner_id)
    )""",
    """CREATE TRIGGER IF NOT EXISTS workflow_preference_events_immutable_update
       BEFORE UPDATE ON workflow_preference_events BEGIN
       SELECT RAISE(ABORT, 'Preference history is immutable'); END""",
    """CREATE TRIGGER IF NOT EXISTS workflow_preference_events_immutable_delete
       BEFORE DELETE ON workflow_preference_events BEGIN
       SELECT RAISE(ABORT, 'Preference history is immutable'); END""",
)


def migrate_preferences(conn: sqlite3.Connection) -> None:
    """Install additive tables inside the caller's migration transaction."""
    for statement in MIGRATION_STATEMENTS:
        conn.execute(statement)


def _validate_text(text: str) -> None:
    if not isinstance(text, str) or not text.strip() or len(text) > 10000:
        raise WorkflowError(422, 'invalid_request', 'Preference must contain 1–10000 characters')


def _owned(conn: sqlite3.Connection, owner: str, preference_id: str) -> dict:
    row = conn.execute(
        'SELECT * FROM workflow_preferences WHERE owner_id=? AND preference_id=?',
        (owner, preference_id),
    ).fetchone()
    if row is None:
        raise WorkflowError(404, 'preference_not_found', 'Preference not found')
    return dict(row)


def list_preferences(conn: sqlite3.Connection, principal: Principal) -> list[dict]:
    rows = conn.execute(
        'SELECT * FROM workflow_preferences WHERE owner_id=? ORDER BY created_at, preference_id',
        (principal.owner_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def preference_history(conn: sqlite3.Connection, principal: Principal, preference_id: str) -> list[dict]:
    _owned(conn, principal.owner_id, preference_id)
    rows = conn.execute(
        'SELECT revision, text, status, event, created_at FROM workflow_preference_events'
        ' WHERE owner_id=? AND preference_id=? ORDER BY revision',
        (principal.owner_id, preference_id),
    ).fetchall()
    return [dict(row) for row in rows]


def _check_activation(conn: sqlite3.Connection, owner: str, text: str,
                      current_id: str | None = None, *, enforce_cap: bool = True) -> None:
    rows = conn.execute(
        "SELECT preference_id, text FROM workflow_preferences WHERE owner_id=? AND status='active'",
        (owner,),
    ).fetchall()
    other = [row for row in rows if row['preference_id'] != current_id]
    if enforce_cap and current_id is None and len(other) >= DEFAULT_CAP:
        raise WorkflowError(409, 'preference_limit', 'The active preference limit is reached. Stop or combine a preference first.')
    model = DefaultEmbedder()
    try:
        candidate = model.encode(text, normalize_embeddings=True)
        vectors = [(row, model.encode(row['text'], normalize_embeddings=True)) for row in other]
    except Exception as exc:
        raise WorkflowError(503, 'preference_check_unavailable', 'Preference conflict checking is unavailable. Try again.') from exc
    for row, existing in vectors:
        # Recompute both vectors in this process because Python hash seeds vary.
        words = set(text.casefold().split())
        other_words = set(row['text'].casefold().split())
        jaccard = len(words & other_words) / len(words | other_words) if words | other_words else 0
        if _cosine(candidate, existing) >= CONFLICT_THRESHOLD or jaccard >= 0.70:
            raise WorkflowError(409, 'preference_conflict', 'A similar active preference already exists.',
                                current={'conflict_preference_id': row['preference_id']})


def _pending_conflict(conn: sqlite3.Connection, owner: str, text: str, *, enforce_cap: bool) -> str | None:
    try:
        _check_activation(conn, owner, text, enforce_cap=enforce_cap)
    except WorkflowError as error:
        if error.code != 'preference_conflict':
            raise
        return error.current['conflict_preference_id']
    return None


def _event(conn: sqlite3.Connection, preference: dict, event: str) -> None:
    conn.execute(
        'INSERT INTO workflow_preference_events'
        ' (event_id, preference_id, owner_id, revision, text, status, event, created_at)'
        ' VALUES (?,?,?,?,?,?,?,?)',
        (f"pev_{uuid.uuid4().hex}", preference['preference_id'], preference['owner_id'],
         preference['revision'], preference['text'], preference['status'], event, preference['updated_at']),
    )


def _insert(conn: sqlite3.Connection, principal: Principal, text: str, status: str,
            origin: str, origin_ref: str | None, conflict_id: str | None = None) -> dict:
    now = utc_timestamp()
    preference = {
        'preference_id': f'pref_{uuid.uuid4().hex}', 'owner_id': principal.owner_id,
        'text': text, 'status': status, 'origin': origin, 'origin_ref': origin_ref,
        'conflict_preference_id': conflict_id,
        'revision': 1, 'created_at': now, 'updated_at': now,
    }
    conn.execute(
        'INSERT INTO workflow_preferences'
        ' (preference_id, owner_id, text, status, origin, origin_ref, conflict_preference_id, revision, created_at, updated_at)'
        ' VALUES (?,?,?,?,?,?,?,?,?,?)',
        tuple(preference[name] for name in ('preference_id', 'owner_id', 'text', 'status',
              'origin', 'origin_ref', 'conflict_preference_id', 'revision', 'created_at', 'updated_at')),
    )
    _event(conn, preference, 'created')
    return preference


def mutate_preference(conn: sqlite3.Connection, principal: Principal, action: str,
                      preference_id: str | None, payload: dict, request_id: str) -> WorkflowResult:
    """Perform an idempotent, revision-checked manual change in one transaction."""
    require_request_id(request_id)
    suffix = '' if action == 'create' else f'/{preference_id}' + (f'/{action}' if action != 'edit' else '')
    path = f'/api/workflow/preferences{suffix}'
    method = 'PATCH' if action == 'edit' else 'POST'
    digest = request_digest(method, path, payload)
    with atomic_write(conn):
        replay = find_idempotent(conn, principal.owner_id, request_id,
                                 method=method, resource_path=path, digest=digest)
        if replay is not None:
            return replay
        if action == 'create':
            _validate_text(payload['text'])
            if not payload['consent']:
                raise WorkflowError(409, 'approval_conflict', 'Confirm before activating this preference.')
            _check_activation(conn, principal.owner_id, payload['text'])
            result = _insert(conn, principal, payload['text'], 'active', 'manual', None)
            status = 201
        else:
            result = _owned(conn, principal.owner_id, preference_id)
            if result['revision'] != payload['expected_revision']:
                raise WorkflowError(409, 'revision_conflict', 'This preference changed. Your edits have not been saved.',
                                    current={'preference_revision': result['revision']})
            if action in ('activate', 'edit'):
                if not payload['consent']:
                    raise WorkflowError(409, 'approval_conflict', 'Confirm before activating this preference.')
                text = payload['text'] if action == 'edit' else result['text']
                _validate_text(text)
                own_active_id = preference_id if result['status'] == 'active' else None
                _check_activation(conn, principal.owner_id, text, own_active_id)
                result.update(text=text, status='active')
            elif action == 'stop':
                if result['status'] != 'active':
                    raise WorkflowError(409, 'preference_state_conflict', 'Only active preferences can be stopped.')
                result['status'] = 'stopped'
            elif action == 'reject':
                if result['status'] != 'pending':
                    raise WorkflowError(409, 'preference_state_conflict', 'Only pending suggestions can be dismissed.')
                result['status'] = 'rejected'
            else:
                raise WorkflowError(422, 'invalid_request', 'Unknown preference action')
            result['revision'] += 1
            result['updated_at'] = utc_timestamp()
            conn.execute('UPDATE workflow_preferences SET text=?, status=?, revision=?, updated_at=?'
                         ' WHERE owner_id=? AND preference_id=?',
                         (result['text'], result['status'], result['revision'], result['updated_at'],
                          principal.owner_id, preference_id))
            _event(conn, result, action)
            status = 200
        body = {'preference': result}
        record_idempotent(conn, principal.owner_id, request_id, method=method, resource_path=path,
                          digest=digest, response_status=status, body=body, created_at=utc_timestamp())
        return WorkflowResult(status, body)


def propose_preference(conn: sqlite3.Connection, principal: Principal, text: str, *,
                       origin: str, origin_ref: str, request_id: str) -> dict:
    """Record an AI suggestion only against an owned immutable source version."""
    _validate_text(text)
    if origin != 'item' or not origin_ref:
        raise WorkflowError(422, 'invalid_request', 'An owned source version is required')
    if not isinstance(request_id, str) or not request_id.strip():
        raise WorkflowError(422, 'invalid_request', 'A suggestion request id is required')
    path = '/api/workflow/preferences/suggestions'
    digest = request_digest('POST', path, {'text': text, 'origin': origin, 'origin_ref': origin_ref})
    with atomic_write(conn):
        replay = find_idempotent(conn, principal.owner_id, request_id,
                                 method='POST', resource_path=path, digest=digest)
        if replay is not None:
            return replay.body['preference']
        version = conn.execute('SELECT 1 FROM workflow_versions WHERE owner_id=? AND version_id=?',
                               (principal.owner_id, origin_ref)).fetchone()
        if version is None:
            raise WorkflowError(404, 'version_not_found', 'Source version not found')
        conflict_id = _pending_conflict(conn, principal.owner_id, text, enforce_cap=True)
        preference = _insert(conn, principal, text, 'pending', origin, origin_ref, conflict_id)
        record_idempotent(conn, principal.owner_id, request_id, method='POST', resource_path=path,
                          digest=digest, response_status=201, body={'preference': preference},
                          created_at=utc_timestamp())
        return preference


def import_legacy(conn: sqlite3.Connection, principal: Principal, legacy_ids: list[int]) -> list[dict]:
    """Explicitly map legacy local lessons to one owner as pending suggestions."""
    if principal.mode.value != 'trusted_local':
        raise WorkflowError(403, 'legacy_import_forbidden', 'Legacy mapping requires trusted local access')
    results = []
    with atomic_write(conn):
        for legacy_id in legacy_ids:
            if not isinstance(legacy_id, int) or isinstance(legacy_id, bool) or legacy_id < 1:
                raise WorkflowError(422, 'invalid_request', 'A valid local lesson id is required')
            previous = conn.execute("SELECT * FROM workflow_preferences WHERE origin='legacy' AND origin_ref=?",
                                    (str(legacy_id),)).fetchone()
            if previous:
                if previous['owner_id'] != principal.owner_id:
                    raise WorkflowError(409, 'legacy_already_mapped', 'This lesson was mapped to another owner')
                results.append(dict(previous))
                continue
            row = conn.execute('SELECT rule_text FROM lessons WHERE id=?', (legacy_id,)).fetchone()
            if row is None:
                raise WorkflowError(404, 'legacy_lesson_not_found', 'Local lesson not found')
            _validate_text(row['rule_text'])
            conflict_id = _pending_conflict(conn, principal.owner_id, row['rule_text'], enforce_cap=False)
            results.append(_insert(conn, principal, row['rule_text'], 'pending', 'legacy', str(legacy_id), conflict_id))
    return results
