"""Normal HTTP entry-point evidence for context, preferences and author decisions."""
from contextlib import closing
import unittest
from unittest.mock import Mock, patch

from content_machine.api.app import app
from content_machine.config import AppConfig
from content_machine.schemas import CouncilScores
from content_machine.storage.db import connect
from content_machine.workflow.schemas import Proposal
from content_machine.workflow.versions import get_version
from workflow_action_fixtures import ActionApiFixture


class WorkflowBatchAcceptanceTest(ActionApiFixture, unittest.TestCase):
    def test_stopped_preferences_and_later_context_leave_approved_and_captured_work_intact(self):
        item, text = self.saved_item()
        item_id = item['item_id']
        approved = self._approve(item_id, 2, [text], 'original-approval')
        self.assertEqual(approved.status_code, 200, approved.text)
        approved_version = approved.json()['approval']['version_id']
        def save_profile(name, revision, key):
            response = self.client.put('/api/workflow/settings/profile', json={
                'name': name, 'role': '', 'bio': '', 'expected_revision': revision,
            }, headers={'Idempotency-Key': key})
            self.assertEqual(response.status_code, 200, response.text)
        save_profile('Original creator', 0, 'profile-original')
        preference = self.client.post('/api/workflow/preferences', json={
            'text': 'Use short paragraphs.', 'consent': True,
        }, headers={'Idempotency-Key': 'original-preference'})
        self.assertEqual(preference.status_code, 201, preference.text)
        cfg = AppConfig()
        cfg.models.council = {'a': 'judge', 'b': 'judge', 'c': 'judge'}
        router = Mock()
        def complete(models, prompt, **kwargs):
            if kwargs['schema'] is Proposal:
                return {'segment': 0, 'current': text, 'proposed': 'Clearer wording from the same evidence.'}
            return CouncilScores(narrative=8, velocity=8, depth=8, slop_purity=8,
                                 threshold_met=False, verdict='revise', required_actions=['Clarify'])
        router.complete.side_effect = complete
        with patch.dict(app.state._state, clear=False), \
             patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': '1'}), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', return_value=router):
            app.state._state.pop('workflow_reviewer', None)
            first = self.action(item_id, 'review', {'expected_revision': 2}, 'review-original')
            self.assertEqual(first.status_code, 200, first.text)
            original_operation = first.json()['operation']
            self.assertEqual(len(original_operation['result']['review']['proposals']), 1)
            self.assertEqual(self._item(item_id)['artifact']['segments'], [text])
            stopped = self.client.post(f"/api/workflow/preferences/{preference.json()['preference']['preference_id']}/stop",
                json={'expected_revision': 1}, headers={'Idempotency-Key': 'stop-preference'})
            self.assertEqual(stopped.status_code, 200, stopped.text)
            save_profile('Updated creator', 1, 'profile-updated')
            second = self.action(item_id, 'review', {'expected_revision': 2}, 'review-updated')
            self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(original_operation['editorial_snapshot']['profile']['name'], 'Original creator')
        self.assertEqual(len(original_operation['editorial_snapshot']['preferences']), 1)
        self.assertEqual(second.json()['operation']['editorial_snapshot']['profile']['name'], 'Updated creator')
        self.assertEqual(second.json()['operation']['editorial_snapshot']['preferences'], [])
        stored = self.client.get(f"/api/workflow/items/{item_id}/operations/{original_operation['operation_id']}")
        self.assertEqual(stored.json()['operation'], original_operation)
        self.assertEqual(self._item(item_id)['active_approval_id'], approved.json()['approval']['approval_id'])
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(get_version(conn, self.fixture.a, approved_version, item_id=item_id).artifact.segments, [text])
        # Acceptance is a separate, explicit save and creates an unapproved revision.
        proposal = original_operation['result']['review']['proposals'][0]
        accepted = self.fixture._patch(item_id, {'expected_revision': 2,
            'artifact': {'segments': [proposal['proposed']]}, 'stage': 'draft_review'})
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()['item']['working_revision'], 3)
        self.assertIsNone(accepted.json()['item']['active_approval_id'])
        with closing(connect(self.fixture.db_path)) as conn:
            self.assertEqual(get_version(conn, self.fixture.a, approved_version, item_id=item_id).artifact.segments, [text])

    def test_reading_approved_export_does_not_construct_or_call_a_model_router(self):
        item, text = self.saved_item()
        approved = self._approve(item['item_id'], 2, [text], 'approve-export')
        self.assertEqual(approved.status_code, 200, approved.text)
        version_id = approved.json()['approval']['version_id']
        with patch('content_machine.api.app._make_router') as legacy_router, \
             patch('content_machine.workflow.runtime.make_router') as workflow_router:
            response = self.client.get(f"/api/workflow/items/{item['item_id']}/exports/{version_id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.content, text.encode('utf-8'))
        legacy_router.assert_not_called()
        workflow_router.assert_not_called()
