"""Support features are mounted on the real app and upgrade existing databases."""
import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

import test_workflow_api_items as fixtures
from content_machine.api.app import app
from content_machine.storage.db import connect
from content_machine.workflow.migrations import migrate_workflow


class WorkflowSupportIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client

    def test_settings_routes_are_available_in_the_normal_application(self):
        initial = self.client.get('/api/workflow/settings')
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()['profile']['name'], '')
        self.assertEqual(initial.json()['sources'], [])
        saved = self.client.put('/api/workflow/settings/profile', json={
            'name': '  A creator  ', 'role': '', 'bio': '', 'expected_revision': 0,
        }, headers={'Idempotency-Key': 'integration-profile'})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.get('/api/workflow/settings').json()['profile']['name'], '')
        self.fixture._as(self.fixture.a)
        self.assertEqual(self.client.get('/api/workflow/settings').json()['profile']['name'], '  A creator  ')

    def test_existing_database_upgrades_without_changing_legacy_data(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE legacy_evidence (value TEXT NOT NULL)')
            conn.execute('INSERT INTO legacy_evidence VALUES (?)', ('preserve exactly',))
            migrate_workflow(conn)
            migrate_workflow(conn)
            self.assertEqual(conn.execute('SELECT value FROM legacy_evidence').fetchone()[0], 'preserve exactly')
            names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({'workflow_profiles', 'workflow_sources', 'workflow_preferences',
                             'workflow_preference_events'} <= names)

    def test_settings_survive_reopen_migration_and_seed_refresh(self):
        from content_machine.storage.paths import sync_seed
        profile = self.client.put('/api/workflow/settings/profile', json={
            'name': 'Creator', 'role': 'Engineer', 'bio': 'Real context', 'expected_revision': 0,
        }, headers={'Idempotency-Key': 'persist-profile'})
        self.assertEqual(profile.status_code, 200, profile.text)
        source = self.client.post('/api/workflow/settings/sources', json={
            'kind': 'rss', 'name': 'Feed', 'url': 'https://example.org/feed', 'enabled': True,
        }, headers={'Idempotency-Key': 'persist-source'})
        self.assertEqual(source.status_code, 201, source.text)
        before = self.client.get('/api/workflow/settings').json()
        with closing(connect(self.fixture.db_path)) as conn:
            migrate_workflow(conn)
            conn.commit()
        seed = Path(self.fixture._home.name) / 'seed.md'
        runtime = Path(self.fixture._home.name) / 'runtime.md'
        seed.write_text('New seed', encoding='utf-8')
        runtime.write_text('Old seed', encoding='utf-8')
        with patch.dict('os.environ', {'DEMO_MODE': '0'}):
            sync_seed(seed, runtime)
        self.assertEqual(runtime.read_text(encoding='utf-8'), 'New seed')
        # Every HTTP request reopens the configured SQLite database.
        self.assertEqual(self.client.get('/api/workflow/settings').json(), before)

    def test_edit_disable_source_does_not_rewrite_attached_or_frozen_evidence(self):
        from content_machine.workflow.schemas import VersionPurpose
        from content_machine.workflow.versions import freeze_version, get_version
        created = self.client.post('/api/workflow/settings/sources', json={
            'kind': 'rss', 'name': 'Original feed', 'url': 'https://example.org/feed', 'enabled': True,
        }, headers={'Idempotency-Key': 'evidence-source'})
        self.assertEqual(created.status_code, 201, created.text)
        source_id = created.json()['source']['source_id']
        item = self.fixture._create_item()
        evidence = {'source_id': source_id, 'url': 'https://example.org/article', 'title': 'Article',
                    'excerpt': 'The original evidence.', 'fetched_at': '2026-11-06T12:00:00.000Z'}
        saved = self.fixture._patch(item['item_id'], {'expected_revision': 1, 'context': {'sources': [evidence]}})
        self.assertEqual(saved.status_code, 200, saved.text)
        with closing(connect(self.fixture.db_path)) as conn:
            version = freeze_version(conn, self.fixture.a, item['item_id'], 2, VersionPurpose.REVIEW)
        changed = self.client.patch(f'/api/workflow/settings/sources/{source_id}', json={
            'expected_revision': 1, 'name': 'Renamed', 'url': 'https://example.org/new-feed', 'enabled': False,
        }, headers={'Idempotency-Key': 'change-evidence-source'})
        self.assertEqual(changed.status_code, 200, changed.text)
        current = self.client.get(f"/api/workflow/items/{item['item_id']}").json()['item']
        history = self.client.get(f"/api/workflow/items/{item['item_id']}/versions").json()
        self.assertTrue(any(entry['version_id'] == version.version_id for entry in history['versions']))
        self.assertEqual(current['context']['sources'], [evidence])
        with closing(connect(self.fixture.db_path)) as conn:
            frozen = get_version(conn, self.fixture.a, version.version_id, item_id=item['item_id'])
            self.assertEqual(frozen.context.model_dump(mode='json')['sources'], [evidence])
        self.assertEqual(self.client.post('/api/workflow/discovery/refresh').json()['status'], 'no_sources')

    def test_source_update_failed_commit_rolls_back_and_retries_same_key(self):
        created = self.client.post('/api/workflow/settings/sources', json={
            'kind': 'rss', 'name': 'Original', 'url': 'https://example.org/feed', 'enabled': True,
        }, headers={'Idempotency-Key': 'update-source-create'})
        self.assertEqual(created.status_code, 201, created.text)
        original = created.json()['source']
        path = f"/api/workflow/settings/sources/{original['source_id']}"
        body = {'expected_revision': 1, 'name': 'Updated', 'enabled': False}
        headers = {'Idempotency-Key': 'source-update-retry'}
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE source_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE source_child(parent_id INTEGER REFERENCES source_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_source_update AFTER UPDATE ON workflow_sources '
                'BEGIN INSERT INTO source_child VALUES(999); END;')
            conn.commit()
        self.fixture._use_transactional_factory()
        with TestClient(app, raise_server_exceptions=False) as client:
            failure = client.patch(path, json=body, headers=headers)
        self.assertEqual(failure.status_code, 500)
        self.assertEqual(self.client.get('/api/workflow/settings').json()['sources'], [original])
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM source_child').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_idempotency WHERE request_id=?',
                                          ('source-update-retry',)).fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_source_update')
            conn.commit()
        success = self.client.patch(path, json=body, headers=headers)
        self.assertEqual(success.status_code, 200, success.text)
        self.assertEqual(success.json()['source']['revision'], 2)
        self.assertEqual(self.client.patch(path, json=body, headers=headers).json(), success.json())

    def test_preferences_are_governed_and_private_in_the_normal_application(self):
        path = '/api/workflow/preferences'
        self.assertEqual(self.client.get(path).status_code, 200)
        body = {'text': 'Explain the engineering tradeoffs.', 'consent': True}
        saved = self.client.post(path, json=body, headers={'Idempotency-Key': 'preference-one'})
        self.assertEqual(saved.status_code, 201, saved.text)
        self.assertEqual(saved.json()['preference']['status'], 'active')
        duplicate = self.client.post(path, json=body, headers={'Idempotency-Key': 'preference-duplicate'})
        self.assertEqual((duplicate.status_code, duplicate.json()['code']), (409, 'preference_conflict'))
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.get(path).json()['preferences'], [])
        self.fixture._as(self.fixture.a)
        self.assertEqual(len(self.client.get(path).json()['preferences']), 1)

    def test_discovery_is_scoped_and_reports_missing_fetcher_honestly(self):
        empty = self.client.post('/api/workflow/discovery/refresh')
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json()['status'], 'no_sources')
        source = self.client.post('/api/workflow/settings/sources', json={
            'kind': 'rss', 'name': 'Engineering feed',
            'url': 'https://example.com/feed', 'enabled': True,
        }, headers={'Idempotency-Key': 'integration-source'})
        self.assertEqual(source.status_code, 201, source.text)
        unavailable = self.client.post('/api/workflow/discovery/refresh')
        self.assertEqual(unavailable.status_code, 200, unavailable.text)
        self.assertEqual(unavailable.json()['status'], 'unavailable')
        self.assertEqual(unavailable.json()['items'], [])
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.post('/api/workflow/discovery/refresh').json()['status'], 'no_sources')

    def test_preference_commit_failure_rolls_back_and_retries_the_same_key(self):
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript(
                'CREATE TABLE pref_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE pref_child(parent_id INTEGER REFERENCES pref_parent(id)'
                ' DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER pref_fail AFTER INSERT ON workflow_preferences'
                ' BEGIN INSERT INTO pref_child VALUES(999); END;'
            )
            conn.commit()
        self.fixture._use_transactional_factory()
        body = {'text': 'Explain engineering tradeoffs with source evidence.', 'consent': True}
        headers = {'Idempotency-Key': 'failed-preference'}
        with TestClient(app, raise_server_exceptions=False) as client:
            failure = client.post('/api/workflow/preferences', json=body, headers=headers)
        self.assertEqual(failure.status_code, 500)
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_preferences').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_preference_events').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_idempotency'
                                         ' WHERE request_id=?', ('failed-preference',)).fetchone()[0], 0)
            conn.execute('DROP TRIGGER pref_fail')
            conn.commit()
        success = self.client.post('/api/workflow/preferences', json=body, headers=headers)
        self.assertEqual(success.status_code, 201, success.text)
        replay = self.client.post('/api/workflow/preferences', json=body, headers=headers)
        self.assertEqual(replay.json(), success.json())
        self.assertEqual(len(self.client.get('/api/workflow/preferences').json()['preferences']), 1)


if __name__ == '__main__':
    unittest.main()
