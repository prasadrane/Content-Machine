"""Normal-app retained-format matrix through configured offline model routing."""
import json
import unittest
from unittest.mock import Mock, patch

from content_machine.api.app import app
from content_machine.config import AppConfig
from content_machine.schemas import CouncilScores
from content_machine.workflow.format_registry import CANONICAL_PAIRS
from content_machine.workflow.schemas import Artifact, Proposal
from workflow_action_fixtures import ActionApiFixture


class FormatAcceptanceTest(ActionApiFixture, unittest.TestCase):
    def test_every_format_keeps_generation_review_approval_and_export_separate(self):
        cfg = AppConfig()
        cfg.models.council = {'a': 'judge', 'b': 'judge', 'c': 'judge'}
        model = Mock()
        with patch.dict(app.state._state, clear=False), \
             patch.dict('os.environ', {'CONTENT_MACHINE_WORKFLOW_AI': '1'}), \
             patch('content_machine.workflow.runtime.load_config', return_value=cfg), \
             patch('content_machine.workflow.runtime.make_router', return_value=model):
            app.state._state.pop('workflow_generator', None)
            app.state._state.pop('workflow_reviewer', None)
            capabilities = self.client.get('/api/workflow/capabilities').json()['pairs']
            self.assertEqual({(p['destination'], p['format']) for p in capabilities}, set(CANONICAL_PAIRS))
            self.assertTrue(all(p['can_generate'] and p['can_review'] for p in capabilities))
            for index, (destination, format_id) in enumerate(CANONICAL_PAIRS):
                with self.subTest(format=format_id):
                    created = self.fixture._post({'title': 'A grounded engineering observation',
                        'destination': destination, 'format': format_id})
                    self.assertEqual(created.status_code, 201, created.text)
                    item_id = created.json()['item']['item_id']
                    original = ['  Author supplied draft\n']
                    context = {'notes': 'Observed queue behavior in a local experiment.',
                        'interpretation': 'Backpressure is a tradeoff, not a benchmark.',
                        'experience': None, 'preference_snapshot_id': None,
                        'sources': [{'source_id': 'source', 'url': 'https://example.org/queue',
                            'title': 'Queue behavior', 'excerpt': 'A bounded queue applies backpressure.',
                            'fetched_at': '2026-11-07T12:00:00.000Z'}]}
                    saved = self.fixture._patch(item_id, {'expected_revision': 1,
                        'artifact': {'segments': original}, 'context': context})
                    self.assertEqual(saved.status_code, 200, saved.text)
                    text = ('  [Visual Cue] Explain queue behavior.\n[Camera Zoom] Backpressure. [Pause]  '
                            if format_id.endswith('_script') else '  Bounded queues apply backpressure.\n')
                    segments = [text, 'An explicit tradeoff.'] if format_id == 'x_thread' else [text]
                    def complete(models, prompt, **kwargs):
                        if kwargs['schema'] is Artifact:
                            material = json.loads(prompt.split('\n', 1)[1])
                            self.assertEqual(material['notes'], context['notes'])
                            self.assertEqual(material['sources'][0]['excerpt'], context['sources'][0]['excerpt'])
                            self.assertEqual(material['draft_segments'], original)
                            self.assertIsNone(material['experience'])
                            self.assertEqual((material['destination'], material['format']), (destination, format_id))
                            self.assertNotIn('benchmark chapter', kwargs['system'].lower())
                            self.assertIn('Never invent', kwargs['system'])
                            return {'segments': segments}
                        if kwargs['schema'] is Proposal:
                            return {'segment': 0, 'current': segments[0], 'proposed': segments[0]}
                        self.assertIn('bounded queue applies backpressure', prompt.lower())
                        return CouncilScores(narrative=8, velocity=8, depth=8, slop_purity=8,
                            threshold_met=False, verdict='revise', required_actions=['Check the tradeoff'])
                    model.complete.side_effect = complete
                    generation = self.action(item_id, 'generate', {'expected_revision': 2}, f'generate-{index}')
                    self.assertEqual(generation.status_code, 200, generation.text)
                    operation = generation.json()['operation']
                    self.assertEqual(operation['result']['artifact']['segments'], segments)
                    self.assertEqual(self._item(item_id)['artifact']['segments'], original)
                    self.assertIsNone(self._item(item_id)['active_approval_id'])
                    before_foreign = model.complete.call_count
                    self.fixture._as(self.fixture.b)
                    foreign = self.action(item_id, 'review', {'expected_revision': 2}, f'foreign-review-{index}')
                    self.assertEqual(foreign.status_code, 404, foreign.text)
                    self.assertEqual(model.complete.call_count, before_foreign)
                    self.fixture._as(self.fixture.a)
                    accepted = self.fixture._patch(item_id, {'expected_revision': 2, 'artifact': {'segments': segments}})
                    self.assertEqual(accepted.status_code, 200, accepted.text)
                    review = self.action(item_id, 'review', {'expected_revision': 3}, f'review-{index}')
                    self.assertEqual(review.status_code, 200, review.text)
                    reviewed = review.json()['operation']
                    self.assertEqual(reviewed['editorial_snapshot']['artifact']['segments'], segments)
                    self.assertEqual(reviewed['result']['review']['score_basis']['raw']['scale'], [0, 10])
                    self.assertIsNone(reviewed['result']['review']['score_basis']['normalized'])
                    self.assertIsNone(self._item(item_id)['active_approval_id'])
                    approval = self.action(item_id, 'approve', {'expected_revision': 3, 'consent': True,
                        'artifact_digest': self._digest(segments, destination, format_id)}, f'approve-{index}')
                    self.assertEqual(approval.status_code, 200, approval.text)
                    version_id = approval.json()['approval']['version_id']
                    before = model.complete.call_count
                    path = f'/api/workflow/items/{item_id}/exports/{version_id}'
                    exported = self.client.get(path)
                    self.assertEqual(exported.status_code, 200, exported.text)
                    self.assertEqual(exported.content, '\n\n'.join(segments).encode('utf-8'))
                    self.assertEqual(self.client.get(path + '?as=json').json()['segments'], segments)
                    self.assertEqual(model.complete.call_count, before)
                    linked = self.action(item_id, 'adapt', {'source_version_id': version_id,
                        'destination': 'instagram' if destination != 'instagram' else 'linkedin',
                        'format': 'instagram_caption' if destination != 'instagram' else 'linkedin_post'}, f'adapt-{index}')
                    self.assertEqual(linked.status_code, 201, linked.text)
                    self.assertIsNone(linked.json()['item']['active_approval_id'])
