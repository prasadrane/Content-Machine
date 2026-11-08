"""Legacy editorial errors stay explicit and redact provider details."""
import unittest
from unittest.mock import patch

from content_machine.interview.engine import InterviewProviderError
from content_machine.humanize.transformer import HumanizeProviderError


class EditorialFailureHttpTest(unittest.TestCase):
    def setUp(self):
        import test_workflow_api_items as fixtures
        self.fixture = fixtures.WorkflowItemsApiTest(methodName='runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_provider_failure_is_a_sanitized_503_for_each_editorial_action(self):
        cases = [
            ('/api/interview/brief', {'title': 'A real engineering topic'},
             'content_machine.api.app.InterviewEngine.generate_briefing', InterviewProviderError),
            ('/api/interview/synthesize', {'topic_title': 'A real topic', 'topic_summary': 'A summary',
             'responses': [], 'raw_notes': 'My source notes', 'spike_id': 'safe'},
             'content_machine.api.app.InterviewEngine.synthesize_draft', InterviewProviderError),
            ('/api/humanize', {'text': 'A genuine draft from the author.'},
             'content_machine.humanize.HumanizeTransformer.transform', HumanizeProviderError),
        ]
        for path, payload, target, error in cases:
            with self.subTest(path=path), patch('content_machine.api.app._make_router'), \
                 patch('content_machine.api.app._make_db'), \
                 patch(target, side_effect=error('secret-provider-detail')):
                response = self.fixture.client.post(path, json=payload)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertEqual(response.json()['code'], 'provider_unavailable')
                self.assertNotIn('secret-provider-detail', response.text)
