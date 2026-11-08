"""Normal-app dual-session guest copy routes with ephemeral signed fixtures."""
from contextlib import closing
import sqlite3
import unittest
import uuid
from unittest.mock import Mock

import test_workflow_guest_bootstrap_api as fixtures
from content_machine.api.app import app
from content_machine.storage.db import connect
from content_machine.workflow.guest_transfer import migrate_guest_transfer
from content_machine.workflow.schemas import Principal


class GuestTransferApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GuestBootstrapApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.guest = self.fixture.token()
        self.creator_id = str(uuid.uuid4())
        self.creator = self.fixture.token(owner=self.creator_id, anonymous=False)
        self.other = self.fixture.token(owner=str(uuid.uuid4()), anonymous=False)
        with closing(connect(self.fixture.fixture.db_path)) as conn:
            migrate_guest_transfer(conn)
        self.assertEqual(self.fixture.boot(self.guest).status_code, 200)

    def headers(self, creator=None, guest=None, key='copy-key'):
        return {'Authorization': 'Bearer ' + (creator or self.creator),
                'X-Guest-Authorization': 'Bearer ' + (guest or self.guest), 'Idempotency-Key': key}

    def preview(self, headers=None):
        return self.client.post('/api/workflow/guest/transfer/preview', json={}, headers=self.headers() if headers is None else headers)

    def confirm(self, fingerprint, **kwargs):
        return self.client.post('/api/workflow/guest/transfer',
            json={'consent': True, 'source_fingerprint': fingerprint}, **kwargs)

    def test_preview_copy_receipt_and_retry_use_verified_creator_and_leave_guest_intact(self):
        preview = self.preview()
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['item_count'], 2)
        fingerprint = preview.json()['source_fingerprint']
        copied = self.confirm(fingerprint, headers=self.headers())
        self.assertEqual(copied.status_code, 200, copied.text)
        self.assertEqual(copied.json(), self.confirm(fingerprint, headers=self.headers()).json())
        self.assertEqual(self.preview().json()['source_fingerprint'], fingerprint)
        receipt_url = '/api/workflow/guest/transfers/' + copied.json()['transfer_id']
        receipt = self.client.get(receipt_url, headers={'Authorization': 'Bearer ' + self.creator})
        self.assertEqual(receipt.status_code, 200, receipt.text)
        self.assertIs(receipt.json()['editorial_approval'], False)
        for token in (self.other, self.guest):
            denied = self.client.get(receipt_url, headers={'Authorization': 'Bearer ' + token})
            self.assertIn(denied.status_code, (401, 404))
        payload = str(receipt.json()) + str(copied.json())
        self.assertNotIn(self.guest, payload)
        self.assertNotIn(self.creator, payload)

    def test_invalid_missing_reversed_and_same_subject_proofs_fail_before_storage(self):
        factory = Mock(wraps=app.state.workflow_connection_factory)
        app.state.workflow_connection_factory = factory
        cases = [{}, {'Authorization': 'Bearer ' + self.creator},
                 self.headers(creator=self.guest), self.headers(guest=self.creator),
                 self.headers(guest='forged'), self.headers(creator='forged'),
                 self.headers(creator=self.fixture.token(anonymous=False)),
                 {**self.headers(), 'X-Guest-Authorization': 'Basic abc'}]
        for headers in cases:
            with self.subTest(headers=list(headers)):
                result = self.preview(headers=headers)
                self.assertIn(result.status_code, (401, 409), result.text)
        factory.assert_not_called()

    def test_owner_fields_missing_key_and_nonboolean_consent_rejected(self):
        fingerprint = self.preview().json()['source_fingerprint']
        for payload in ({'consent': 'true', 'source_fingerprint': fingerprint},
                        {'consent': True, 'source_fingerprint': fingerprint, 'owner_id': 'victim'}):
            result = self.client.post('/api/workflow/guest/transfer', json=payload, headers=self.headers())
            self.assertEqual(result.status_code, 422, result.text)
        headers = self.headers()
        headers.pop('Idempotency-Key')
        self.assertEqual(self.confirm(fingerprint, headers=headers).status_code, 422)
        result = self.client.post('/api/workflow/guest/transfer',
            json={'consent': False, 'source_fingerprint': fingerprint}, headers=self.headers())
        self.assertEqual(result.status_code, 422)
        with closing(connect(self.fixture.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)

    def test_missing_session_verifier_is_typed_unavailable_before_storage(self):
        app.state.workflow_authenticator = lambda request: Principal(owner_id=self.creator_id, mode='hosted_verified')
        factory = Mock(wraps=app.state.workflow_connection_factory)
        app.state.workflow_connection_factory = factory
        response = self.preview()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'guest_auth_unavailable')
        factory.assert_not_called()

    def test_commit_failure_does_not_return_success_or_persist_partial_target(self):
        fingerprint = self.preview().json()['source_fingerprint']
        with closing(connect(self.fixture.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE transfer_api_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE transfer_api_child(id INTEGER REFERENCES transfer_api_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_transfer_api AFTER INSERT ON workflow_guest_transfers BEGIN INSERT INTO transfer_api_child VALUES(999); END;')
            conn.commit()
        self.fixture.fixture._use_transactional_factory()
        with self.assertRaises(sqlite3.IntegrityError):
            self.confirm(fingerprint, headers=self.headers())
        with closing(connect(self.fixture.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_guest_transfers').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_items WHERE owner_id=?',
                                          (self.creator_id,)).fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_transfer_api')
            conn.commit()
        self.assertEqual(self.confirm(fingerprint, headers=self.headers()).status_code, 200)
