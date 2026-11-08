"""The normal app entry point gates unscoped legacy data when hosted."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from content_machine.api.app import app
from starlette.routing import Mount


class LegacyHttpTest(unittest.TestCase):
    def test_registered_surface_inventory(self):
        """Print the audited registration rather than infer it from source grep."""
        for route in app.routes:
            methods = ','.join(sorted(getattr(route, 'methods', ()) or ())) or 'MOUNT'
            print(f'C47_ROUTE {methods} {route.path}')
            self.assertTrue(route.path.startswith('/api/') or route.path in {
                '/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc',
                '/assets', '/{full_path:path}'}, route.path)

    def test_unknown_hosted_api_paths_keep_404(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), TestClient(app) as client:
            for path in ['/api', '/api/not-a-route', '/api/profile/not-a-route', '/api/workflow-other']:
                with self.subTest(path=path):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 404, response.text)

    def test_every_registered_legacy_route_is_denied_before_handler_or_dependencies(self):
        """Use actual registration, including wrong methods and hostile IDs."""
        with patch.dict('os.environ', {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), \
             patch('content_machine.api.app._make_db') as database, \
             patch('content_machine.api.app._make_router') as router, \
             patch('content_machine.api.app.ProfileManager') as profile, TestClient(app) as client:
            audited = []
            for route in app.routes:
                path = route.path
                if not path.startswith('/api/') or path.startswith('/api/workflow/') or path in {'/api/health', '/api/meta'}:
                    continue
                path = path.replace('{spike_id}', 'creator-A-private').replace('{rule_id}', '123')
                audited.append(route.path)
                for method in sorted(set(route.methods) | {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD'}):
                    with self.subTest(path=path, method=method):
                        response = client.request(method, path, content=b'not valid JSON', headers={
                            'X-Owner-ID': 'creator-A', 'Authorization': 'Bearer forged',
                            'X-Forwarded-For': '127.0.0.1', 'Content-Type': 'application/json'})
                        self.assertEqual(response.status_code, 410, response.text)
            self.assertEqual(len(audited), 22)
        database.assert_not_called()
        router.assert_not_called()
        profile.assert_not_called()

    def test_only_build_assets_are_mounted_and_spa_never_reads_requested_files(self):
        mounts = [route for route in app.routes if isinstance(route, Mount)]
        self.assertTrue(all(route.path == '/assets' for route in mounts))
        for route in mounts:
            self.assertFalse(route.app.follow_symlink)
            self.assertEqual(str(route.app.directory), str(__import__('content_machine.api.app', fromlist=['_UI_DIST'])._UI_DIST / 'assets'))
        with patch.dict('os.environ', {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), TestClient(app) as client:
            for path in ['/projects/creator-A/distribution/anchor.md', '/knowledge/02_voice-guide.md', '/state.db', '/editor/deep-link']:
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('creator-A-private', response.text)

    def test_hosted_global_data_routes_are_denied_before_storage(self):
        with patch.dict('os.environ', {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), \
             patch('content_machine.api.app._make_db') as database, \
             patch('content_machine.api.app.ProfileManager') as profile, TestClient(app) as client:
            for method, path in [('GET', '/api/profile'), ('POST', '/api/profile'),
                                 ('GET', '/api/lessons'), ('POST', '/api/oracle/run'),
                                 ('GET', '/api/distribute/history')]:
                response = client.request(method, path, json={})
                self.assertEqual(response.status_code, 410, response.text)
            self.assertEqual(client.get('/api/health').status_code, 200)
        database.assert_not_called()
        profile.assert_not_called()
