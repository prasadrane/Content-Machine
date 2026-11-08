"""C41 source-preservation checks with exhausted and unavailable providers."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from content_machine.interview.engine import InterviewEngine, InterviewProviderError
from content_machine.router.base import AllRoutesFailed


class WorkflowInterviewFailureTest(unittest.TestCase):
    def test_title_only_without_source_or_provider_never_becomes_fallback_success(self):
        router = Mock()
        router.complete.side_effect = AllRoutesFailed([('model', 'route', 'private-detail')])
        for provider in (None, router):
            with self.subTest(provider=provider), self.assertRaises(InterviewProviderError) as error:
                InterviewEngine(router=provider).generate_briefing('A title without an article', body=None)
            self.assertNotIn('private-detail', str(error.exception))

    def test_exhausted_synthesis_preserves_caller_notes_and_existing_transcript(self):
        notes = '  My actual notes\nwith exact spacing  '
        answers = [{'persona': 'Reviewer', 'question': 'What happened?', 'answer': '  Actual answer  '}]
        original_answers = [dict(answer) for answer in answers]
        router = Mock()
        router.complete.side_effect = AllRoutesFailed([('model', 'route', 'private-detail')])
        with tempfile.TemporaryDirectory(prefix='c41-acceptance-') as directory:
            transcript = Path(directory) / 'projects' / 'existing' / 'raw_transcript.md'
            transcript.parent.mkdir(parents=True)
            transcript.write_bytes(b'  Previously saved evidence\r\n')
            with patch.dict('os.environ', {'CONTENT_MACHINE_HOME': directory}), \
                 patch('content_machine.knowledge.provider.get_editorial_context', return_value={
                     'style_section': '', 'voice_section': '', 'rules_section': '',
                 }), self.assertRaises(InterviewProviderError):
                InterviewEngine(router=router).synthesize_draft(
                    'Real idea', 'Supplied context', answers, raw_notes=notes, spike_id='existing')
            self.assertEqual(transcript.read_bytes(), b'  Previously saved evidence\r\n')
        self.assertEqual(answers, original_answers)
        self.assertEqual(notes, '  My actual notes\nwith exact spacing  ')
