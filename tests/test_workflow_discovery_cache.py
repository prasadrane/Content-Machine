"""Durable owner/source-scoped conditional RSS retrieval through the real app."""
from contextlib import closing
from unittest import TestCase
from unittest.mock import patch

from content_machine.api.app import app
from content_machine.storage.db import connect
from content_machine.workflow import safe_rss
import test_workflow_discovery_http as http_fixtures
from test_workflow_safe_rss import FakeContext, FakeSocket, RSS, addresses, reply


class DiscoveryCacheHttpTest(TestCase):
    # Reuse setup helpers without collecting another copy of the HTTP tests.
    setUp = http_fixtures.DiscoveryHttpTest.setUp
    source = http_fixtures.DiscoveryHttpTest.source
    refresh = http_fixtures.DiscoveryHttpTest.refresh

    def transport(self, payload=RSS, status='200 OK', headers=None):
        sock = FakeSocket(reply(payload, status, headers))
        def fixture_fetch(source):
            with patch.object(safe_rss.socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
                 patch.object(safe_rss.socket, 'socket', return_value=sock), \
                 patch.object(safe_rss.ssl, 'create_default_context', return_value=FakeContext()):
                return safe_rss._fetch_in_process(source)
        with patch.object(safe_rss, 'fetch', side_effect=fixture_fetch):
            result = self.refresh()
        return result, sock

    def cache_rows(self):
        with closing(connect(self.fixture.db_path)) as conn:
            return [dict(row) for row in conn.execute('SELECT * FROM workflow_discovery_cache')]

    def test_persisted_validators_reach_next_request_but_never_settings_or_experience(self):
        source = self.source()
        before = self.client.get('/api/workflow/settings').json()
        first, sock = self.transport(headers={'ETag': '"owner-a"',
            'Last-Modified': 'Fri, 06 Nov 2026 12:00:00 GMT'})
        self.assertEqual(first['status'], 'ok')
        self.assertNotIn(b'If-None-Match', sock.sent)
        second, sock = self.transport(b'', '304 Not Modified')
        self.assertIn(b'If-None-Match: "owner-a"', sock.sent)
        self.assertIn(b'If-Modified-Since: Fri, 06 Nov 2026 12:00:00 GMT', sock.sent)
        self.assertEqual(second['status'], 'history_unavailable')
        self.assertEqual(second['items'], [])
        self.assertFalse(second['history_available'])
        rows = self.cache_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['owner_id'], rows[0]['source_id']), (self.fixture.a.owner_id, source['source_id']))
        self.assertEqual(self.client.get('/api/workflow/settings').json(), before)
        self.assertEqual(self.client.get('/api/workflow/items').json()['items'], [])

    def test_owner_source_and_url_changes_never_reuse_other_validators(self):
        a = self.source()
        self.transport(headers={'ETag': '"a"'})
        self.fixture._as(self.fixture.b)
        self.source('B same URL')
        _, sock = self.transport(headers={'ETag': '"b"'})
        self.assertNotIn(b'If-None-Match', sock.sent)
        self.fixture._as(self.fixture.a)
        _, sock = self.transport(b'', '304 Not Modified')
        self.assertIn(b'If-None-Match: "a"', sock.sent)
        changed = self.client.patch('/api/workflow/settings/sources/' + a['source_id'], json={
            'expected_revision': 1, 'url': 'https://new.example/rss',
        }, headers=self.fixture._headers())
        self.assertEqual(changed.status_code, 200, changed.text)
        _, sock = self.transport(headers={'ETag': '"new"'})
        self.assertNotIn(b'If-None-Match', sock.sent)
        rows = self.cache_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['etag'] for row in rows}, {'"new"', '"b"'})

    def test_only_bounded_etag_and_http_date_fields_are_persisted(self):
        self.source()
        self.transport(headers={'ETag': 'Bearer credential-value', 'Last-Modified': 'not a date',
            'Set-Cookie': 'session=private'})
        self.assertEqual(self.cache_rows(), [])
        self.transport(headers={'ETag': '"' + 'x' * 600 + '"', 'Last-Modified': 'not a date'})
        self.assertEqual(self.cache_rows(), [])

    def test_same_owner_sources_with_same_url_have_independent_validators(self):
        first = self.source('One')
        second = self.source('Two')
        expected = {first['source_id']: '"one"', second['source_id']: '"two"'}
        def fixture_fetch(source):
            return safe_rss.RSSFetchResult(source=source['name'], cache_url=source['url'],
                                          etag=expected[source['source_id']])
        with patch.object(safe_rss, 'fetch', side_effect=fixture_fetch):
            self.refresh()
        with patch.object(safe_rss, 'fetch', side_effect=fixture_fetch) as fetch:
            self.refresh()
        actual = {call.args[0]['source_id']: call.args[0]['cache']['etag'] for call in fetch.call_args_list}
        self.assertEqual(actual, expected)

    def test_success_without_validators_clears_stale_conditional_metadata(self):
        self.source()
        self.transport(headers={'ETag': '"before"'})
        self.assertEqual(len(self.cache_rows()), 1)
        self.transport()
        self.assertEqual(self.cache_rows(), [])
        _, sock = self.transport()
        self.assertNotIn(b'If-None-Match', sock.sent)

    def test_missing_cache_table_does_not_hide_valid_feed_results(self):
        self.source()
        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute('DROP TABLE workflow_discovery_cache')
            conn.commit()
        # Production connect normally migrates. Simulate an unavailable cache
        # without recreating the table while retaining the actual item tables.
        app.state.workflow_connection_factory = lambda: connect(self.fixture.db_path, init=False)
        result, _ = self.transport(headers={'ETag': '"fresh"'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['cache_warnings'])

    def test_cache_write_failure_preserves_valid_retrieval_and_rolls_back(self):
        self.source()
        with closing(connect(self.fixture.db_path)) as conn:
            conn.execute("CREATE TRIGGER fail_discovery_cache BEFORE INSERT ON workflow_discovery_cache "
                         "BEGIN SELECT RAISE(ABORT, 'cache unavailable'); END")
            conn.commit()
        result, _ = self.transport(headers={'ETag': '"fresh"'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['items'][0]['title'], 'Engineering update')
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['cache_warnings'])
        self.assertEqual(self.cache_rows(), [])

    def test_deferred_commit_failure_does_not_claim_retrieval_failed(self):
        self.source()
        with closing(connect(self.fixture.db_path)) as conn:
            conn.executescript('CREATE TABLE cache_parent(id INTEGER PRIMARY KEY);'
                'CREATE TABLE cache_child(parent_id INTEGER REFERENCES cache_parent(id) DEFERRABLE INITIALLY DEFERRED);'
                'CREATE TRIGGER fail_cache_commit AFTER INSERT ON workflow_discovery_cache '
                'BEGIN INSERT INTO cache_child VALUES(999); END;')
            conn.commit()
        self.fixture._use_transactional_factory()
        result, _ = self.transport(headers={'ETag': '"fresh"'})
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['errors'], [])
        self.assertTrue(result['cache_warnings'])
        self.assertEqual(self.cache_rows(), [])
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM cache_child').fetchone()[0], 0)
