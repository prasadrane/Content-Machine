"""Mounted guest bootstrap with signed ephemeral JWTs and disposable SQLite."""
from contextlib import closing
import os
import sqlite3
import time
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric import ec
import jwt

import test_workflow_api_items as fixtures
from content_machine.storage.db import connect
from content_machine.workflow.hosted_auth import SupabaseAuthenticator
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.schemas import Principal

PROJECT = 'https://example.supabase.co'


class GuestBootstrapApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.key = ec.generate_private_key(ec.SECP256R1())
        keys = Mock()
        keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        self.auth = SupabaseAuthenticator(PROJECT, jwks_client=keys)
        fixtures.app.state.workflow_authenticator = self.auth
        self.owner = str(uuid.uuid4())

    def token(self, owner=None, anonymous=True, **changes):
        return jwt.encode({'iss': PROJECT + '/auth/v1', 'aud': 'authenticated',
            'sub': owner or self.owner, 'role': 'authenticated', 'is_anonymous': anonymous,
            'iat': int(time.time()) - 5, 'exp': int(time.time()) + 60, **changes},
            self.key, algorithm='ES256', headers={'kid': 'fixture'})

    def boot(self, token=None, body=None):
        return self.client.post('/api/workflow/guest/bootstrap', json={} if body is None else body,
            headers={'Authorization': 'Bearer ' + (token or self.token())})

    def test_normal_route_seeds_once_labels_owned_list_and_preserves_edits(self):
        token = self.token()
        first = self.boot(token)
        self.assertEqual(first.status_code, 200, first.text)
        examples = first.json()['examples']
        self.assertEqual(len(examples), 2)
        self.assertTrue(all(row['label'] == 'Demo example' for row in examples))
        self.assertEqual(first.json(), self.boot(token).json())
        selected = examples[0]['item']
        saved = self.client.patch('/api/workflow/items/' + selected['item_id'],
            headers={'Authorization': 'Bearer ' + token, 'Idempotency-Key': 'edit-example'},
            json={'expected_revision': selected['working_revision'], 'context': {'notes': 'My exact edits\n'}})
        self.assertEqual(saved.status_code, 200)
        returned = self.boot(token).json()['examples']
        edited = next(row['item'] for row in returned if row['item']['item_id'] == selected['item_id'])
        self.assertEqual(edited['context']['notes'], 'My exact edits\n')
        listed = self.client.get('/api/workflow/items', headers={'Authorization': 'Bearer ' + token}).json()['items']
        self.assertEqual(len(listed), 2)
        self.assertTrue(all(row['guest_example_label'] == 'Demo example' for row in listed))
        other = self.boot(self.token(owner=str(uuid.uuid4()))).json()['examples']
        self.assertFalse({row['item']['item_id'] for row in other} & {row['item']['item_id'] for row in examples})

    def test_missing_forged_nonanonymous_and_metadata_only_claims_fail_before_storage(self):
        factory = Mock(wraps=fixtures.app.state.workflow_connection_factory)
        fixtures.app.state.workflow_connection_factory = factory
        missing = self.client.post('/api/workflow/guest/bootstrap', json={})
        self.assertEqual(missing.status_code, 401)
        for token in ('forged', self.token(anonymous=False), self.token(anonymous='true'),
                      self.token(anonymous=None, user_metadata={'is_anonymous': True})):
            with self.subTest(token=token[:10]):
                self.assertEqual(self.boot(token).status_code, 401)
        factory.assert_not_called()

    def test_browser_owner_and_anonymous_fields_are_rejected(self):
        response = self.boot(body={'owner_id': 'victim', 'is_anonymous': True})
        self.assertEqual(response.status_code, 422)
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)

    def test_commit_failure_rolls_back_and_same_guest_can_retry(self):
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE guest_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE guest_child(parent_id INTEGER REFERENCES guest_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_guest AFTER INSERT ON workflow_guest_examples BEGIN INSERT INTO guest_child VALUES (999); END;')
            conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.boot()
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_guest')
            conn.commit()
        self.assertEqual(self.boot().status_code, 200)

    def test_absent_session_verifier_fails_closed(self):
        fixtures.app.state.workflow_authenticator = lambda request: fixtures.principal(self.owner)
        response = self.boot()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'guest_auth_unavailable')

    def test_session_proof_for_another_owner_is_rejected_before_storage(self):
        factory = Mock(wraps=fixtures.app.state.workflow_connection_factory)
        fixtures.app.state.workflow_connection_factory = factory
        self.auth.verify_session = Mock(return_value=VerifiedGuestSession(
            Principal(owner_id=str(uuid.uuid4()), mode='hosted_verified'), is_anonymous=True))
        response = self.boot()
        self.assertEqual(response.status_code, 401)
        factory.assert_not_called()

    def test_session_verifier_failure_or_untrusted_shape_fails_before_storage(self):
        factory = Mock(wraps=fixtures.app.state.workflow_connection_factory)
        fixtures.app.state.workflow_connection_factory = factory
        for value in (None, {'owner_id': self.owner, 'is_anonymous': True},
                      VerifiedGuestSession(Principal(owner_id=self.owner, mode='trusted_local'), True)):
            self.auth.verify_session = Mock(return_value=value)
            with self.subTest(kind=type(value).__name__):
                self.assertEqual(self.boot().status_code, 401)
        self.auth.verify_session = Mock(side_effect=RuntimeError('unavailable'))
        self.assertEqual(self.boot().status_code, 401)
        factory.assert_not_called()

    def test_request_owned_transaction_commits_before_acknowledgement(self):
        self.fixture._use_transactional_factory()
        first = self.boot()
        self.assertEqual(first.status_code, 200, first.text)
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 2)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_examples').fetchone()[0], 2)
        self.assertEqual(self.boot().json(), first.json())

    def test_request_owned_commit_failure_has_no_success_or_partial_records(self):
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE guest_outer_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE guest_outer_child(parent_id INTEGER REFERENCES guest_outer_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_guest_outer AFTER INSERT ON workflow_guest_examples BEGIN INSERT INTO guest_outer_child VALUES (999); END;')
            conn.commit()
        self.fixture._use_transactional_factory()
        with self.assertRaises(sqlite3.IntegrityError):
            self.boot()
        with closing(connect(self.fixture.db_path)) as conn:
            for table in ('workflow_items', 'workflow_guest_examples', 'workflow_idempotency'):
                self.assertEqual(conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_guest_outer')
            conn.commit()
        self.assertEqual(self.boot().status_code, 200)

    def test_hosted_guest_cannot_fall_back_to_default_sqlite(self):
        for environment in ({'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}, {'VERCEL': '1'}):
            with self.subTest(environment=environment), patch.dict(fixtures.app.state._state, clear=False), \
                 patch.dict(os.environ, environment), \
                 patch('content_machine.api.app._make_db') as default_storage:
                fixtures.app.state._state.pop('workflow_connection_factory', None)
                response = self.boot()
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()['code'], 'workflow_storage_misconfigured')
                default_storage.assert_not_called()
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_examples').fetchone()[0], 0)

    def test_hosted_missing_or_invalid_auth_fails_before_storage_configuration(self):
        factory = Mock(wraps=fixtures.app.state.workflow_connection_factory)
        cases = ({}, {'Authorization': 'Basic not-a-session'}, {'Authorization': 'Bearer forged'},
                 {'Authorization': 'Bearer ' + self.token(anonymous=False)},
                 {'Authorization': 'Bearer ' + self.token(exp=int(time.time()) - 1)})
        for configured_factory in (False, True):
            with self.subTest(configured_factory=configured_factory), \
                 patch.dict(fixtures.app.state._state, clear=False), \
                 patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), \
                 patch('content_machine.api.app._make_db') as default_storage:
                if configured_factory:
                    fixtures.app.state.workflow_connection_factory = factory
                else:
                    fixtures.app.state._state.pop('workflow_connection_factory', None)
                for headers in cases:
                    response = self.client.post('/api/workflow/guest/bootstrap', json={}, headers=headers)
                    self.assertEqual(response.status_code, 401, response.text)
                    self.assertEqual(response.json()['code'], 'unauthenticated')
                default_storage.assert_not_called()
        factory.assert_not_called()
