"""Authenticated guest AI fails closed with saved content and actionable errors."""
import unittest
from unittest.mock import Mock, patch

import test_workflow_guest_bootstrap_api as fixtures
from content_machine.api.app import app
from content_machine.config import AppConfig
from content_machine.router.base import ModelRouter, Route
from content_machine.workflow.schemas import Artifact
from test_workflow_provider_execution import POLICY, MODEL


class GuestBudgetApiTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.GuestBootstrapApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.token = self.fixture.token()
        self.assertEqual(self.fixture.boot(self.token).status_code, 200)
        self.headers = {'Authorization': 'Bearer ' + self.token, 'Idempotency-Key': 'guest-ai'}
        self.generator = Mock(return_value={'segments': ['Must not call this provider']})
        app.state.workflow_generator = self.generator

    def test_unconfigured_guest_ai_is_actionable_durable_and_does_not_call_provider(self):
        items = self.client.get('/api/workflow/items', headers=self.headers).json()['items']
        item = items[0]
        url = '/api/workflow/items/' + item['item_id']
        original = self.client.get(url, headers=self.headers).json()['item']
        with patch.dict('os.environ', {'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': ''}):
            response = self.client.post(url + '/generate', json={'expected_revision': item['working_revision']}, headers=self.headers)
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()['code'], 'guest_budget_unconfigured')
        self.assertEqual(response.json()['operation']['error']['code'], 'guest_budget_unconfigured')
        self.assertEqual(self.client.get(url, headers=self.headers).json()['item'], original)
        self.generator.assert_not_called()

    def test_actual_guest_adapter_quota_and_metadata_are_durable_across_retry(self):
        app.state._state.pop('workflow_generator', None)
        seen = []
        class Adapter:
            def complete(self, **kwargs):
                seen.append(kwargs)
                return Artifact(segments=['A source-grounded proposal'])
        def router(_):
            return ModelRouter({'free': Route('free', 'cloudflare_workers_ai', Adapter())})
        cfg = AppConfig()
        cfg.models.writer = MODEL
        policy = {**POLICY, 'CONTENT_MACHINE_WORKFLOW_AI': '1',
                  'CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS': '1000000'}
        items = self.client.get('/api/workflow/items', headers=self.headers).json()['items']
        with patch.dict('os.environ', policy), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', side_effect=router):
            first = self.client.post('/api/workflow/items/' + items[0]['item_id'] + '/generate',
                json={'expected_revision': items[0]['working_revision']}, headers=self.headers)
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()['operation']['result']['provider_calls'][0]['model'], MODEL)
            retry = self.client.post('/api/workflow/items/' + items[0]['item_id'] + '/generate',
                json={'expected_revision': items[0]['working_revision']}, headers=self.headers)
            self.assertEqual(retry.json(), first.json())
            denied = self.client.post('/api/workflow/items/' + items[1]['item_id'] + '/generate',
                json={'expected_revision': items[1]['working_revision']},
                headers={**self.headers, 'Idempotency-Key': 'second-guest-ai'})
        self.assertEqual(denied.status_code, 429, denied.text)
        self.assertEqual(denied.json()['code'], 'guest_budget_exhausted')
        self.assertFalse(denied.json()['operation']['error']['provider_calls'][0]['dispatched'])
        self.assertEqual(len(seen), 1)
