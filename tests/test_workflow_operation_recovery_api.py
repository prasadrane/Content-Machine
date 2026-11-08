"""HTTP recovery requires confirmation and persists only committed owned outcomes."""
from contextlib import closing
import unittest

from fastapi.testclient import TestClient
import test_workflow_api_items as fixtures
from content_machine.api.app import app
from content_machine.storage.db import connect
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.operations import begin_operation, complete_operation, get_operation


class OperationRecoveryApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.item = self.fixture._create_item()
        self.item_id = self.item['item_id']
        with closing(connect(self.fixture.db_path)) as conn:
            self.operation = begin_operation(conn, self.fixture.a, self.item_id, 1, 'generate', 'recovery-test')[0]
        self.op_id = self.operation['operation_id']
        self.path = f'/api/workflow/items/{self.item_id}/operations/{self.op_id}/abandon'

    def read_operation(self):
        with closing(connect(self.fixture.db_path)) as conn:
            return get_operation(conn, self.fixture.a, self.item_id, self.op_id)

    def test_confirmation_owner_replay_and_late_completion(self):
        for body in ({}, {'confirm': False}, {'confirm': 'true'}, {'confirm': 1}):
            self.assertEqual(self.client.post(self.path, json=body).status_code, 422, body)
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.post(self.path, json={'confirm': True}).status_code, 404)
        self.fixture._as(self.fixture.a)
        response = self.client.post(self.path, json={'confirm': True})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()['operation']
        self.assertEqual(result['state'], 'failed')
        self.assertEqual(result['error']['code'], 'operation_abandoned')
        self.assertEqual(self.client.post(self.path, json={'confirm': True}).json()['operation'], result)
        with closing(connect(self.fixture.db_path)) as conn:
            with self.assertRaises(WorkflowError):
                complete_operation(conn, self.fixture.a, self.item_id, self.op_id, {'late': True})
        self.assertEqual(self.read_operation(), result)

    def test_completed_operation_is_not_rewritten(self):
        with closing(connect(self.fixture.db_path)) as conn:
            completed = complete_operation(conn, self.fixture.a, self.item_id, self.op_id, {'done': True})
        response = self.client.post(self.path, json={'confirm': True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['operation'], completed)

    def test_deferred_outer_commit_failure_rolls_back_and_never_acknowledges(self):
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE recovery_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE recovery_child(parent_id INTEGER REFERENCES recovery_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_recovery AFTER UPDATE OF state ON workflow_operations '
                'BEGIN INSERT INTO recovery_child VALUES(123); END;')
            conn.commit()
        def factory():
            conn = connect(self.fixture.db_path)
            conn.execute('BEGIN')
            return conn
        app.state.workflow_connection_factory = factory
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(self.path, json={'confirm': True})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.read_operation()['state'], 'pending')
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM recovery_child').fetchone()[0], 0)
