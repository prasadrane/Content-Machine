"""Offline generation contract tests for every retained destination and format."""
import json
import unittest
from dataclasses import replace
from unittest.mock import Mock

from content_machine.router.base import ProviderError
from content_machine.workflow.context import (
    ActivePreference, ArtifactSnapshot, CreatorProfile, EditorialSnapshot,
    ItemContext, SourceEvidence,
)
from content_machine.workflow.format_registry import CANONICAL_PAIRS
from content_machine.workflow.schemas import Artifact
from content_machine.workflow.writing_adapters import ProposalValidationError, generate_proposal


class WritingAdapterTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = EditorialSnapshot(
            owner_id='owner-a', item_id='item-a', version_id='version-a', revision=2,
            destination='linkedin', format='linkedin_post', title='A real title',
            context=ItemContext(notes='Actual notes', experience=None, interpretation='Our interpretation',
                sources=(SourceEvidence(source_id='source-a', url='https://example.org/a', title='A title-only source',
                                        excerpt='', fetched_at='2026-11-06T12:00:00.000Z', title_only=True),),
                preference_snapshot_id=None),
            artifact=ArtifactSnapshot(segments=('Existing text',)),
            profile=CreatorProfile(name='A real author', role='', bio='', revision=2),
            preferences=(ActivePreference(preference_id='pref-a', text='Use short paragraphs', revision=1),),
        )

    def router(self, payload):
        router = Mock()
        router.complete.return_value = payload
        return router

    def test_each_pair_uses_structured_output_and_owned_context(self):
        self.assertEqual(len(CANONICAL_PAIRS), 8)
        for destination, format_id in CANONICAL_PAIRS:
            with self.subTest(pair=(destination, format_id)):
                text = '[Visual Cue] Explain. [Camera Zoom] [Pause]' if format_id.endswith('_script') else 'Grounded text'
                segments = [text, 'Second point'] if format_id == 'x_thread' else [text]
                router = self.router({'segments': segments})
                snapshot = replace(self.snapshot, destination=destination, format=format_id)
                proposal = generate_proposal(snapshot, router, ['writer-model'])
                self.assertIsInstance(proposal, Artifact)
                self.assertEqual(proposal.segments, segments)
                args, kwargs = router.complete.call_args
                self.assertEqual(args[0], ['writer-model'])
                self.assertEqual(kwargs['schema'], Artifact)
                prompt = args[1]
                self.assertIn('Actual notes', prompt)
                self.assertIn('A real title', prompt)
                self.assertIn('A title-only source', prompt)
                self.assertIn('Our interpretation', prompt)
                self.assertIn('Existing text', prompt)
                self.assertIn('Use short paragraphs', prompt)
                self.assertIn(format_id, prompt)
                self.assertNotIn('owner-a', prompt)
                self.assertIn('never invent', kwargs['system'].lower())
                self.assertIn('instructions', kwargs['system'].lower())

    def test_instagram_deliverables_have_distinct_instructions(self):
        calls = []
        for format_id, output in [('instagram_caption', 'Caption'),
                                  ('instagram_reel_script', '[Visual Cue] Script [Camera Zoom] [Pause]')]:
            router = self.router({'segments': [output]})
            generate_proposal(replace(self.snapshot, destination='instagram', format=format_id), router, ['writer'])
            calls.append(router.complete.call_args.kwargs['system'])
        self.assertIn('caption', calls[0].lower())
        self.assertIn('reel', calls[1].lower())
        self.assertNotEqual(calls[0], calls[1])

    def test_provider_error_propagates_and_no_fallback_is_returned(self):
        router = self.router(None)
        router.complete.side_effect = ProviderError('Provider unavailable')
        with self.assertRaisesRegex(ProviderError, 'Provider unavailable'):
            generate_proposal(self.snapshot, router, ['writer'])

    def test_every_pair_rejects_invalid_or_missing_structured_output(self):
        for destination, format_id in CANONICAL_PAIRS:
            for output in ({'segments': []}, {'segments': [123]}, {'segments': ['text'], 'extra': True}, 'not JSON'):
                with self.subTest(pair=(destination, format_id), output=output):
                    router = self.router(output)
                    with self.assertRaises(ProposalValidationError):
                        generate_proposal(replace(self.snapshot, destination=destination, format=format_id), router, ['writer'])

    def test_format_limits_and_script_cues_are_enforced(self):
        for destination, format_id in CANONICAL_PAIRS:
            if format_id.endswith('_script'):
                with self.subTest(format=format_id):
                    with self.assertRaises(ProposalValidationError):
                        generate_proposal(replace(self.snapshot, destination=destination, format=format_id),
                                          self.router({'segments': ['Script without cues']}), ['writer'])
        with self.assertRaises(ProposalValidationError):
            generate_proposal(replace(self.snapshot, destination='x', format='x_thread'),
                              self.router({'segments': ['a' * 281]}), ['writer'])
        with self.assertRaises(ProposalValidationError):
            generate_proposal(replace(self.snapshot, destination='instagram', format='instagram_caption'),
                              self.router({'segments': ['a' * 2201]}), ['writer'])

    def test_accepts_valid_json_and_revalidates_model_constructed_instances(self):
        result = generate_proposal(self.snapshot, self.router(json.dumps({'segments': ['Exact text']})), ['writer'])
        self.assertEqual(result.segments, ['Exact text'])
        invalid = Artifact.model_construct(segments=[1])
        with self.assertRaises(ProposalValidationError):
            generate_proposal(self.snapshot, self.router(invalid), ['writer'])

    def test_rejects_unknown_pairs_empty_models_and_non_snapshot(self):
        for snapshot, models in [(replace(self.snapshot, format='unknown'), ['writer']), (self.snapshot, []), ({}, ['writer'])]:
            router = self.router({'segments': ['text']})
            with self.assertRaises((ValueError, TypeError)):
                generate_proposal(snapshot, router, models)
            router.complete.assert_not_called()

    def test_empty_input_does_not_ask_a_model_to_invent_a_story(self):
        blank = replace(self.snapshot, title=None,
            context=ItemContext(notes='', experience=None, interpretation=None, sources=(), preference_snapshot_id=None),
            artifact=ArtifactSnapshot(segments=()))
        router = self.router({'segments': ['Invented text']})
        with self.assertRaises(ValueError):
            generate_proposal(blank, router, ['writer'])
        router.complete.assert_not_called()
