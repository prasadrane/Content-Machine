"""Wording proposals remain grounded, version-bound and optional advice."""
from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from content_machine.config import AppConfig
from content_machine.schemas import CouncilScores
from content_machine.workflow.context import ArtifactSnapshot, EditorialSnapshot, ItemContext
from content_machine.workflow.schemas import Proposal
from content_machine.workflow.writing_adapters import suggest_wording
from content_machine.workflow import runtime


class WordingProposalTest(unittest.TestCase):
    def test_local_cleanup_is_labeled_and_never_reported_as_model_rewrite(self):
        from content_machine.workflow.writing_adapters import cleanup_wording
        snapshot = replace(self.snapshot, artifact=ArtifactSnapshot(('We should utilize bounded queues.',)))
        suggestions = cleanup_wording(snapshot)
        self.assertEqual(suggestions[0]['current'], snapshot.artifact.segments[0])
        self.assertEqual(suggestions[0]['provenance'], 'deterministic_cleanup')
        self.assertNotEqual(suggestions[0]['proposed'], suggestions[0]['current'])
        self.assertEqual(snapshot.artifact.segments, ('We should utilize bounded queues.',))

    def test_runtime_records_local_fallback_against_original_reviewed_version(self):
        snapshot = replace(self.snapshot, artifact=ArtifactSnapshot(('We should utilize queues.',)))
        cfg = AppConfig()
        cfg.models.council = {'a': 'judge', 'b': 'judge', 'c': 'judge'}
        model = Mock()
        def complete(models, prompt, **kwargs):
            if kwargs['schema'] is Proposal:
                raise RuntimeError('private-diagnostic')
            return CouncilScores(narrative=8, velocity=8, depth=8, slop_purity=8,
                threshold_met=False, verdict='revise', required_actions=['Check the tradeoff'])
        model.complete.side_effect = complete
        with patch.object(runtime, 'load_config', return_value=cfg), patch.object(runtime, 'make_router', return_value=model):
            advice = runtime.review(snapshot)
        self.assertEqual(advice['proposals'][0]['provenance'], 'deterministic_cleanup')
        self.assertEqual(advice['proposals'][0]['current'], snapshot.artifact.segments[0])
        self.assertEqual(advice['score_basis']['input_version_id'], snapshot.version_id)
        self.assertTrue(any('Local cleanup' in note for note in advice['actions']['notes']))
        self.assertNotIn('private-diagnostic', str(advice))

    def setUp(self):
        self.snapshot = EditorialSnapshot('private-owner', 'private-item', 'version', 2,
            'linkedin', 'linkedin_post', ItemContext('Actual engineering notes', None, None, (), None),
            ArtifactSnapshot(('  Exact draft\n',)), None, (), title='Engineering idea')

    def test_one_proposal_preserves_exact_input_and_excludes_internal_identity(self):
        router = Mock()
        router.complete.return_value = {'segment': 0, 'current': '  Exact draft\n', 'proposed': 'Clearer draft'}
        result = suggest_wording(self.snapshot, router, ['writer'])
        self.assertEqual(result, [{'segment': 0, 'current': '  Exact draft\n', 'proposed': 'Clearer draft', 'provenance': 'model_rewrite'}])
        self.assertEqual(self.snapshot.artifact.segments, ('  Exact draft\n',))
        args, kwargs = router.complete.call_args
        self.assertIn('Actual engineering notes', args[1])
        self.assertNotIn('private-owner', args[1])
        self.assertNotIn('private-item', args[1])
        self.assertIs(kwargs['schema'], Proposal)
        self.assertIn('Never invent', kwargs['system'])

    def test_invalid_target_blank_and_overlong_changes_are_rejected(self):
        for segment, current, proposed in [(-1, '  Exact draft\n', 'Edit'), (9, '  Exact draft\n', 'Edit'), (0, 'Other draft', 'Edit'),
                                           (0, '  Exact draft\n', '   ')]:
            with self.subTest(segment=segment, proposed=proposed):
                router = Mock()
                router.complete.return_value = {'segment': segment, 'current': current, 'proposed': proposed}
                with self.assertRaises(ValueError):
                    suggest_wording(self.snapshot, router, ['writer'])
        thread = replace(self.snapshot, destination='x', format='x_thread')
        router.complete.return_value = {'segment': 0, 'current': '  Exact draft\n', 'proposed': 'x' * 281}
        with self.assertRaises(ValueError):
            suggest_wording(thread, router, ['writer'])

    def test_unchanged_wording_returns_no_proposal(self):
        router = Mock()
        router.complete.return_value = {'segment': 0, 'current': '  Exact draft\n', 'proposed': '  Exact draft\n'}
        self.assertEqual(suggest_wording(self.snapshot, router, ['writer']), [])

    def test_runtime_review_keeps_advice_when_wording_provider_fails(self):
        cfg = AppConfig()
        cfg.models.council = {'a': 'judge', 'b': 'judge', 'c': 'judge'}
        router = Mock()
        def complete(models, prompt, **kwargs):
            if kwargs['schema'] is Proposal:
                raise RuntimeError('private-provider-diagnostic')
            return CouncilScores(narrative=8, velocity=8, depth=8, slop_purity=8,
                                 threshold_met=False, verdict='revise', required_actions=['Clarify'])
        router.complete.side_effect = complete
        with patch.object(runtime, 'load_config', return_value=cfg), \
             patch.object(runtime, 'make_router', return_value=router):
            result = runtime.review(self.snapshot)
        self.assertEqual(result['proposals'], [])
        self.assertEqual(result['actions']['required_actions'], ['[a] Clarify'])
        self.assertTrue(any('Wording suggestion unavailable' in note for note in result['actions']['notes']))
        self.assertNotIn('private-provider-diagnostic', str(result))
