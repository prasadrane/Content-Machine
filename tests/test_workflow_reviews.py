"""Council advice is bound to the exact editorial input and never rewrites it."""
from dataclasses import replace
from pathlib import Path
import unittest

from content_machine.config import AppConfig
from content_machine.schemas import CouncilScores
from content_machine.workflow.context import EditorialSnapshot, ItemContext, ArtifactSnapshot
from content_machine.workflow.reviews import review_snapshot, validate_review_advice
from content_machine.router.base import AllRoutesFailed


class ReviewSnapshotTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = EditorialSnapshot(
            owner_id='private-owner', item_id='item', version_id='v2', revision=2,
            destination='linkedin', format='linkedin_post', title='Source-based idea',
            context=ItemContext('Actual evidence', None, None, (), None),
            artifact=ArtifactSnapshot(('  Exact draft\r\n',)), profile=None, preferences=(),
        )
        self.cfg = AppConfig()
        self.cfg.models.council = {'a': 'qwen3.8-max', 'b': 'qwen3.8-max', 'c': 'qwen3.8-flash'}

    def test_one_pass_uses_real_context_and_returns_explicit_raw_score_basis(self):
        calls = []
        class Router:
            def complete(_, models, prompt, **kwargs):
                calls.append((prompt, kwargs))
                return CouncilScores.model_validate({
                    'narrative': 8, 'velocity': 8, 'depth': 8, 'slop_purity': 8,
                    'threshold_met': False, 'verdict': 'revise', 'required_actions': ['Clarify the mechanism'],
                })
        result = review_snapshot(self.snapshot, Router(), self.cfg, 'Frozen rubric')
        self.assertEqual(len(calls), 3)
        self.assertTrue(all('Actual evidence' in prompt for prompt, _ in calls))
        self.assertTrue(all('private-owner' not in prompt for prompt, _ in calls))
        self.assertEqual(result['score_basis']['input_version_id'], 'v2')
        self.assertEqual(result['score_basis']['raw']['scale'], [0, 10])
        self.assertIsNone(result['score_basis']['normalized'])
        self.assertEqual(result['proposals'], [])
        self.assertEqual(self.snapshot.artifact.segments, ('  Exact draft\r\n',))

    def test_blank_draft_is_rejected_before_any_judge_call(self):
        class Router:
            def complete(*args, **kwargs):
                raise AssertionError('Blank input must not reach a model')
        with self.assertRaises(ValueError):
            review_snapshot(replace(self.snapshot, artifact=ArtifactSnapshot(())), Router(), self.cfg, 'rubric')

    def test_malformed_judge_output_is_validated_locally(self):
        class Router:
            def complete(*args, **kwargs):
                return CouncilScores.model_construct(
                    narrative=99, velocity=8, depth=8, slop_purity=8,
                    threshold_met=False, verdict='revise', required_actions=['Edit'],
                )
        with self.assertRaises(ValueError):
            review_snapshot(self.snapshot, Router(), self.cfg, 'rubric')

    def test_invalid_score_and_unrelated_proposals_are_rejected(self):
        score = {'narrative': 8, 'velocity': 8, 'depth': 8, 'slop_purity': 8,
                 'threshold_met': False, 'verdict': 'revise', 'required_actions': ['Clarify']}
        advice = {'actions': {'required_actions': ['Clarify'], 'notes': []},
                  'score_basis': {'input_version_id': 'v2', 'raw': {'scale': [0, 10],
                      'composite': 8, 'judges': {'a': score, 'b': score, 'c': score}}, 'normalized': None},
                  'proposals': []}
        self.assertEqual(validate_review_advice(advice, self.snapshot), advice)
        invalid = [
            {**advice, 'score_basis': {**advice['score_basis'], 'input_version_id': 'other'}},
            {**advice, 'actions': {'required_actions': 'not a list', 'notes': []}},
            {**advice, 'score_basis': {**advice['score_basis'], 'raw': {**advice['score_basis']['raw'], 'composite': 11}}},
            {**advice, 'score_basis': {**advice['score_basis'], 'raw': {**advice['score_basis']['raw'], 'judges': {'a': {**score, 'depth': float('nan')}, 'b': score, 'c': score}}}},
            {**advice, 'score_basis': {**advice['score_basis'], 'raw': {**advice['score_basis']['raw'], 'judges': {'a': score, 'b': score}}}},
            {**advice, 'proposals': [{'segment': 0, 'current': 'another text', 'proposed': 'new'}]},
            {**advice, 'proposals': [{'segment': 99, 'current': '', 'proposed': 'new'}]},
        ]
        for entry in invalid:
            with self.subTest(entry=entry), self.assertRaises(ValueError):
                validate_review_advice(entry, self.snapshot)
        with self.assertRaises(ValueError):
            validate_review_advice(advice, replace(self.snapshot, artifact=ArtifactSnapshot(())))
        thread = replace(self.snapshot, destination='x', format='x_thread')
        invalid_thread_advice = {**advice, 'proposals': [{'segment': 0,
            'current': thread.artifact.segments[0], 'proposed': 'x' * 281}]}
        with self.assertRaises(ValueError):
            validate_review_advice(invalid_thread_advice, thread)

    def test_partial_council_failure_reports_generic_note_without_provider_details(self):
        self.cfg.models.council = {'a': 'good', 'b': 'good', 'c': 'good', 'd': 'fails'}
        class Router:
            def complete(_, models, prompt, **kwargs):
                if models == ['fails']:
                    raise AllRoutesFailed([('model', 'relay', 'sensitive-provider-token')])
                return CouncilScores.model_validate({
                    'narrative': 8, 'velocity': 8, 'depth': 8, 'slop_purity': 8,
                    'threshold_met': False, 'verdict': 'revise', 'required_actions': ['Clarify'],
                })
        result = review_snapshot(self.snapshot, Router(), self.cfg, 'rubric')
        self.assertEqual(result['actions']['notes'], ['1 Council judge(s) unavailable'])
        self.assertNotIn('sensitive-provider-token', str(result))
