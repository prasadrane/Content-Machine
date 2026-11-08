"""Provider failures must never be represented as successful AI work."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from content_machine.humanize.transformer import HumanizeProviderError, HumanizeTransformer
from content_machine.interview.engine import InterviewEngine, InterviewProviderError

SECRET = 'provider-secret-private-diagnostic'


class EditorialFailureTest(unittest.TestCase):
    def test_briefing_failures_and_invalid_output_return_sanitized_failure(self):
        for result in [None, {}, 'bad', RuntimeError(SECRET)]:
            with self.subTest(result=result):
                router = Mock()
                if isinstance(result, Exception):
                    router.complete.side_effect = result
                else:
                    router.complete.return_value = result
                with self.assertRaises(InterviewProviderError) as raised:
                    InterviewEngine(router=router).generate_briefing('User supplied topic')
                self.assertNotIn(SECRET, str(raised.exception))
        with self.assertRaises(InterviewProviderError):
            InterviewEngine().generate_briefing('User supplied topic')

    def test_synthesis_failure_does_not_overwrite_existing_source_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'projects' / 'safe' / 'raw_transcript.md'
            target.parent.mkdir(parents=True)
            target.write_text('  existing source\n', encoding='utf-8')
            for result in [None, '', '   ', {'draft': 'unexpected'}, RuntimeError(SECRET)]:
                with self.subTest(result=result):
                    router = Mock()
                    if isinstance(result, Exception):
                        router.complete.side_effect = result
                    else:
                        router.complete.return_value = result
                    with patch.dict('os.environ', {'CONTENT_MACHINE_HOME': directory}), \
                         patch('content_machine.knowledge.provider.get_editorial_context', return_value={
                             'style_section': '', 'voice_section': '', 'rules_section': '',
                         }), self.assertRaises(InterviewProviderError) as raised:
                        InterviewEngine(router=router).synthesize_draft('Title', 'Summary', [],
                                                                       raw_notes='  source\n', spike_id='safe')
                    self.assertNotIn(SECRET, str(raised.exception))
                    self.assertEqual(target.read_text(encoding='utf-8'), '  existing source\n')

    def test_humanize_failure_never_returns_a_sanitizer_substitute(self):
        for result in [None, '', '   ', {'content': 'unexpected'}, RuntimeError(SECRET)]:
            with self.subTest(result=result):
                router = Mock()
                if isinstance(result, Exception):
                    router.complete.side_effect = result
                else:
                    router.complete.return_value = result
                with self.assertRaises(HumanizeProviderError) as raised:
                    HumanizeTransformer(router=router, voice_guide='').transform('  Exact user input\n')
                self.assertNotIn(SECRET, str(raised.exception))

    def test_genuine_humanize_result_retains_original_result_contract(self):
        router = Mock()
        router.complete.return_value = 'A supported rewrite.'
        result = HumanizeTransformer(router=router, voice_guide='').transform('Original')
        self.assertEqual(result.original_text, 'Original')
        self.assertEqual(result.humanized_text, 'A supported rewrite.')
