"""C25 normal-app HTTP checks using offline transport fixtures and real parsing."""
import os
from unittest import TestCase
from unittest.mock import Mock, patch

import test_workflow_api_items as fixtures
from content_machine.api.app import app
from content_machine.workflow import safe_rss
from test_workflow_safe_rss import RSS


FLAG = 'CONTENT_MACHINE_WORKFLOW_DISCOVERY_RSS'
MISSING = object()


class DiscoveryHttpTest(TestCase):
    def setUp(self):
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        previous = getattr(app.state, 'workflow_discovery_fetcher', MISSING)
        if previous is not MISSING:
            del app.state.workflow_discovery_fetcher
        def restore():
            if previous is MISSING:
                if hasattr(app.state, 'workflow_discovery_fetcher'):
                    del app.state.workflow_discovery_fetcher
            else:
                app.state.workflow_discovery_fetcher = previous
        self.addCleanup(restore)
        self.env = patch.dict(os.environ, {FLAG: '1'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def source(self, name='Owned feed', enabled=True):
        response = self.client.post('/api/workflow/settings/sources', json={
            'kind': 'rss', 'name': name, 'url': 'https://feed.example/rss', 'enabled': enabled,
        }, headers=self.fixture._headers())
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['source']

    def refresh(self):
        response = self.client.post('/api/workflow/discovery/refresh')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_network_requires_exact_opt_in_and_explicit_none_disables_it(self):
        self.source()
        with patch.object(safe_rss, 'fetch') as fetch:
            for value in ('', '0', 'true'):
                os.environ[FLAG] = value
                self.assertEqual(self.refresh()['status'], 'unavailable')
            os.environ[FLAG] = '1'
            app.state.workflow_discovery_fetcher = None
            self.assertEqual(self.refresh()['status'], 'unavailable')
            fetch.assert_not_called()

    def test_injected_fetcher_precedes_opt_in_and_is_still_owner_scoped(self):
        self.source()
        os.environ[FLAG] = '0'
        injected = Mock(return_value=safe_rss.RSSFetchResult(source='fixture'))
        app.state.workflow_discovery_fetcher = injected
        with patch.object(safe_rss, 'fetch') as runtime:
            self.assertEqual(self.refresh()['status'], 'empty')
            runtime.assert_not_called()
        self.assertEqual(injected.call_count, 1)

    def test_partial_title_only_empty_and_unavailable_history_on_normal_route(self):
        self.source()
        self.source('Second feed')
        title_only = safe_rss._parse_items(b'<rss><channel><item><title>Title only</title>'
            b'<link>https://site.example/title</link></item></channel></rss>', 'fixture')
        with patch.object(safe_rss, 'fetch', side_effect=[
            safe_rss.RSSFetchResult(source='fixture', items=title_only),
            RuntimeError('private failure detail'),
        ]):
            result = self.refresh()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['items'][0]['excerpt'], '')
        self.assertNotIn('private failure detail', str(result))
        with patch.object(safe_rss, 'fetch', return_value=safe_rss.RSSFetchResult(source='fixture')):
            self.assertEqual(self.refresh()['status'], 'empty')
        with patch.object(safe_rss, 'fetch', return_value=safe_rss.RSSFetchResult(source='fixture', not_modified=True)):
            unchanged = self.refresh()
        self.assertEqual(unchanged['status'], 'history_unavailable')
        self.assertFalse(unchanged['history_available'])
        self.assertEqual(unchanged['items'], [])
        self.assertEqual(self.client.get('/api/workflow/items').json()['items'], [])

    def test_normal_route_authentication_precedes_runtime_fetch(self):
        self.source()
        app.state.workflow_authenticator = lambda request: None
        with patch.object(safe_rss, 'fetch') as fetch:
            response = self.client.post('/api/workflow/discovery/refresh')
        self.assertEqual(response.status_code, 401, response.text)
        fetch.assert_not_called()

    def test_real_feed_parsing_then_explicit_attachment_never_invents_experience(self):
        owned = self.source()
        self.source('Disabled feed', enabled=False)
        self.fixture._as(self.fixture.b)
        self.source('Other creator')
        self.fixture._as(self.fixture.a)
        def offline(source):
            return safe_rss.RSSFetchResult(source=source['name'], items=safe_rss._parse_items(RSS, source['name']))
        with patch.object(safe_rss, 'fetch', side_effect=offline) as fetch:
            result = self.refresh()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual([call.args[0]['source_id'] for call in fetch.call_args_list], [owned['source_id']])
        reference = {key: value for key, value in result['items'][0].items() if key != 'source_name'}
        self.assertEqual(reference['title'], 'Engineering update')
        self.assertEqual(reference['url'], 'https://site.example/post')
        self.assertEqual(reference['excerpt'], 'Real & useful')
        self.assertRegex(reference['fetched_at'], r'^\d{4}-\d{2}-\d{2}T.*Z$')
        self.assertEqual(self.client.get('/api/workflow/items').json()['items'], [])
        item = self.fixture._create_item(title=reference['title'])
        saved = self.fixture._patch(item['item_id'], {'expected_revision': 1, 'context': {'sources': [reference]}})
        self.assertEqual(saved.status_code, 200, saved.text)
        context = saved.json()['item']['context']
        self.assertEqual(context['sources'], [reference])
        self.assertIsNone(context['experience'])
        self.assertIsNone(context['interpretation'])
        self.fixture._as(self.fixture.b)
        self.assertEqual(self.client.get('/api/workflow/items').json()['items'], [])
        self.assertEqual(self.client.get('/api/workflow/items/' + item['item_id']).status_code, 404)

