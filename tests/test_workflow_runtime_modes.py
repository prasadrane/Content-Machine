"""CONTENT_MACHINE_WORKFLOW_AI mode matrix and free-router wiring (offline)."""
import unittest
from unittest.mock import Mock, patch

from content_machine.workflow import runtime
from content_machine.workflow.runtime import get_provider

CREDENTIALS = ('GEMINI_API_KEY', 'CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'CONTENT_MACHINE_AI_PROVIDERS')


def environment(ai=None, hosted=False, **extra):
    env = {'GEMINI_API_KEY': '', 'CLOUDFLARE_ACCOUNT_ID': '', 'CLOUDFLARE_API_TOKEN': ''}
    if ai is not None:
        env['CONTENT_MACHINE_WORKFLOW_AI'] = ai
    if hosted:
        env['CONTENT_MACHINE_DEPLOYMENT_MODE'] = 'hosted'
    env.update(extra)
    return env


class State:
    pass


class RuntimeModeTest(unittest.TestCase):
    def provider(self, env, remove=()):
        with patch.dict('os.environ', env):
            import os
            for name in ('CONTENT_MACHINE_WORKFLOW_AI', 'CONTENT_MACHINE_DEPLOYMENT_MODE', 'VERCEL', *remove):
                if name not in env:
                    os.environ.pop(name, None)
            return get_provider(Mock(state=State()), 'generate')

    def test_mode_matrix(self):
        key = {'GEMINI_API_KEY': 'fixture-key'}
        cases = [
            ('0 is off even when hosted with credentials', environment('0', hosted=True, **key), None),
            ('1 is the legacy router regardless of free credentials', environment('1'), runtime.generate),
            ('auto with a credential is on', environment('auto', **key), runtime.generate),
            ('auto without credentials is off', environment('auto'), None),
            ('unset hosted with a credential is on', environment(None, hosted=True, **key), runtime.generate),
            ('unset hosted without credentials is off', environment(None, hosted=True), None),
            ('unset local with a credential stays off', environment(None, **key), None),
            ('blank local with a credential stays off', environment('', **key), None),
        ]
        for label, env, expected in cases:
            with self.subTest(label):
                self.assertIs(self.provider(env), expected)

    def test_auto_generation_uses_free_router_and_never_the_relay(self):
        snapshot = object()
        env = environment('auto', GEMINI_API_KEY='fixture-key')
        with patch.dict('os.environ', env), \
             patch.object(runtime, 'make_router', side_effect=AssertionError('relay router built')), \
             patch.object(runtime, 'generate_proposal', return_value='proposal') as generate:
            self.assertEqual(runtime.generate(snapshot), 'proposal')
        router, models = generate.call_args.args[1], generate.call_args.args[2]
        self.assertEqual(list(router.routes), ['gemini'])
        self.assertEqual(models, ['free-strong'])
        self.assertTrue(all(r.protocol != 'anthropic_messages' for r in router.routes.values()))

    def test_auto_review_passes_the_free_config_to_council(self):
        env = environment('auto', GEMINI_API_KEY='fixture-key')
        with patch.dict('os.environ', env), \
             patch.object(runtime, 'make_router', side_effect=AssertionError('relay router built')), \
             patch.object(runtime, 'review_snapshot', return_value={'actions': {'notes': []}}) as council, \
             patch.object(runtime, 'suggest_wording', return_value=[]), \
             patch.object(runtime, 'validate_review_advice', lambda advice, snapshot: advice):
            runtime.review(object())
        router, cfg = council.call_args.args[1], council.call_args.args[2]
        self.assertEqual(list(router.routes), ['gemini'])
        self.assertEqual((cfg.routes, cfg.models.writer), ({}, 'free-strong'))

    def test_injected_none_still_disables_in_auto_mode(self):
        app = Mock()
        app.state.workflow_generator = None
        with patch.dict('os.environ', environment('auto', GEMINI_API_KEY='fixture-key')):
            self.assertIsNone(get_provider(app, 'generate'))


class RuntimeCapabilitiesTest(unittest.TestCase):
    def setUp(self):
        import test_workflow_api_items as fixtures
        from content_machine.api.app import app
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        patcher = patch.dict(app.state._state, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        app.state._state.pop('workflow_generator', None)
        app.state._state.pop('workflow_reviewer', None)

    def capabilities(self, env):
        with patch.dict('os.environ', env):
            return self.client.get('/api/workflow/capabilities').json()['pairs']

    def test_capabilities_follow_free_credentials_in_auto_mode(self):
        on = self.capabilities(environment('auto', GEMINI_API_KEY='fixture-key'))
        self.assertTrue(on and all(p['can_generate'] and p['can_review'] for p in on))
        off = self.capabilities(environment('auto'))
        self.assertTrue(off and all(not p['can_generate'] and not p['can_review'] for p in off))
