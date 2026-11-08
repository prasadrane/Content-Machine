"""The hosted boundary must reject legacy handlers before they run."""
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_machine.workflow.legacy_boundary import LegacyBoundaryMiddleware


class LegacyBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        app = FastAPI()
        app.add_middleware(LegacyBoundaryMiddleware)

        @app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
        def api(path: str):
            self.calls.append(path)
            return {'path': path}

        @app.get('/asset')
        def asset():
            self.calls.append('asset')
            return {'ok': True}

        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_hosted_denies_global_routes_even_with_forged_identity(self):
        routes = ['/api/profile', '/api/lessons', '/api/council/history/private',
                  '/api/distribute/history', '/api/oracle/run', '/api/interview/synthesize',
                  '/api/linkedin/sync', '/api/humanize', '/api/workflow-other']
        with patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}, clear=True):
            for route in routes:
                with self.subTest(route=route):
                    response = self.client.post(route, headers={'X-Owner-ID': 'someone', 'Authorization': 'Bearer forged'})
                    self.assertEqual(response.status_code, 410)
                    self.assertEqual(response.json()['code'], 'legacy_unavailable')
            self.assertEqual(self.calls, [])

    def test_vercel_presence_enables_gate_without_other_configuration(self):
        with patch.dict(os.environ, {'VERCEL': ''}, clear=True):
            self.assertEqual(self.client.get('/api/profile').status_code, 410)
            self.assertEqual(self.calls, [])

    def test_hosted_allows_workflow_and_health_metadata_to_continue_normally(self):
        with patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}, clear=True):
            for route in ['/api/workflow', '/api/workflow/items', '/api/health', '/api/meta', '/asset']:
                with self.subTest(route=route):
                    self.assertEqual(self.client.get(route).status_code, 200)

    def test_hosted_does_not_allow_other_methods_on_public_metadata(self):
        with patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}, clear=True):
            for route in ['/api/health', '/api/meta']:
                self.assertEqual(self.client.post(route).status_code, 410)
            self.assertEqual(self.calls, [])

    def test_local_legacy_handlers_remain_available(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.get('/api/profile').status_code, 200)
            self.assertEqual(self.calls, ['profile'])
