"""Normal private API entry with real default local storage and disposable data.

This exercises fresh/reopened HTTP clients, not a deployed process restart.
Hosted durability remains a separate integration gate.
"""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import test_workflow_api_items as fixtures
from content_machine.storage.db import DB_NAME, connect
from content_machine.storage.paths import ensure_tree
from content_machine.workflow.recovery import inspect_database


class PrivateRestartTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home = Path(self.fixture._home.name)

    def test_empty_private_default_storage_retains_saved_work_after_seed_refresh_and_client_reopen(self):
        app = fixtures.app
        with patch.dict(app.state._state, clear=False), \
             patch('content_machine.demo_seed.seed_demo') as seed_demo:
            # Use the real app's default SQLite factory rather than the fixture
            # factory. CONTENT_MACHINE_HOME already points to disposable data;
            # only the trusted authenticator is injected for this HTTP check.
            app.state._state.pop('workflow_connection_factory', None)
            database = self.home / DB_NAME
            self.assertFalse(database.exists())
            with TestClient(app) as first:
                self.assertEqual(first.get('/api/workflow/items').json(), {'items': []})
                initial = first.get('/api/workflow/settings').json()
                self.assertEqual(initial['profile'], {'name': '', 'role': '', 'bio': '',
                                                      'revision': 0, 'updated_at': None})
                self.assertEqual(initial['sources'], [])
                self.assertEqual(first.get('/api/workflow/preferences').json(), {'preferences': []})
                self.assertTrue(database.exists())

                profile = first.put('/api/workflow/settings/profile', json={
                    'name': '  Real creator  ', 'role': '', 'bio': 'My factual notes\n', 'expected_revision': 0,
                }, headers={'Idempotency-Key': 'private-profile'})
                self.assertEqual(profile.status_code, 200, profile.text)
                created = first.post('/api/workflow/items', json={
                    'title': 'Owned real draft', 'destination': 'linkedin', 'format': 'linkedin_post',
                }, headers={'Idempotency-Key': 'private-create'})
                self.assertEqual(created.status_code, 201, created.text)
                item_id = created.json()['item']['item_id']
                item_path = '/api/workflow/items/' + item_id
                exact = '  My saved observation.\nCaf\u00e9 and trailing spaces.  '
                saved = first.patch(item_path, json={'expected_revision': 1,
                    'context': {'notes': '  Original supporting notes\n'}, 'artifact': {'segments': [exact]}},
                    headers={'Idempotency-Key': 'private-save'})
                self.assertEqual(saved.status_code, 200, saved.text)
                digest = 'sha256:' + hashlib.sha256(json.dumps({'destination': 'linkedin',
                    'format': 'linkedin_post', 'segments': [exact]}, ensure_ascii=False,
                    sort_keys=True, separators=(',', ':')).encode()).hexdigest()
                approved = first.post(item_path + '/approve', json={'expected_revision': 2,
                    'artifact_digest': digest, 'consent': True},
                    headers={'Idempotency-Key': 'private-approve'})
                self.assertEqual(approved.status_code, 200, approved.text)
                version_id = approved.json()['approval']['version_id']
                before_item = first.get(item_path).json()
                before_settings = first.get('/api/workflow/settings').json()
                before_history = first.get(item_path + '/versions').json()
            fingerprint = inspect_database(database)['fingerprint']

            seeds = self.home / 'test-seeds'
            seeds.mkdir()
            (seeds / '01_style-guide.md').write_text('New authoring seed', encoding='utf-8')
            for _ in range(2):
                with patch('content_machine.storage.paths.SEED_DIR', seeds), \
                     patch.dict('os.environ', {'DEMO_MODE': '0'}):
                    tree = ensure_tree()
                self.assertEqual((tree['knowledge'] / '01_style-guide.md').read_text(encoding='utf-8'),
                                 'New authoring seed')
                # Normal initialization really re-runs migrations on reopen.
                with closing(connect(database)):
                    pass
                with TestClient(app) as reopened:
                    self.assertEqual(reopened.get(item_path).json(), before_item)
                    self.assertEqual(reopened.get('/api/workflow/settings').json(), before_settings)
                    self.assertEqual(reopened.get(item_path + '/versions').json(), before_history)
                    exported = reopened.get(item_path + '/exports/' + version_id)
                    self.assertEqual(exported.status_code, 200, exported.text)
                    self.assertEqual(exported.content, exact.encode())
                    self.assertEqual(exported.headers['x-artifact-digest'], digest)
                    self.assertEqual(reopened.get('/api/workflow/preferences').json(), {'preferences': []})
                    listed = reopened.get('/api/workflow/items').json()['items']
                    self.assertEqual([row['item_id'] for row in listed], [item_id])
                    self.assertNotIn('guest_example_label', listed[0])
                self.assertEqual(inspect_database(database)['fingerprint'], fingerprint)
            seed_demo.assert_not_called()
