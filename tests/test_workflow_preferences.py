"""Creator preferences remain governed, private and transactionally durable."""
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from content_machine.storage.db import connect
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.http import workflow_error_response
from content_machine.workflow.preference_routes import router
from content_machine.workflow.preferences import import_legacy, migrate_preferences, mutate_preference, propose_preference
from content_machine.workflow.schemas import Principal
from content_machine.workflow.schemas import ItemCreate, VersionPurpose
from content_machine.workflow.items import create_item
from content_machine.workflow.versions import freeze_version


class PreferencesApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='preference-tests-')
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / 'test.db'
        with closing(connect(self.db_path)) as conn:
            migrate_preferences(conn)
            conn.commit()
        self.owner = Principal(owner_id='owner-A', mode='hosted_verified')
        self.other = Principal(owner_id='owner-B', mode='hosted_verified')
        app = FastAPI()
        app.add_exception_handler(WorkflowError, lambda request, exc: workflow_error_response(exc))
        app.include_router(router, prefix='/api/workflow')
        app.dependency_overrides[resolve_principal] = lambda: self.owner

        def connection(request: Request):
            conn = connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()
        from content_machine.workflow.http import get_workflow_connection
        app.dependency_overrides[get_workflow_connection] = connection
        self.client = TestClient(app)

    def post(self, path, body, key='key'):
        return self.client.post('/api/workflow/preferences' + path, json=body,
                                headers={'Idempotency-Key': key})

    def patch_preference(self, preference_id, body, key='key'):
        return self.client.patch(f'/api/workflow/preferences/{preference_id}', json=body,
                                 headers={'Idempotency-Key': key})

    def create(self, text='Prefer concrete examples.', key='create'):
        response = self.post('', {'text': text, 'consent': True}, key)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['preference']

    def listing(self):
        response = self.client.get('/api/workflow/preferences')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['preferences']

    def test_empty_manual_activation_and_owner_isolation(self):
        self.assertEqual(self.listing(), [])
        created = self.create('  Use concrete examples.  ')
        self.assertEqual(created['text'], '  Use concrete examples.  ')
        self.assertEqual(created['status'], 'active')
        self.assertEqual(created['origin'], 'manual')
        self.assertEqual(created['revision'], 1)
        self.assertEqual(len(self.listing()), 1)
        self.owner, self.other = self.other, self.owner
        self.assertEqual(self.listing(), [])
        response = self.post(f"/{created['preference_id']}/stop", {'expected_revision': 1}, 'foreign')
        self.assertEqual(response.status_code, 404)
        history = self.client.get(f"/api/workflow/preferences/{created['preference_id']}/history")
        self.assertEqual(history.status_code, 404)
        self.assertEqual(self.listing(), [])
        self.owner, self.other = self.other, self.owner
        self.assertEqual(self.listing()[0]['status'], 'active')

    def test_consent_duplicate_conflict_and_cap_never_report_activation(self):
        denied = self.post('', {'text': 'Use examples.', 'consent': False}, 'denied')
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(self.listing(), [])
        first = self.create('Use concrete examples.')
        duplicate = self.post('', {'text': 'Use concrete examples.', 'consent': True}, 'duplicate')
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()['code'], 'preference_conflict')
        self.assertEqual(duplicate.json()['conflict_preference_id'], first['preference_id'])
        with patch('content_machine.workflow.preferences.DEFAULT_CAP', 1):
            limited = self.post('', {'text': 'Avoid unsupported numerical claims.', 'consent': True}, 'limited')
        self.assertEqual(limited.status_code, 409)
        self.assertEqual(limited.json()['code'], 'preference_limit')
        self.assertEqual(len(self.listing()), 1)
        self.owner, self.other = self.other, self.owner
        with patch('content_machine.workflow.preferences.DEFAULT_CAP', 1):
            self.create('Another creator has a separate preference.', 'owner-B-create')
        self.assertEqual(len(self.listing()), 1)

    def test_edit_stop_and_history_use_revision_checks(self):
        first = self.create()
        preference_id = first['preference_id']
        changed = self.patch_preference(preference_id,
            {'text': '  Use examples grounded in observations.\n', 'expected_revision': 1, 'consent': True}, 'edit')
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()['preference']['revision'], 2)
        stale = self.post(f'/{preference_id}/stop', {'expected_revision': 1}, 'stale')
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()['code'], 'revision_conflict')
        stopped = self.post(f'/{preference_id}/stop', {'expected_revision': 2}, 'stop')
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()['preference']['status'], 'stopped')
        history = self.client.get(f'/api/workflow/preferences/{preference_id}/history')
        self.assertEqual(history.status_code, 200)
        self.assertEqual([e['status'] for e in history.json()['events']], ['active', 'active', 'stopped'])
        self.assertEqual(history.json()['events'][1]['text'], '  Use examples grounded in observations.\n')

    def test_idempotent_retries_replay_and_changed_request_conflicts(self):
        body = {'text': 'Prefer compact paragraphs.', 'consent': True}
        original = self.post('', body, 'stable')
        replay = self.post('', body, 'stable')
        self.assertEqual(original.status_code, 201)
        self.assertEqual((replay.status_code, replay.json()), (201, original.json()))
        changed = self.post('', {'text': 'Another rule.', 'consent': True}, 'stable')
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.json()['code'], 'idempotency_conflict')
        self.assertEqual(len(self.listing()), 1)
        missing = self.client.post('/api/workflow/preferences', json=body)
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.json()['code'], 'invalid_request')

    def test_proposals_remain_pending_and_cannot_bypass_conflict_on_activation(self):
        first = self.create('Prefer compact paragraphs.')
        with closing(connect(self.db_path)) as conn:
            created = create_item(conn, self.owner,
                ItemCreate(title='Source', destination='linkedin', format='linkedin_post'), request_id='source')
            source_id = created.body['item']['item_id']
            version = freeze_version(conn, self.owner, source_id, 1, VersionPurpose.REVIEW)
            suggestion = propose_preference(conn, self.owner, 'Prefer compact paragraphs.',
                                            origin='item', origin_ref=version.version_id, request_id='proposal')
            replay = propose_preference(conn, self.owner, 'Prefer compact paragraphs.',
                                        origin='item', origin_ref=version.version_id, request_id='proposal')
            self.assertEqual(replay, suggestion)
            self.assertEqual(suggestion['conflict_preference_id'], first['preference_id'])
            with self.assertRaises(WorkflowError):
                propose_preference(conn, self.owner, 'Another suggestion.', origin='item',
                                   origin_ref=version.version_id, request_id='proposal')
            with patch('content_machine.workflow.preferences.DEFAULT_CAP', 1):
                with self.assertRaises(WorkflowError) as blocked:
                    propose_preference(conn, self.owner, 'Avoid made-up numbers.', origin='item',
                                       origin_ref=version.version_id, request_id='at-cap')
            self.assertEqual(blocked.exception.code, 'preference_limit')
            with self.assertRaises(WorkflowError) as foreign:
                propose_preference(conn, self.other, 'A private draft preference.', origin='item',
                                   origin_ref=version.version_id, request_id='foreign-proposal')
            self.assertEqual(foreign.exception.status_code, 404)
        self.assertEqual(suggestion['status'], 'pending')
        preference_id = suggestion['preference_id']
        denied = self.post(f'/{preference_id}/activate', {'expected_revision': 1, 'consent': True}, 'activate')
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(denied.json()['code'], 'preference_conflict')
        self.assertEqual([p['status'] for p in self.listing()].count('active'), 1)
        rejected = self.post(f'/{preference_id}/reject', {'expected_revision': 1}, 'reject')
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()['preference']['status'], 'rejected')

    def test_concurrent_activation_obeys_the_owner_cap(self):
        barrier = threading.Barrier(2)
        def create_concurrently(index):
            with closing(connect(self.db_path, init=False)) as conn:
                barrier.wait(timeout=5)
                try:
                    result = mutate_preference(conn, self.owner, 'create', None,
                        {'text': ['Use concise examples.', 'Avoid ungrounded numbers.'][index], 'consent': True},
                        f'concurrent-{index}')
                    return result.status_code
                except WorkflowError as error:
                    return error.status_code
        with patch('content_machine.workflow.preferences.DEFAULT_CAP', 1), ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(create_concurrently, [0, 1]))
        self.assertEqual(sorted(outcomes), [201, 409])
        self.assertEqual(len(self.listing()), 1)

    def test_conflict_checker_failure_cannot_activate_a_preference(self):
        with patch('content_machine.workflow.preferences.DefaultEmbedder.encode', side_effect=RuntimeError('offline')):
            response = self.post('', {'text': 'Use factual examples.', 'consent': True}, 'check-failed')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'preference_check_unavailable')
        self.assertEqual(self.listing(), [])

    def test_failed_write_rolls_back_history_and_retry_key(self):
        with closing(connect(self.db_path)) as conn:
            conn.execute("CREATE TRIGGER fail_preference_event BEFORE INSERT ON workflow_preference_events"
                         " BEGIN SELECT RAISE(ABORT, 'forced test failure'); END")
            conn.commit()
        with TestClient(self.client.app, raise_server_exceptions=False) as client:
            result = client.post('/api/workflow/preferences',
                json={'text': 'Use factual examples.', 'consent': True},
                headers={'Idempotency-Key': 'retry-after-failure'})
        self.assertEqual(result.status_code, 500)
        with closing(connect(self.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_preferences').fetchone()[0], 0)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM workflow_idempotency').fetchone()[0], 0)
            conn.execute('DROP TRIGGER fail_preference_event')
            conn.commit()
        result = self.post('', {'text': 'Use factual examples.', 'consent': True}, 'retry-after-failure')
        self.assertEqual(result.status_code, 201)

    def test_local_legacy_mapping_is_explicit_recoverable_and_repeatable(self):
        first = self.create('Legacy rule')
        with closing(connect(self.db_path)) as conn:
            conn.execute("INSERT INTO lessons(rule_text, status) VALUES ('Legacy rule', 'active')")
            legacy_id = conn.execute('SELECT id FROM lessons').fetchone()[0]
            conn.commit()
            local = Principal(owner_id='owner-A', mode='trusted_local')
            result = import_legacy(conn, local, [legacy_id])
            again = import_legacy(conn, local, [legacy_id])
            self.assertEqual(result, again)
            self.assertEqual(result[0]['status'], 'pending')
            self.assertEqual(result[0]['origin'], 'legacy')
            self.assertEqual(result[0]['conflict_preference_id'], first['preference_id'])
            self.assertEqual(conn.execute('SELECT rule_text FROM lessons').fetchone()[0], 'Legacy rule')
            with self.assertRaises(WorkflowError):
                import_legacy(conn, self.other, [legacy_id])
            other_local = Principal(owner_id='owner-B', mode='trusted_local')
            with self.assertRaises(WorkflowError) as mapped:
                import_legacy(conn, other_local, [legacy_id])
            self.assertEqual(mapped.exception.code, 'legacy_already_mapped')
        self.assertEqual(len(self.listing()), 2)


if __name__ == '__main__':
    unittest.main()
