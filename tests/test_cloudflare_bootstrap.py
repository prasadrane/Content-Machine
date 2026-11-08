"""Cloudflare routing is explicitly configured, without network access."""
import unittest
from unittest.mock import patch
from pathlib import Path

from content_machine.bootstrap import make_router
from content_machine.config import AppConfig, load_config


class CloudflareBootstrapTest(unittest.TestCase):
    def config(self):
        return AppConfig.model_validate({
            'routes': {'workers': {'protocol': 'cloudflare_workers_ai',
                'account_id_env': 'CM_TEST_CF_ACCOUNT', 'api_key_env': 'CM_TEST_CF_TOKEN'}},
            'route_models': {'@cf/*': ['workers']},
        })

    def test_configured_route_uses_the_cloudflare_adapter(self):
        with patch.dict('os.environ', {'CM_TEST_CF_ACCOUNT': 'a' * 32, 'CM_TEST_CF_TOKEN': 'test-token'}), \
             patch('content_machine.router.cloudflare_workers_ai.CloudflareWorkersAI') as adapter:
            router = make_router(self.config())
        adapter.assert_called_once_with('a' * 32, 'test-token', timeout_s=30.0)
        self.assertIs(router.routes['workers'].adapter, adapter.return_value)
        self.assertEqual(router.routes['workers'].protocol, 'cloudflare_workers_ai')

    def test_missing_credentials_cannot_become_a_messages_route(self):
        with patch.dict('os.environ', {'CM_TEST_CF_ACCOUNT': '', 'CM_TEST_CF_TOKEN': ''}):
            router = make_router(self.config())
        self.assertNotIn('workers', router.routes)

    def test_repository_cloudflare_candidate_is_explicit_without_changing_relay_defaults(self):
        path = Path(__file__).resolve().parents[1] / 'config.json'
        with patch.dict('os.environ', {'DEMO_MODE': ''}):
            cfg = load_config(path)
        route = cfg.routes['cloudflare_workers_ai']
        self.assertEqual(route.protocol, 'cloudflare_workers_ai')
        self.assertEqual(route.account_id_env, 'CLOUDFLARE_ACCOUNT_ID')
        self.assertEqual(route.api_key_env, 'CLOUDFLARE_API_TOKEN')
        candidate = '@cf/qwen/qwen3.8-27b'
        self.assertEqual(cfg.route_models[candidate], ['cloudflare_workers_ai'])
        self.assertEqual(cfg.route_models['*'], ['token_plan_relay'])
        self.assertEqual(cfg.models.writer, 'qwen3.8-max')
        # Exact model mapping wins even with the existing wildcard fallback.
        self.assertEqual(make_router(cfg)._routes_for(candidate), ['cloudflare_workers_ai'])
