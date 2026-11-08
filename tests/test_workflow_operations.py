"""Guard operation claims, immutable inputs, ownership and retry semantics."""
import json
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import create_item, save_item
from content_machine.workflow.operations import (
    OPERATION_MIGRATION_STATEMENTS, begin_operation, complete_operation,
    fail_operation, get_operation, list_operations,
)
from content_machine.workflow.schemas import ItemCreate, ItemPatch, Principal
from content_machine.workflow.settings import ProfileSave, save_profile


class WorkflowOperationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cm-operations-')
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'operations.db'
        with closing(connect(self.path)) as conn:
            for statement in OPERATION_MIGRATION_STATEMENTS:
                conn.execute(statement)
            conn.commit()
        self.conn = connect(self.path, init=False)
        self.addCleanup(self.conn.close)
        self.a = Principal(owner_id='owner-a', mode='hosted_verified')
        self.b = Principal(owner_id='owner-b', mode='hosted_verified')
        self.item = create_item(self.conn, self.a,
            ItemCreate(title='Index tradeoffs', destination='linkedin', format='linkedin_post'),
            request_id='create-item').body['item']
        self.item_id = self.item['item_id']

    def begin(self, key='generate-one', kind='generate', revision=1):
        return begin_operation(self.conn, self.a, self.item_id, revision, kind, key)

    def test_abandon_is_owned_idempotent_and_late_completion_cannot_win(self):
        from content_machine.workflow.operation_recovery import abandon_operation
        operation, _ = self.begin()
        op_id = operation['operation_id']
        with self.assertRaises(WorkflowError):
            abandon_operation(self.conn, self.b, self.item_id, op_id)
        abandoned = abandon_operation(self.conn, self.a, self.item_id, op_id)
        self.assertEqual(abandoned['error']['code'], 'operation_abandoned')
        self.assertEqual(abandon_operation(self.conn, self.a, self.item_id, op_id), abandoned)
        with self.assertRaises(WorkflowError):
            complete_operation(self.conn, self.a, self.item_id, op_id, {'late': True})
        completed, _ = self.begin(key='second')
        complete_operation(self.conn, self.a, self.item_id, completed['operation_id'], {})
        self.assertEqual(abandon_operation(self.conn, self.a, self.item_id, completed['operation_id'])['state'], 'completed')

    def test_claim_freezes_version_and_returns_owned_pending_operation(self):
        save_profile(self.conn, self.a, ProfileSave(name='Ada', role='Engineer', bio='', expected_revision=0),
                     request_id='profile')
        operation, created = self.begin()
        self.assertTrue(created)
        self.assertEqual(operation['state'], 'pending')
        self.assertEqual(operation['kind'], 'generate')
        self.assertEqual(operation['context_snapshot']['notes'], '')
        self.assertEqual(operation['editorial_snapshot']['title'], 'Index tradeoffs')
        self.assertEqual(operation['editorial_snapshot']['profile']['name'], 'Ada')
        self.assertEqual(operation['editorial_snapshot']['version_id'], operation['input_version_id'])
        self.assertEqual(get_operation(self.conn, self.a, self.item_id, operation['operation_id']), operation)
        self.assertEqual(list_operations(self.conn, self.a, self.item_id), [operation])
        self.assertFalse(self.conn.in_transaction)
        with closing(connect(self.path, init=False)) as other:
            self.assertEqual(other.execute('SELECT COUNT(*) FROM workflow_operations').fetchone()[0], 1)
            self.assertEqual(other.execute('SELECT COUNT(*) FROM workflow_operation_inputs').fetchone()[0], 1)
            self.assertEqual(other.execute('SELECT COUNT(*) FROM workflow_versions').fetchone()[0], 1)

    def test_retries_use_frozen_input_and_changed_requests_conflict(self):
        first, _ = self.begin()
        save_profile(self.conn, self.a, ProfileSave(name='Later', role='', bio='', expected_revision=0),
                     request_id='profile-later')
        saved = save_item(self.conn, self.a, self.item_id, ItemPatch(expected_revision=1,
                          context={'notes': 'Changed after the claim'}), request_id='edit-item')
        self.assertEqual(saved.body['item']['working_revision'], 2)
        replay, created = self.begin()
        self.assertFalse(created)
        self.assertEqual(replay, first)
        self.assertIsNone(replay['editorial_snapshot']['profile'])
        for call in (lambda: self.begin(revision=2), lambda: self.begin(kind='review'),
                     lambda: begin_operation(self.conn, self.a, 'another-item', 1, 'generate', 'generate-one')):
            with self.assertRaises(WorkflowError) as error:
                call()
            self.assertEqual(error.exception.code, 'idempotency_conflict')
        with self.assertRaises(WorkflowError) as collision:
            self.begin(key='create-item')
        self.assertEqual(collision.exception.code, 'idempotency_conflict')

    def test_completion_and_failure_are_owner_scoped_idempotent_and_do_not_edit_items(self):
        operation, _ = self.begin()
        op_id = operation['operation_id']
        denied = lambda: get_operation(self.conn, self.b, self.item_id, op_id)
        with self.assertRaises(WorkflowError) as error:
            denied()
        self.assertEqual(error.exception.status_code, 404)
        result = {'segments': ['  Exact suggestion\n']}
        completed = complete_operation(self.conn, self.a, self.item_id, op_id, result)
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(completed['result'], result)
        self.assertEqual(complete_operation(self.conn, self.a, self.item_id, op_id, result), completed)
        self.assertEqual(self.begin()[0], completed)
        with self.assertRaises(WorkflowError) as changed:
            complete_operation(self.conn, self.a, self.item_id, op_id, {'segments': ['different']})
        self.assertEqual(changed.exception.code, 'operation_state_conflict')
        with self.assertRaises(WorkflowError):
            fail_operation(self.conn, self.a, self.item_id, op_id, {'code': 'provider_failed'})
        with self.assertRaises(WorkflowError) as foreign:
            complete_operation(self.conn, self.b, self.item_id, op_id, result)
        self.assertEqual(foreign.exception.status_code, 404)
        self.assertEqual(self.conn.execute('SELECT working_revision FROM workflow_items WHERE item_id=?',
                                           (self.item_id,)).fetchone()[0], 1)
        failed, _ = self.begin(key='second')
        failure = {'code': 'provider_failed', 'detail': 'The provider failed.'}
        actual = fail_operation(self.conn, self.a, self.item_id, failed['operation_id'], failure)
        self.assertEqual(actual['state'], 'failed')
        self.assertEqual(fail_operation(self.conn, self.a, self.item_id, failed['operation_id'], failure), actual)

    def test_claim_rejects_an_outer_transaction_before_provider_can_start(self):
        self.conn.execute('BEGIN')
        with self.assertRaises(WorkflowError) as blocked:
            self.begin()
        self.assertEqual(blocked.exception.code, 'operation_transaction_open')
        self.assertTrue(self.conn.in_transaction)
        self.conn.rollback()
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_operations').fetchone()[0], 0)

    def test_failed_commit_rolls_back_version_operation_input_and_idempotency(self):
        self.conn.executescript('CREATE TABLE op_parent (id INTEGER PRIMARY KEY);'
            'CREATE TABLE op_child (id INTEGER REFERENCES op_parent(id) DEFERRABLE INITIALLY DEFERRED);'
            'CREATE TRIGGER fail_op AFTER INSERT ON workflow_operations BEGIN INSERT INTO op_child VALUES(99); END;')
        with self.assertRaises(sqlite3.IntegrityError):
            self.begin()
        for table in ('workflow_operations', 'workflow_operation_inputs', 'workflow_versions'):
            self.assertEqual(self.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM workflow_idempotency WHERE request_id='generate-one'").fetchone()[0], 0)
        self.conn.execute('DROP TRIGGER fail_op')
        self.conn.commit()
        self.assertTrue(self.begin()[1])

    def test_terminal_commit_failure_leaves_pending_and_retry_can_finish(self):
        operation, _ = self.begin()
        self.conn.executescript('CREATE TABLE terminal_parent (id INTEGER PRIMARY KEY);'
            'CREATE TABLE terminal_child (id INTEGER REFERENCES terminal_parent(id) DEFERRABLE INITIALLY DEFERRED);'
            'CREATE TRIGGER fail_terminal AFTER UPDATE ON workflow_operations '
            'BEGIN INSERT INTO terminal_child VALUES(99); END;')
        result = {'segments': ['Exact output']}
        with self.assertRaises(sqlite3.IntegrityError):
            complete_operation(self.conn, self.a, self.item_id, operation['operation_id'], result)
        pending = get_operation(self.conn, self.a, self.item_id, operation['operation_id'])
        self.assertEqual(pending['state'], 'pending')
        self.assertIsNone(pending['result'])
        self.conn.execute('DROP TRIGGER fail_terminal')
        self.conn.commit()
        completed = complete_operation(self.conn, self.a, self.item_id, operation['operation_id'], result)
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(completed['result'], result)

    def test_concurrent_identical_claims_create_one_operation(self):
        barrier = threading.Barrier(2)
        def claim(_):
            with closing(connect(self.path, init=False)) as conn:
                barrier.wait(timeout=5)
                return begin_operation(conn, self.a, self.item_id, 1, 'generate', 'concurrent')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, range(2)))
        self.assertEqual(sorted(created for _, created in results), [False, True])
        self.assertEqual(results[0][0]['operation_id'], results[1][0]['operation_id'])
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_operations').fetchone()[0], 1)

    def test_inputs_are_immutable_and_missing_old_title_remains_missing(self):
        operation, _ = self.begin()
        op_id = operation['operation_id']
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('UPDATE workflow_operation_inputs SET editorial_snapshot_json=? WHERE operation_id=?',
                              ('{}', op_id))
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute('DELETE FROM workflow_operation_inputs WHERE operation_id=?', (op_id,))
        self.conn.rollback()
        from content_machine.workflow.operations import decode_editorial_snapshot
        original = operation['editorial_snapshot']
        del original['title']
        restored = decode_editorial_snapshot(json.dumps(original))
        self.assertIsNone(restored.title)
        self.assertEqual(restored.version_id, operation['input_version_id'])

    def test_invalid_kind_revision_and_request_key_do_not_create_records(self):
        for kind, revision, key in [('publish', 1, 'x'), ('generate', 0, 'y'),
                                    ('generate', True, 'z'), ('generate', 1, '  ')]:
            with self.subTest(kind=kind, revision=revision, key=key):
                with self.assertRaises(WorkflowError):
                    self.begin(kind=kind, revision=revision, key=key)
        with self.assertRaises(WorkflowError) as stale:
            self.begin(revision=2)
        self.assertEqual(stale.exception.code, 'revision_conflict')
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM workflow_operations').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
