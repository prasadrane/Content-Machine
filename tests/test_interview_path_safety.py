"""Unsafe interview identifiers never reach model or filesystem writes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from content_machine.interview.engine import InterviewEngine


class InterviewPathSafetyTest(unittest.TestCase):
    def test_unsafe_spike_ids_fail_before_provider_or_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            router = Mock()
            with patch.dict('os.environ', {'CONTENT_MACHINE_HOME': directory}):
                for slug in ['../escape', '/absolute', '..\\escape', '.', '']:
                    with self.subTest(slug=slug), self.assertRaises(ValueError):
                        InterviewEngine(router=router).synthesize_draft('Title', 'Summary', [], spike_id=slug)
            router.complete.assert_not_called()
            self.assertEqual(list(Path(directory).rglob('raw_transcript.md')), [])

    def test_existing_valid_spike_persists_within_project_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            router = Mock()
            router.complete.return_value = 'Draft'
            with patch.dict('os.environ', {'CONTENT_MACHINE_HOME': directory}):
                result = InterviewEngine(router=router).synthesize_draft('Title', 'Summary', [], spike_id='safe-id')
            self.assertEqual(result['spike_id'], 'safe-id')
            self.assertTrue((Path(directory) / 'projects' / 'safe-id' / 'raw_transcript.md').is_file())
