"""Explicit runtime opt-in connects the accepted writing adapters."""
import unittest
from unittest.mock import patch, Mock

from content_machine.config import AppConfig
from content_machine.workflow.runtime import get_provider


class WorkflowRuntimeTest(unittest.TestCase):
    def test_unconfigured_runtime_has_no_provider(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': ''}):
            self.assertIsNone(get_provider(Mock(state=object()), 'generate'))

    def test_explicit_disabled_injection_stays_disabled(self):
        app = Mock()
        app.state.workflow_generator = None
        with patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': '1'}):
            self.assertIsNone(get_provider(app, 'generate'))

    def test_configured_runtime_uses_frozen_snapshot(self):
        class State:
            pass
        app = Mock(state=State())
        cfg = AppConfig()
        router = Mock()
        snapshot = object()
        with patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': '1'}), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', return_value=router), \
             patch('content_machine.workflow.runtime.generate_proposal', return_value='proposal') as generate:
            provider = get_provider(app, 'generate')
            self.assertEqual(provider(snapshot), 'proposal')
        generate.assert_called_once_with(snapshot, router, [cfg.models.writer])

    def test_injected_provider_has_priority(self):
        app = Mock()
        provider = lambda snapshot: snapshot
        app.state.workflow_reviewer = provider
        self.assertIs(get_provider(app, 'review'), provider)


class RuntimeHttpTest(unittest.TestCase):
    def setUp(self):
        import test_workflow_api_items as fixtures
        from content_machine.api.app import app
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.app = app
        self.client = self.fixture.client
        self.state_patch = patch.dict(app.state._state, clear=False)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)
        app.state._state.pop('workflow_generator', None)
        app.state._state.pop('workflow_reviewer', None)

    def test_readiness_and_generation_use_the_actual_adapter_for_every_pair(self):
        from content_machine.workflow.format_registry import CANONICAL_PAIRS
        cfg = AppConfig()
        router = Mock()
        with patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': '1'}), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', return_value=router):
            capabilities = self.client.get('/api/workflow/capabilities').json()['pairs']
            self.assertTrue(all(pair['can_generate'] and pair['can_review'] for pair in capabilities))
            for index, (destination, format_id) in enumerate(CANONICAL_PAIRS):
                with self.subTest(format=format_id):
                    created = self.client.post('/api/workflow/items', json={
                        'title': 'An actual source note', 'destination': destination, 'format': format_id,
                    }, headers={'Idempotency-Key': f'create-runtime-{index}'})
                    self.assertEqual(created.status_code, 201, created.text)
                    item = created.json()['item']
                    text = '[Visual Cue] Example [Camera Zoom] [Pause]' if format_id.endswith('_script') else 'Example from notes'
                    segments = [text, 'Second point'] if format_id == 'x_thread' else [text]
                    router.complete.return_value = {'segments': segments}
                    generated = self.client.post(f"/api/workflow/items/{item['item_id']}/generate",
                        json={'expected_revision': 1}, headers={'Idempotency-Key': f'generate-runtime-{index}'})
                    self.assertEqual(generated.status_code, 200, generated.text)
                    self.assertEqual(generated.json()['operation']['result']['artifact']['segments'], segments)
                    current = self.client.get(f"/api/workflow/items/{item['item_id']}").json()['item']
                    self.assertEqual(current['artifact']['segments'], [])

    def test_readiness_is_false_without_opt_in_or_injection(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': ''}):
            response = self.client.get('/api/workflow/capabilities')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(not pair['can_generate'] and not pair['can_review']
                            for pair in response.json()['pairs']))
