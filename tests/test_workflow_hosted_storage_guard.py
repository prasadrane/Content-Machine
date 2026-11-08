"""Hosted requests must not accidentally acknowledge local SQLite storage."""
import os
import unittest
from unittest.mock import patch

from content_machine.api.app import app
from content_machine.storage.db import connect
from workflow_action_fixtures import ActionApiFixture


class HostedStorageGuardTest(ActionApiFixture, unittest.TestCase):
    def test_hosted_without_a_configured_factory_never_opens_default_sqlite(self):
        for environment in ({'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}, {'VERCEL': '1'}):
            with self.subTest(environment=environment), patch.dict(app.state._state, clear=False), \
                 patch.dict(os.environ, environment), \
                 patch('content_machine.api.app._make_db') as default_storage:
                app.state._state.pop('workflow_connection_factory', None)
                requests = [
                    ('GET', '/api/workflow/items', None),
                    ('GET', '/api/workflow/settings', None),
                    ('POST', '/api/workflow/items', {'title': 'A private idea',
                        'destination': 'linkedin', 'format': 'linkedin_post'}),
                    ('POST', '/api/workflow/preferences', {'text': 'Use examples.', 'consent': True}),
                ]
                for method, path, body in requests:
                    response = self.client.request(method, path, json=body,
                        headers={'Idempotency-Key': 'storage-unavailable'})
                    self.assertEqual(response.status_code, 503, response.text)
                    self.assertEqual(response.json()['code'], 'workflow_storage_misconfigured')
                    self.assertIn('durable storage', response.json()['detail'].lower())
                default_storage.assert_not_called()

    def test_supported_local_default_and_explicit_factory_keep_existing_work(self):
        item, text = self.saved_item()
        with patch.dict(app.state._state, clear=False), \
             patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': ''}), \
             patch('content_machine.api.app._make_db', side_effect=lambda: connect(self.fixture.db_path)) as default_storage:
            app.state._state.pop('workflow_connection_factory', None)
            self.assertEqual(self._item(item['item_id'])['artifact']['segments'], [text])
            default_storage.assert_called_once()
        with patch.dict(os.environ, {'CONTENT_MACHINE_DEPLOYMENT_MODE': 'hosted'}), \
             patch('content_machine.api.app._make_db') as default_storage:
            self.assertEqual(self._item(item['item_id'])['artifact']['segments'], [text])
            default_storage.assert_not_called()
