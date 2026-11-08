"""Atomic unapproved working copies with immutable, original guest history.

No routing or automatic migration. Integrators must install the explicit schema
and preserve HTTP commit-before-response. This SQLite service does not certify
hosted persistence. No historical consent is transferred to the recipient.
"""
import json
import re
import uuid

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import _verified
from content_machine.workflow.guest_transfer_storage import TRANSFER_MIGRATION_STATEMENTS, capture, fingerprint
from content_machine.workflow.items import get_item
from content_machine.workflow.persistence import atomic_write, canonical_json
from content_machine.workflow.schemas import Principal, utc_timestamp

POLICY = 'unapproved-copy-with-original-history-v1'


def migrate_guest_transfer(conn):
    """Explicit additive migration; never discover or alter real workspaces."""
    with atomic_write(conn):
        for statement in TRANSFER_MIGRATION_STATEMENTS:
            conn.execute(statement)


def _identities(guest_proof, creator_proof, verifier):
    guest = _verified(guest_proof, verifier, anonymous=True)
    creator = _verified(creator_proof, verifier, anonymous=False)
    if guest.owner_id == creator.owner_id:
        raise WorkflowError(409, 'invalid_transfer', 'Guest and creator sessions must be distinct.')
    return guest, creator


def preview_guest_copy(conn, guest_proof, creator_proof, verifier):
    """Read a consent fingerprint for the complete source graph, without copying."""
    guest, _ = _identities(guest_proof, creator_proof, verifier)
    with atomic_write(conn):
        archive = capture(conn, guest.owner_id)
        return {'policy': POLICY, 'source_fingerprint': fingerprint(archive),
                'item_count': len(archive['tables']['workflow_items']), 'requires_new_approval': True}


def _copy_item(conn, creator, source, example_label, now):
    # Validate exact current values using their normal domain decoder. New
    # context references are mapped only at typed fields, never inside text.
    original = get_item(conn, Principal(owner_id=source['owner_id'], mode='hosted_verified'), source['item_id'])
    context = original.context.model_dump(mode='json')
    mapping = []
    for entry in context['sources']:
        source_id = entry['source_id']
        entry['source_id'] = uuid.uuid4().hex
        mapping.append({'source_id': source_id, 'target_context_source_id': entry['source_id']})
    context['preference_snapshot_id'] = None
    target_id = uuid.uuid4().hex
    stage = 'draft_review' if any(text.strip() for text in original.artifact.segments) else 'idea'
    conn.execute('''INSERT INTO workflow_items(item_id,owner_id,title,destination,format,stage,
        working_revision,context_json,artifact_json,parent_version_id,active_approval_id,created_at,updated_at)
        VALUES(?,?,?,?,?,?,1,?,?,NULL,NULL,?,?)''',
        (target_id, creator.owner_id, original.title, original.destination, original.format, stage,
         canonical_json(context), canonical_json(original.artifact.model_dump(mode='json')), now, now))
    return {'source_item_id': original.item_id, 'target_item_id': target_id,
            'context_source_mapping': mapping, 'source_example_label': example_label}


def copy_guest_workspace(conn, guest_proof, creator_proof, verifier, *, consent,
                         request_id, source_fingerprint):
    """Copy once with explicit dual proofs and consent bound to source fingerprint.

    With an idle connection, success follows commit. If the caller owns an outer
    transaction it must commit before acknowledging HTTP success, as with other
    workflow services. Source history stays in an inert immutable receipt.
    """
    if consent is not True:
        raise WorkflowError(422, 'consent_required', 'Explicit copy consent is required.')
    guest, creator = _identities(guest_proof, creator_proof, verifier)
    if (not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 200
            or not isinstance(source_fingerprint, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', source_fingerprint)):
        raise WorkflowError(422, 'invalid_request', 'A copy request key and source fingerprint are required.')
    with atomic_write(conn):
        existing = conn.execute('''SELECT * FROM workflow_guest_transfers
            WHERE source_owner_id=? AND destination_owner_id=?''', (guest.owner_id, creator.owner_id)).fetchone()
        if existing:
            if existing['source_fingerprint'] == source_fingerprint and existing['policy'] == POLICY:
                return json.loads(existing['response_json'])
            code = 'idempotency_conflict' if existing['request_id'] == request_id else 'guest_already_copied'
            raise WorkflowError(409, code, 'This guest workspace was already copied. Existing copies are preserved.')
        archive = capture(conn, guest.owner_id)
        if fingerprint(archive) != source_fingerprint:
            raise WorkflowError(409, 'transfer_source_changed', 'Guest work changed. Review a fresh copy preview.')
        transfer_id, now = uuid.uuid4().hex, utc_timestamp()
        labels = {row['item_id']: row['label'] for row in archive['tables']['workflow_guest_examples']}
        mappings = [_copy_item(conn, creator, row, labels.get(row['item_id']), now)
                    for row in archive['tables']['workflow_items']]
        result = {'status': 'copied', 'transfer_id': transfer_id, 'policy': POLICY,
                  'requires_new_approval': True, 'items': mappings}
        conn.execute('''INSERT INTO workflow_guest_transfers(transfer_id,source_owner_id,destination_owner_id,
            request_id,source_fingerprint,policy,archive_json,response_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)''',
            (transfer_id, guest.owner_id, creator.owner_id, request_id, source_fingerprint, POLICY,
             canonical_json(archive), canonical_json(result), now))
        for mapping in mappings:
            conn.execute('''INSERT INTO workflow_guest_transfer_items(transfer_id,source_item_id,target_item_id,
                destination_owner_id,context_mapping_json,example_label) VALUES(?,?,?,?,?,?)''',
                (transfer_id, mapping['source_item_id'], mapping['target_item_id'], creator.owner_id,
                 canonical_json(mapping['context_source_mapping']), mapping['source_example_label']))
        return result


def get_transfer_receipt(conn, principal, transfer_id):
    """Only the receiving verified creator can inspect the inert source archive."""
    if not isinstance(principal, Principal) or principal.mode.value != 'hosted_verified':
        raise WorkflowError(401, 'unauthenticated', 'A verified creator is required.')
    row = conn.execute('''SELECT * FROM workflow_guest_transfers
        WHERE transfer_id=? AND destination_owner_id=?''', (transfer_id, principal.owner_id)).fetchone()
    if row is None:
        raise WorkflowError(404, 'transfer_not_found', 'Transfer receipt not found.')
    archive = json.loads(row['archive_json'])
    if fingerprint(archive) != row['source_fingerprint']:
        raise WorkflowError(409, 'transfer_invalid_history', 'Transfer archive fingerprint mismatch.')
    return {'transfer_id': transfer_id, 'policy': row['policy'], 'editorial_approval': False,
            'archive': archive, 'copy': json.loads(row['response_json'])}


def transferred_example_labels(conn, principal):
    """Owned copy provenance for normal item summaries; never infer from titles."""
    return {row['target_item_id']: row['example_label'] for row in conn.execute(
        '''SELECT target_item_id,example_label FROM workflow_guest_transfer_items
           WHERE destination_owner_id=? AND example_label IS NOT NULL''', (principal.owner_id,))}
