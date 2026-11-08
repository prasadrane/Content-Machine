"""Guest copy receipts retain original history without transferring consent."""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3
import unittest
from unittest.mock import MagicMock

import test_workflow_recovery as fixtures
from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.items import get_item
from content_machine.workflow import guest_transfer as transfer
from content_machine.workflow.guest_transfer_storage import capture, TABLES


class PostgresCaptureTest(unittest.TestCase):
    def connection(self, extra=()):
        conn = MagicMock(dialect='postgresql')
        conn._raw.execute.return_value.fetchall.return_value = [(table, 'owner_id') for table in TABLES] + list(extra)
        conn._driver.side_effect = lambda call, *args: call(*args)
        conn.execute.return_value.__iter__ = lambda self: iter([])
        return conn

    def test_catalog_path_archives_only_owned_tables_without_sqlite_metadata(self):
        conn = self.connection()
        archive = capture(conn, 'guest')
        self.assertEqual(set(archive['tables']), set(TABLES))
        for call in conn.execute.call_args_list:
            self.assertNotIn('PRAGMA', call.args[0])
            self.assertNotIn('sqlite_master', call.args[0])
            self.assertEqual(call.args[1], ('guest',))
        self.assertIn('current_schema()', conn._raw.execute.call_args_list[0].args[0])

    def test_catalog_unknown_owned_history_fails_closed(self):
        conn = self.connection([('workflow_future_history', 'owner_id')])
        with self.assertRaises(WorkflowError) as raised:
            capture(conn, 'guest')
        self.assertEqual(raised.exception.code, 'transfer_unsupported_history')


class GuestTransferTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.RecoveryTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.conn = self.fixture.conn
        self.conn.execute("UPDATE workflow_operations SET state='failed',finished_at='2026-11-07T10:00:00.000Z' WHERE owner_id=?", (self.fixture.a.owner_id,))
        self.conn.commit()
        transfer.migrate_guest_transfer(self.conn)
        self.conn.commit()
        self.proofs = {'guest': VerifiedGuestSession(self.fixture.a, True),
                       'creator': VerifiedGuestSession(self.fixture.b, False)}

    def verify(self, proof):
        return self.proofs.get(proof)

    def preview(self, conn=None):
        return transfer.preview_guest_copy(conn or self.conn, 'guest', 'creator', self.verify)

    def copy(self, conn=None, key='copy', fingerprint=None, consent=True):
        conn = conn or self.conn
        fingerprint = fingerprint or self.preview(conn)['source_fingerprint']
        return transfer.copy_guest_workspace(conn, 'guest', 'creator', self.verify,
            consent=consent, request_id=key, source_fingerprint=fingerprint)

    def test_copies_exact_work_unapproved_and_archives_original_graph(self):
        before = self.preview()['source_fingerprint']
        original = get_item(self.conn, self.fixture.a, self.fixture.a_id)
        creator_original = get_item(self.conn, self.fixture.b, self.fixture.b_id)
        copied = self.copy()
        mapping = copied['items'][0]
        self.assertEqual(mapping['source_item_id'], original.item_id)
        target = get_item(self.conn, self.fixture.b, mapping['target_item_id'])
        self.assertEqual(target.artifact, original.artifact)
        self.assertEqual(target.context.notes, original.context.notes)
        self.assertEqual(target.working_revision, 1)
        self.assertEqual(target.stage.value, 'draft_review')
        self.assertIsNone(target.active_approval_id)
        self.assertIsNone(target.parent_version_id)
        self.assertEqual(get_item(self.conn, self.fixture.b, self.fixture.b_id), creator_original)
        self.assertEqual(get_item(self.conn, self.fixture.a, self.fixture.a_id), original)
        self.assertEqual(self.preview()['source_fingerprint'], before)
        receipt = transfer.get_transfer_receipt(self.conn, self.fixture.b, copied['transfer_id'])
        self.assertEqual(len(receipt['archive']['tables']['workflow_versions']), 1)
        self.assertEqual(len(receipt['archive']['tables']['workflow_approvals']), 1)
        self.assertEqual(len(receipt['archive']['tables']['workflow_operations']), 1)
        self.assertEqual(receipt['archive']['tables']['workflow_approvals'][0]['approved_by'], self.fixture.a.owner_id)
        self.assertFalse(receipt['editorial_approval'])
        self.assertEqual(self.conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_same_key_and_same_generation_replay_without_duplicate_copies(self):
        fingerprint = self.preview()['source_fingerprint']
        first = self.copy(fingerprint=fingerprint)
        self.assertEqual(first, self.copy(fingerprint=fingerprint))
        self.assertEqual(first, self.copy(key='other-retry', fingerprint=fingerprint))
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 3)
        with self.assertRaises(WorkflowError) as raised:
            self.copy(fingerprint='sha256:' + 'a' * 64)
        self.assertEqual(raised.exception.code, 'idempotency_conflict')

    def test_source_changes_require_fresh_consent_and_no_delta_copy(self):
        fingerprint = self.preview()['source_fingerprint']
        self.conn.execute("UPDATE workflow_items SET title='changed' WHERE item_id=?", (self.fixture.a_id,))
        self.conn.commit()
        with self.assertRaises(WorkflowError) as raised:
            self.copy(fingerprint=fingerprint)
        self.assertEqual(raised.exception.code, 'transfer_source_changed')
        self.copy(key='fresh')
        self.conn.execute("UPDATE workflow_items SET title='later' WHERE item_id=?", (self.fixture.a_id,))
        self.conn.commit()
        with self.assertRaises(WorkflowError) as raised:
            self.copy(key='delta')
        self.assertEqual(raised.exception.code, 'guest_already_copied')

    def test_requires_consent_dual_verified_distinct_sessions_and_valid_key(self):
        fingerprint = self.preview()['source_fingerprint']
        cases = [('guest', 'creator', False, 'copy'), ('unknown', 'creator', True, 'copy'),
                 ('creator', 'guest', True, 'copy'), ('guest', 'guest', True, 'copy'),
                 ('guest', 'creator', True, '')]
        for guest, creator, consent, key in cases:
            with self.subTest(case=(guest, creator, consent, key)), self.assertRaises(WorkflowError):
                transfer.copy_guest_workspace(self.conn, guest, creator, self.verify,
                    consent=consent, request_id=key, source_fingerprint=fingerprint)
        self.proofs['same'] = VerifiedGuestSession(self.fixture.a, False)
        with self.assertRaises(WorkflowError):
            transfer.preview_guest_copy(self.conn, 'guest', 'same', self.verify)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)

    def test_pending_operation_refused_before_any_target_write(self):
        self.conn.execute("UPDATE workflow_operations SET state='pending' WHERE owner_id=?", (self.fixture.a.owner_id,))
        self.conn.commit()
        with self.assertRaises(WorkflowError) as raised:
            self.preview()
        self.assertEqual(raised.exception.code, 'guest_operations_pending')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 2)

    def test_receipt_is_immutable_owner_scoped_and_hash_verified(self):
        copied = self.copy()
        with self.assertRaises(WorkflowError):
            transfer.get_transfer_receipt(self.conn, self.fixture.a, copied['transfer_id'])
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE workflow_guest_transfers SET source_fingerprint='bad'")
        self.conn.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('DELETE FROM workflow_guest_transfers')
        self.conn.rollback()

    def test_deferred_commit_failure_rolls_back_items_receipt_and_mappings(self):
        self.conn.executescript('CREATE TABLE transfer_parent(id INTEGER PRIMARY KEY);'
            'CREATE TABLE transfer_child(id INTEGER REFERENCES transfer_parent(id) DEFERRABLE INITIALLY DEFERRED);'
            'CREATE TRIGGER fail_transfer AFTER INSERT ON workflow_guest_transfers BEGIN INSERT INTO transfer_child VALUES(999); END;')
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.copy()
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 2)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_guest_transfer_items').fetchone()[0], 0)
        self.conn.execute('DROP TRIGGER fail_transfer')
        self.conn.commit()
        self.assertEqual(self.copy()['status'], 'copied')

    def test_concurrent_requests_copy_once(self):
        fingerprint = self.preview()['source_fingerprint']
        def run(_):
            with closing(connect(self.fixture.source)) as conn:
                return self.copy(conn, fingerprint=fingerprint)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(run, range(2)))
        self.assertEqual(responses[0], responses[1])
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 3)

    def test_context_reference_mapping_preserves_exact_text_and_archives_settings_without_merging(self):
        context = {'notes': 'The literal ID source-ref must remain in text.', 'experience': None,
                   'interpretation': None, 'preference_snapshot_id': 'source-pref-snapshot',
                   'sources': [{'source_id': 'source-ref', 'title': 'Evidence', 'url': 'https://example.org/',
                                'excerpt': 'Exact source-ref\n', 'fetched_at': '2026-11-07T10:00:00.000Z'}]}
        self.conn.execute('UPDATE workflow_items SET context_json=? WHERE item_id=?',
                          (json.dumps(context), self.fixture.a_id))
        now = '2026-11-07T10:00:00.000Z'
        self.conn.execute('INSERT INTO workflow_profiles VALUES(?,?,?,?,?,?)',
                          (self.fixture.a.owner_id, 'Guest name', 'Guest role', 'Guest bio', 1, now))
        self.conn.execute('INSERT INTO workflow_profiles VALUES(?,?,?,?,?,?)',
                          (self.fixture.b.owner_id, 'Creator name', '', '', 1, now))
        self.conn.execute('INSERT INTO workflow_guest_examples VALUES(?,?,?,?,?)',
                          (self.fixture.a.owner_id, 'example', self.fixture.a_id, 'Demo example', now))
        self.conn.commit()
        copied = self.copy()
        target = get_item(self.conn, self.fixture.b, copied['items'][0]['target_item_id'])
        self.assertEqual(target.context.notes, context['notes'])
        self.assertEqual(target.context.sources[0].excerpt, context['sources'][0]['excerpt'])
        self.assertNotEqual(target.context.sources[0].source_id, 'source-ref')
        self.assertIsNone(target.context.preference_snapshot_id)
        self.assertEqual(copied['items'][0]['context_source_mapping'][0]['source_id'], 'source-ref')
        receipt = transfer.get_transfer_receipt(self.conn, self.fixture.b, copied['transfer_id'])
        self.assertEqual(receipt['archive']['tables']['workflow_profiles'][0]['name'], 'Guest name')
        self.assertEqual(self.conn.execute('SELECT name FROM workflow_profiles WHERE owner_id=?',
                                          (self.fixture.b.owner_id,)).fetchone()[0], 'Creator name')
        self.assertEqual(transfer.transferred_example_labels(self.conn, self.fixture.b),
                         {target.item_id: 'Demo example'})

    def test_second_item_failure_rolls_back_first_copy(self):
        from content_machine.workflow.items import create_item
        from content_machine.workflow.schemas import ItemCreate
        create_item(self.conn, self.fixture.a, ItemCreate(title='Refuse this copy',
            destination='linkedin', format='linkedin_post'), request_id='additional')
        self.conn.executescript("CREATE TRIGGER refuse_copy BEFORE INSERT ON workflow_items "
            "WHEN NEW.owner_id='creator-b' AND NEW.title='Refuse this copy' "
            "BEGIN SELECT RAISE(ABORT,'copy interrupted'); END;")
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.copy()
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items WHERE owner_id=?',
                                          (self.fixture.b.owner_id,)).fetchone()[0], 1)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)

    def test_caller_owned_transaction_can_roll_back_without_losing_source(self):
        fingerprint = self.preview()['source_fingerprint']
        self.conn.execute('BEGIN')
        self.copy(fingerprint=fingerprint)
        self.conn.rollback()
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 2)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)
        self.assertEqual(self.copy(fingerprint=fingerprint)['status'], 'copied')

    def test_unknown_owner_scoped_history_fails_closed_instead_of_silently_omitting_it(self):
        self.conn.execute('CREATE TABLE workflow_future_history(owner_id TEXT NOT NULL, payload TEXT)')
        self.conn.commit()
        with self.assertRaises(WorkflowError) as raised:
            self.preview()
        self.assertEqual(raised.exception.code, 'transfer_unsupported_history')

    def test_optional_legacy_provenance_is_archived_when_schema_is_installed(self):
        from content_machine.workflow.legacy_import import initialize_import_schema
        initialize_import_schema(self.conn)
        copied = self.copy()
        receipt = transfer.get_transfer_receipt(self.conn, self.fixture.b, copied['transfer_id'])
        self.assertEqual(receipt['archive']['tables']['workflow_legacy_imports'], [])

    def test_mapping_foreign_keys_cannot_bind_receipt_to_another_owner(self):
        copied = self.copy()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('''INSERT INTO workflow_guest_transfer_items(transfer_id,source_item_id,
                target_item_id,destination_owner_id,context_mapping_json) VALUES(?,?,?,?,?)''',
                (copied['transfer_id'], 'spoofed-source', self.fixture.a_id, self.fixture.a.owner_id, '[]'))
        self.conn.rollback()
