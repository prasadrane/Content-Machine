"""Opt-in mounted HTTP acceptance backed by a disposable PostgreSQL schema.

Only JWT signing/JWKS and AI output are fixtures. Actual routing, authentication
validation, service SQL, PostgreSQL transactions and response bytes are used.
"""
from pathlib import Path
import os
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_postgres_workflow import LivePostgresWorkflowTest, _HOME
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
import jwt

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.hosted_auth import SupabaseAuthenticator
from content_machine.workflow.http import workflow_error_response, workflow_validation_response
from content_machine.workflow.routes import router
from content_machine.workflow.schemas import Artifact
from content_machine.workflow.versions import artifact_digest
from content_machine.config import AppConfig
from content_machine.router.base import ModelRouter, Route


class LivePostgresHttpTest(LivePostgresWorkflowTest):
    def setUp(self):
        super().setUp()
        environment = patch.dict(os.environ, {'CONTENT_MACHINE_WORKFLOW_MODE': 'hosted',
            'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted', 'CONTENT_MACHINE_WORKFLOW_AI': '0'})
        environment.start()
        self.addCleanup(environment.stop)
        self.key = ec.generate_private_key(ec.SECP256R1())
        keys = Mock()
        keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        self.app = FastAPI()
        self.app.add_exception_handler(WorkflowError, lambda request, error: workflow_error_response(error))
        self.app.add_exception_handler(RequestValidationError, lambda request, error: workflow_validation_response(error))
        self.app.include_router(router)
        self.app.state.workflow_authenticator = SupabaseAuthenticator('https://example.supabase.co', jwks_client=keys)
        self.factory = Mock(side_effect=self.session)
        self.app.state.workflow_connection_factory = self.factory
        self.app.state.workflow_generator = Mock(return_value={'segments': ['A bounded queue makes overload visible.']})
        self.creator = self.token(self.a.owner_id, False)
        self.other = self.token(self.b.owner_id, False)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def token(self, owner, anonymous):
        return jwt.encode({'iss': 'https://example.supabase.co/auth/v1', 'aud': 'authenticated',
            'sub': owner, 'role': 'authenticated', 'is_anonymous': anonymous,
            'iat': int(time.time()) - 5, 'exp': int(time.time()) + 300},
            self.key, algorithm='ES256', headers={'kid': 'fixture'})

    def request(self, method, path, payload=None, key=None, token=None, extra=None):
        headers = {'Authorization': 'Bearer ' + (token or self.creator), **(extra or {})}
        if key is not None:
            headers['Idempotency-Key'] = key
        return self.client.request(method, '/api/workflow' + path, json=payload, headers=headers)

    def created(self):
        response = self.request('POST', '/items', {'title': 'Mounted HTTP fixture',
            'destination': 'linkedin', 'format': 'linkedin_post'}, key='create')
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['item']

    def test_http_detail_approval_history_exact_download_and_isolation(self):
        item = self.created()
        item_id = item['item_id']
        # This exercises the mounted detail's latest-review timestamp query,
        # including its empty-history path against actual timestamptz columns.
        detail = self.request('GET', '/items/' + item_id)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIsNone(detail.json()['review'])
        text = 'A bounded queue makes overload visible.\nExact HTTP fixture.  '
        saved = self.request('PATCH', '/items/' + item_id, {'expected_revision': 1,
            'artifact': {'segments': [text]}}, key='save')
        self.assertEqual(saved.status_code, 200, saved.text)
        def advice(snapshot):
            score = {'narrative': 8, 'velocity': 8, 'depth': 8, 'slop_purity': 8,
                     'threshold_met': False, 'verdict': 'revise', 'required_actions': ['Clarify']}
            return {'actions': {'required_actions': ['Clarify'], 'notes': []}, 'proposals': [],
                'score_basis': {'input_version_id': snapshot.version_id, 'normalized': None,
                    'raw': {'scale': [0, 10], 'composite': 8, 'judges': {'a': score, 'b': score, 'c': score}}}}
        self.app.state.workflow_reviewer = advice
        review = self.request('POST', '/items/' + item_id + '/review', {'expected_revision': 2}, key='review')
        self.assertEqual(review.status_code, 200, review.text)
        reviewed_detail = self.request('GET', '/items/' + item_id)
        self.assertEqual(reviewed_detail.json()['review']['state'], 'completed')
        self.assertEqual(reviewed_detail.json()['item']['artifact']['segments'], [text])
        approval = self.request('POST', '/items/' + item_id + '/approve', {'expected_revision': 2,
            'artifact_digest': artifact_digest('linkedin', 'linkedin_post', Artifact(segments=[text])),
            'consent': True}, key='approve')
        self.assertEqual(approval.status_code, 200, approval.text)
        version_id = approval.json()['approval']['version_id']
        history = self.request('GET', '/items/' + item_id + '/versions')
        self.assertEqual(history.status_code, 200, history.text)
        download = self.request('GET', '/items/' + item_id + '/exports/' + version_id)
        self.assertEqual(download.status_code, 200, download.text)
        self.assertEqual(download.content, text.encode('utf-8'))
        approved_detail = self.request('GET', '/items/' + item_id)
        self.assertEqual(approved_detail.json()['approval'], approval.json()['approval'])
        self.assertEqual(self.request('GET', '/items/' + item_id, token=self.other).status_code, 404)
        self.assertEqual(self.request('GET', '/items', token=self.other).json()['items'], [])
        # A new client and fresh DB connection still observe durable approval.
        with TestClient(self.app) as reopened:
            durable = reopened.get('/api/workflow/items/' + item_id,
                headers={'Authorization': 'Bearer ' + self.creator})
        self.assertEqual(durable.json(), approved_detail.json())

    def test_http_settings_preferences_generation_retry_and_owned_snapshots(self):
        item_id = self.created()['item_id']
        profile = self.request('PUT', '/settings/profile', {'name': 'Fixture author', 'role': 'Engineer',
            'bio': 'Grounded facts.', 'expected_revision': 0}, key='profile')
        self.assertEqual(profile.status_code, 200, profile.text)
        source = self.request('POST', '/settings/sources', {'kind': 'rss', 'name': 'Fixture feed',
            'url': 'https://example.com/feed', 'enabled': True}, key='source')
        self.assertEqual(source.status_code, 201, source.text)
        preference = self.request('POST', '/preferences', {'text': 'Use concrete observations.',
            'consent': True}, key='preference')
        self.assertEqual(preference.status_code, 201, preference.text)
        operation = self.request('POST', '/items/' + item_id + '/generate', {'expected_revision': 1}, key='generate')
        self.assertEqual(operation.status_code, 200, operation.text)
        op = operation.json()['operation']
        self.assertEqual(op['state'], 'completed')
        self.assertEqual(op['editorial_snapshot']['profile']['name'], 'Fixture author')
        self.assertEqual(len(op['editorial_snapshot']['preferences']), 1)
        replay = self.request('POST', '/items/' + item_id + '/generate', {'expected_revision': 1}, key='generate')
        self.assertEqual(replay.json(), operation.json())
        self.app.state.workflow_generator.assert_called_once()
        fetched = self.request('GET', '/items/' + item_id + '/operations/' + op['operation_id'])
        self.assertEqual(fetched.json(), operation.json())
        self.assertEqual(self.request('GET', '/settings', token=self.other).json()['profile']['revision'], 0)
        self.assertEqual(self.request('GET', '/preferences', token=self.other).json()['preferences'], [])
        self.assertEqual(self.request('GET', '/items/' + item_id + '/operations/' + op['operation_id'], token=self.other).status_code, 404)

    def test_http_guest_bootstrap_transfer_and_receipt_owner(self):
        guest = self.token(self.b.owner_id, True)
        boot = self.request('POST', '/guest/bootstrap', {}, token=guest)
        self.assertEqual(boot.status_code, 200, boot.text)
        self.assertEqual(boot.json(), self.request('POST', '/guest/bootstrap', {}, token=guest).json())
        headers = {'X-Guest-Authorization': 'Bearer ' + guest}
        preview = self.request('POST', '/guest/transfer/preview', {}, extra=headers)
        self.assertEqual(preview.status_code, 200, preview.text)
        consent = {'consent': True, 'source_fingerprint': preview.json()['source_fingerprint']}
        transfer = self.request('POST', '/guest/transfer', consent, key='transfer', extra=headers)
        self.assertEqual(transfer.status_code, 200, transfer.text)
        self.assertEqual(transfer.json(), self.request('POST', '/guest/transfer', consent,
            key='transfer', extra=headers).json())
        receipt_path = '/guest/transfers/' + transfer.json()['transfer_id']
        receipt = self.request('GET', receipt_path)
        self.assertEqual(receipt.status_code, 200, receipt.text)
        self.assertIs(receipt.json()['editorial_approval'], False)
        self.assertEqual(self.request('GET', receipt_path, token=guest).status_code, 401)
        self.assertEqual(self.request('GET', receipt_path, token=self.other).status_code, 404)
        destination = self.request('GET', '/items').json()['items']
        self.assertEqual(len(destination), 2)
        self.assertTrue(all(row['active_approval_id'] is None and row['working_revision'] == 1 for row in destination))
        self.assertTrue(all(row['guest_example_label'] == 'Demo example' for row in destination))

    def test_http_invalid_auth_and_transfer_proofs_do_not_open_database(self):
        self.factory.reset_mock()
        for path in ('/items', '/settings', '/preferences'):
            self.assertEqual(self.client.get('/api/workflow' + path).status_code, 401)
            self.assertEqual(self.request('GET', path, token='forged').status_code, 401)
        guest = self.token(self.b.owner_id, True)
        for token, extra in ((self.creator, {}), (self.creator, {'X-Guest-Authorization': 'Bearer forged'}),
                             (guest, {'X-Guest-Authorization': 'Bearer ' + self.creator})):
            denied = self.request('POST', '/guest/transfer/preview', {}, token=token, extra=extra)
            self.assertEqual(denied.status_code, 401, denied.text)
        self.factory.assert_not_called()

    def test_http_guest_budget_stops_dispatch_and_persists_attempt_metadata(self):
        del self.app.state.workflow_generator
        model = '@cf/qwen/qwen3.8-27b'
        cfg = AppConfig()
        cfg.models.writer = model
        seen = []
        class Adapter:
            def complete(inner, **kwargs):
                seen.append(kwargs)
                return Artifact(segments=['A bounded queue makes overload visible.'])
        def actual_router(_):
            return ModelRouter({'free-fixture': Route('free-fixture', 'cloudflare_workers_ai', Adapter())})
        first_guest = self.token(self.b.owner_id, True)
        second_guest = self.token(self.a.owner_id, True)
        first = self.request('POST', '/guest/bootstrap', {}, token=first_guest).json()['examples'][0]['item']
        second = self.request('POST', '/guest/bootstrap', {}, token=second_guest).json()['examples'][0]['item']
        path = '/items/' + first['item_id'] + '/generate'
        other_path = '/items/' + second['item_id'] + '/generate'
        policy = {'CONTENT_MACHINE_WORKFLOW_AI': '1',
            'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '1000000',
            'CONTENT_MACHINE_GUEST_AI_PER_CALL_MILLINEURONS': '1000000',
            'CONTENT_MACHINE_GUEST_AI_MAX_INFLIGHT': '4',
            'CONTENT_MACHINE_GUEST_AI_MAX_INPUT_BYTES': '4096'}
        with patch.dict(os.environ, policy), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', side_effect=actual_router):
            successful = self.request('POST', path, {'expected_revision': first['working_revision']},
                key='budget-success', token=first_guest)
            self.assertEqual(successful.status_code, 200, successful.text)
            self.assertEqual(self.request('POST', path, {'expected_revision': first['working_revision']},
                key='budget-success', token=first_guest).json(), successful.json())
            denied = self.request('POST', other_path, {'expected_revision': second['working_revision']},
                key='budget-denied', token=second_guest)
            self.assertEqual(denied.status_code, 429, denied.text)
            self.assertEqual(denied.json()['code'], 'guest_budget_exhausted')
            self.assertEqual(self.request('POST', other_path, {'expected_revision': second['working_revision']},
                key='budget-denied', token=second_guest).json(), denied.json())
        self.assertEqual(len(seen), 1)
        completed = successful.json()['operation']
        metadata = completed['result']['provider_calls'][0]
        self.assertEqual((metadata['provider'], metadata['model'], metadata['dispatched']),
                         ('cloudflare_workers_ai', model, True))
        self.assertEqual(metadata['charged_millineurons'], 1000000)
        failure = denied.json()['operation']
        self.assertFalse(failure['error']['provider_calls'][0]['dispatched'])
        for token, operation in ((first_guest, completed), (second_guest, failure)):
            reopened = self.request('GET', '/items/' + operation['item_id'] + '/operations/' + operation['operation_id'], token=token)
            self.assertEqual(reopened.json()['operation'], operation)
        current = self.request('GET', '/items/' + second['item_id'], token=second_guest).json()['item']
        self.assertEqual(current['artifact'], second['artifact'])
        self.assertIsNone(current['active_approval_id'])


if __name__ == '__main__':
    # Intentionally run only this class's HTTP tests, not inherited service tests.
    names = [name for name in LivePostgresHttpTest.__dict__ if name.startswith('test_http_')]
    suite = unittest.TestSuite(LivePostgresHttpTest(name) for name in sorted(names))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    _HOME.cleanup()
    sys.exit(not result.wasSuccessful())
