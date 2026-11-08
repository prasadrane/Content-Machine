"""Guest bootstrap using separately verified hosted session proofs.

Only trusted server-side authentication code may supply the verifier. It must
verify each credential's signature, expiry, issuer and audience, and report
whether the authenticated Supabase identity is anonymous. Browser-supplied
owner IDs or anonymous flags are never proof. No route is registered here.
"""
from dataclasses import dataclass
import sqlite3
import uuid

from content_machine.workflow import items
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.persistence import atomic_write
from content_machine.workflow.schemas import ItemCreate, ItemPatch, Principal, utc_timestamp


GUEST_MIGRATION_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS workflow_guest_examples (
      owner_id TEXT NOT NULL, example_key TEXT NOT NULL, item_id TEXT NOT NULL,
      label TEXT NOT NULL, created_at TEXT NOT NULL,
      PRIMARY KEY (owner_id, example_key), UNIQUE (item_id, owner_id),
      FOREIGN KEY (item_id, owner_id) REFERENCES workflow_items (item_id, owner_id)
    )""",
)

_EXAMPLES = (
    {
        'key': 'idempotent-retries-v1',
        'title': 'Example: Safer retries',
        'notes': 'Demo example. Explore how an idempotency key can help a service recognize a retried request.',
        'draft': '',
    },
    {
        'key': 'bounded-queues-v1',
        'title': 'Example: Bounded queues',
        'notes': 'Demo example. Consider why a bounded queue can make overload visible to a service.',
        'draft': 'A bounded queue gives a service a clear limit. When it fills, the system can respond to overload instead of quietly accepting unbounded work.',
    },
)


@dataclass(frozen=True)
class VerifiedGuestSession:
    """Server-verifier output, never construct from request JSON or headers."""

    principal: Principal
    is_anonymous: bool


def _verified(proof, verifier, *, anonymous: bool) -> Principal:
    if not callable(verifier):
        raise WorkflowError(503, 'guest_auth_unavailable', 'Guest session verification is unavailable.')
    try:
        result = verifier(proof)
    except Exception:
        result = None
    if (not isinstance(result, VerifiedGuestSession) or not isinstance(result.principal, Principal)
            or result.principal.mode.value != 'hosted_verified'
            or type(result.is_anonymous) is not bool or result.is_anonymous is not anonymous):
        raise WorkflowError(401, 'unauthenticated', 'A verified session is required.')
    return result.principal


def bootstrap_guest(conn: sqlite3.Connection, proof, verifier) -> dict:
    """Seed each verified guest once, leaving later edits and examples intact."""
    principal = _verified(proof, verifier, anonymous=True)
    with atomic_write(conn):
        existing = {row['example_key'] for row in conn.execute(
            'SELECT example_key FROM workflow_guest_examples WHERE owner_id=?', (principal.owner_id,)
        ).fetchall()}
        for example in _EXAMPLES:
            if example['key'] in existing:
                continue
            # Random internal keys are recorded in the same transaction, so a
            # rolled-back attempt can be retried without claiming success.
            created = items.create_item(conn, principal, ItemCreate(
                title=example['title'], destination='linkedin', format='linkedin_post',
            ), request_id=f'guest-create-{uuid.uuid4().hex}')
            item = created.body['item']
            patch = {'expected_revision': item['working_revision'], 'context': {'notes': example['notes']}}
            if example['draft']:
                patch['artifact'] = {'segments': [example['draft']]}
            saved = items.save_item(conn, principal, item['item_id'], ItemPatch.model_validate(patch),
                                    request_id=f'guest-save-{uuid.uuid4().hex}')
            conn.execute(
                'INSERT INTO workflow_guest_examples (owner_id, example_key, item_id, label, created_at)'
                ' VALUES (?, ?, ?, ?, ?)',
                (principal.owner_id, example['key'], saved.body['item']['item_id'], 'Demo example', utc_timestamp()),
            )
        rows = conn.execute(
            'SELECT item_id, label FROM workflow_guest_examples WHERE owner_id=? ORDER BY created_at, example_key',
            (principal.owner_id,),
        ).fetchall()
        examples = [{'label': row['label'], 'item': items.get_item(conn, principal, row['item_id']).model_dump(mode='json')}
                    for row in rows]
    return {'examples': examples}


def guest_example_labels(conn: sqlite3.Connection, principal: Principal) -> dict[str, str]:
    """Read owned stored provenance without seeding or inspecting content."""
    return {row['item_id']: row['label'] for row in conn.execute(
        'SELECT item_id, label FROM workflow_guest_examples WHERE owner_id=?',
        (principal.owner_id,),
    ).fetchall()}


def preview_transfer(conn: sqlite3.Connection, guest_proof, creator_proof, verifier, *, consent: bool) -> dict:
    """Verify both owners and disclose the current transfer availability.

    This is intentionally read-only until atomic, lineage-preserving migration
    of snapshots, approvals and other owned records is independently reviewed.
    An HTTP integration must verify both proofs server-side and require a
    separate explicit action; a count or preview never claims a transfer.
    """
    if consent is not True:
        raise WorkflowError(422, 'consent_required', 'Explicit consent is required to inspect guest transfer.')
    guest = _verified(guest_proof, verifier, anonymous=True)
    creator = _verified(creator_proof, verifier, anonymous=False)
    if guest.owner_id == creator.owner_id:
        raise WorkflowError(409, 'invalid_transfer', 'Guest and creator sessions must be distinct.')
    return {
        'status': 'unavailable',
        'guest_item_count': len(items.list_items(conn, guest)),
        'detail': 'Guest transfer is not available yet. Your guest content remains in its current workspace.',
    }


__all__ = ['GUEST_MIGRATION_STATEMENTS', 'VerifiedGuestSession', 'bootstrap_guest', 'guest_example_labels', 'preview_transfer']
