"""C40 acceptance through legacy and owned workflow HTTP entry points."""
import unittest
from unittest.mock import Mock, patch

from content_machine.api.app import app
from content_machine.router.base import AllRoutesFailed
from workflow_action_fixtures import ActionApiFixture


class WorkflowFailureRoutesTest(ActionApiFixture, unittest.TestCase):
    def test_demo_provider_failures_never_substitute_sample_results(self):
        failure = AllRoutesFailed([('fixture-model', 'fixture-route', 'private-quota-diagnostic')])
        with patch.dict('os.environ', {'DEMO_MODE': '1'}), \
             patch('content_machine.api.app._make_router'), \
             patch('content_machine.api.app._make_db'), \
             patch('content_machine.api.app.run_council', side_effect=failure), \
             patch('content_machine.api.app.DistributionEngine.generate_all', side_effect=failure) as adapt, \
             patch('content_machine.demo_seed.replay_council') as replay_review, \
             patch('content_machine.demo_seed.replay_bundle') as replay_bundle:
            review = self.client.post('/api/council/run', json={
                'draft': '  Actual draft\n', 'spike_id': 'actual-request',
            })
            distribution = self.client.post('/api/distribute/run', json={
                'anchor_post': '  An actual approved anchor post\n', 'project_slug': 'actual-request',
            })
        self.assertEqual(review.status_code, 503, review.text)
        self.assertEqual(distribution.status_code, 502, distribution.text)
        for response in (review, distribution):
            self.assertIsInstance(response.json()['detail'], str)
            self.assertNotIn('replayed', response.json())
            self.assertNotIn('private-quota-diagnostic', response.text)
        self.assertEqual(adapt.call_args.args[0], '  An actual approved anchor post\n')
        replay_review.assert_not_called()
        replay_bundle.assert_not_called()

    def test_failed_review_retains_exact_approved_work_and_request_identity(self):
        item, text = self.saved_item()
        item_id = item['item_id']
        approved = self._approve(item_id, 2, [text], 'prior-human-approval')
        self.assertEqual(approved.status_code, 200, approved.text)
        before = self.client.get(f'/api/workflow/items/{item_id}').json()
        before_counts = self._counts()
        reviewer = Mock(side_effect=AllRoutesFailed([('model', 'route', 'private-provider-detail')]))
        body = {'expected_revision': 2}
        with patch.object(app.state, 'workflow_reviewer', reviewer, create=True):
            response = self.action(item_id, 'review', body, 'failed-review-request')
            retry = self.action(item_id, 'review', body, 'failed-review-request')
        self.assertEqual(response.status_code, 502, response.text)
        self.assertEqual(retry.json(), response.json())
        operation = response.json()['operation']
        self.assertEqual(operation['state'], 'failed')
        self.assertEqual(operation['request_id'], 'failed-review-request')
        self.assertEqual(operation['item_id'], item_id)
        self.assertEqual(operation['editorial_snapshot']['artifact']['segments'], [text])
        self.assertNotIn('private-provider-detail', response.text)
        reviewer.assert_called_once()
        self.assertEqual(self.client.get(f'/api/workflow/items/{item_id}').json(), before)
        counts = self._counts()
        self.assertEqual(counts['workflow_reviews'], before_counts['workflow_reviews'])
        self.assertEqual(counts['workflow_approvals'], before_counts['workflow_approvals'])
        version_id = approved.json()['approval']['version_id']
        exported = self.client.get(f'/api/workflow/items/{item_id}/exports/{version_id}?as=json')
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(exported.json()['segments'], [text])
