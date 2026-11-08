"""Real HTTP generation claims never replace or approve working content."""
from contextlib import closing
import sqlite3
import unittest

from fastapi.testclient import TestClient
import test_workflow_api_items as fixtures
from content_machine.api.app import app
from content_machine.storage.db import connect


class WritingApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.previous = getattr(app.state, 'workflow_generator', None)
        self.addCleanup(setattr, app.state, 'workflow_generator', self.previous)
        self.previous_reviewer = getattr(app.state, 'workflow_reviewer', None)
        self.addCleanup(setattr, app.state, 'workflow_reviewer', self.previous_reviewer)
        self.calls = []
        def generate(snapshot):
            self.calls.append(snapshot)
            return {'segments': ['A proposal from the supplied idea.']}
        app.state.workflow_generator = generate
        self.item = self.fixture._create_item(title='An actual engineering idea')

    def generate(self, key='generate-one', revision=1):
        return self.client.post(f"/api/workflow/items/{self.item['item_id']}/generate",
                                json={'expected_revision': revision}, headers={'Idempotency-Key': key})

    def test_generation_is_a_proposal_with_original_context_and_stable_retry(self):
        result = self.generate()
        self.assertEqual(result.status_code, 200, result.text)
        operation = result.json()['operation']
        self.assertEqual(operation['state'], 'completed')
        self.assertEqual(operation['result']['artifact']['segments'], ['A proposal from the supplied idea.'])
        self.assertEqual(self.calls[0].title, 'An actual engineering idea')
        retry = self.generate()
        self.assertEqual(retry.json(), result.json())
        self.assertEqual(len(self.calls), 1)
        conflict = self.generate(revision=2)
        self.assertEqual(conflict.status_code, 409)
        current = self.client.get(f"/api/workflow/items/{self.item['item_id']}").json()['item']
        self.assertEqual(current['artifact']['segments'], [])
        self.assertIsNone(current['active_approval_id'])
        path = f"/api/workflow/items/{self.item['item_id']}/operations/{operation['operation_id']}"
        self.assertEqual(self.client.get(path).json(), result.json())
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_failure_is_persisted_and_does_not_echo_provider_secrets_or_rerun(self):
        def fail(snapshot):
            self.calls.append(snapshot)
            raise RuntimeError('secret-provider-token')
        app.state.workflow_generator = fail
        result = self.generate()
        self.assertEqual(result.status_code, 502, result.text)
        self.assertEqual(result.json()['operation']['state'], 'failed')
        self.assertNotIn('secret-provider-token', result.text)
        self.assertEqual(self.generate().json(), result.json())
        self.assertEqual(len(self.calls), 1)

    def test_disabled_generator_creates_no_operation(self):
        app.state.workflow_generator = None
        result = self.generate()
        self.assertEqual(result.status_code, 503, result.text)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.fixture._count('workflow_operations'), 0)

    def test_provider_runs_outside_a_transaction_and_can_preserve_newer_edits(self):
        def generate(snapshot):
            with closing(connect(self.fixture.db_path)) as conn:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('UPDATE workflow_items SET title=? WHERE item_id=?',
                             ('Retitled while generating', self.item['item_id']))
                conn.commit()
            return {'segments': ['A new proposal']}
        app.state.workflow_generator = generate
        result = self.generate()
        self.assertEqual(result.status_code, 200, result.text)
        saved = self.client.get(f"/api/workflow/items/{self.item['item_id']}").json()['item']
        self.assertEqual(saved['title'], 'Retitled while generating')
        self.assertEqual(saved['artifact']['segments'], [])

    def test_failed_claim_commit_never_calls_provider(self):
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript(
                'CREATE TABLE op_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE op_child(parent_id INTEGER REFERENCES op_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_claim AFTER INSERT ON workflow_operations'
                ' BEGIN INSERT INTO op_child VALUES(123); END;'
            )
            conn.commit()
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post(f"/api/workflow/items/{self.item['item_id']}/generate",
                                 json={'expected_revision': 1}, headers={'Idempotency-Key': 'fail-claim'})
        self.assertEqual(result.status_code, 500)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.fixture._count('workflow_operations'), 0)

    def review(self, key='review-one', revision=1):
        return self.client.post(f"/api/workflow/items/{self.item['item_id']}/review",
                                json={'expected_revision': revision}, headers={'Idempotency-Key': key})

    def advice(self, snapshot):
        self.calls.append(snapshot)
        score = {'narrative': 8, 'velocity': 8, 'depth': 8, 'slop_purity': 8,
                 'threshold_met': False, 'verdict': 'revise', 'required_actions': ['Clarify']}
        return {'actions': {'required_actions': ['Clarify'], 'notes': []},
                'score_basis': {'input_version_id': snapshot.version_id, 'raw': {'scale': [0, 10],
                    'composite': 8, 'judges': {'a': score, 'b': score, 'c': score}}, 'normalized': None}, 'proposals': []}

    def test_review_http_binds_input_and_retry_preserves_newer_draft(self):
        item_id = self.item['item_id']
        saved = self.fixture._patch(item_id, {'expected_revision': 1, 'artifact': {'segments': ['original']}})
        self.assertEqual(saved.status_code, 200)
        def reviewer(snapshot):
            response = self.fixture._patch(item_id, {'expected_revision': 2, 'artifact': {'segments': ['newer text']}})
            self.assertEqual(response.status_code, 200, response.text)
            return self.advice(snapshot)
        app.state.workflow_reviewer = reviewer
        result = self.review(revision=2)
        self.assertEqual(result.status_code, 200, result.text)
        operation = result.json()['operation']
        review = operation['result']['review']
        self.assertEqual(review['input_version_id'], operation['input_version_id'])
        self.assertEqual(self.calls[0].artifact.segments, ('original',))
        self.assertEqual(self.review(revision=2).json(), result.json())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.review(revision=3).status_code, 409)
        current = self.client.get(f'/api/workflow/items/{item_id}').json()['item']
        self.assertEqual(current['artifact']['segments'], ['newer text'])
        self.assertEqual(current['working_revision'], 3)
        self.assertIsNone(current['active_approval_id'])
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.review(key='foreign', revision=2).status_code, 404)
        self.assertEqual(self.client.get(f"/api/workflow/items/{item_id}/operations/{operation['operation_id']}").status_code, 404)

    def test_malformed_review_is_failed_and_does_not_reinvoke_provider(self):
        def malformed(snapshot):
            self.calls.append(snapshot)
            return {'score_basis': {'input_version_id': snapshot.version_id}, 'actions': 'not valid'}
        app.state.workflow_reviewer = malformed
        response = self.review()
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(response.json()['operation']['state'], 'failed')
        self.assertEqual(self.review().json(), response.json())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.fixture._count('workflow_reviews'), 0)

    def test_review_commit_failure_never_claims_success_or_creates_review(self):
        app.state.workflow_reviewer = self.advice
        saved = self.fixture._patch(self.item['item_id'], {'expected_revision': 1, 'artifact': {'segments': ['actual draft']}})
        self.assertEqual(saved.status_code, 200)
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE review_parent (id INTEGER PRIMARY KEY);'
                               'CREATE TABLE review_child (parent_id INTEGER REFERENCES review_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                               'CREATE TRIGGER fail_review AFTER INSERT ON workflow_reviews BEGIN INSERT INTO review_child VALUES (999); END;')
            conn.commit()
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post(f"/api/workflow/items/{self.item['item_id']}/review", json={'expected_revision': 2}, headers={'Idempotency-Key': 'commit-review'})
        self.assertEqual(result.status_code, 500)
        self.assertEqual(self.fixture._count('workflow_reviews'), 0)
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT state FROM workflow_operations').fetchone()[0], 'pending')
