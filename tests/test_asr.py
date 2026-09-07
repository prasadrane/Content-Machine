"""Tests for ASR dual-path subsystem (plan v2 §3.1, CPU-only).

BatchTranscriber wraps faster-whisper CLI.
LiveMonitor wraps whisper.cpp streaming.

All tests are offline — subprocess calls are mocked.
Set CONTENT_MACHINE_LIVE=1 to exercise real binaries (requires installation).
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ---------------------------------------------------------------------------
# Transcript dataclass tests
# ---------------------------------------------------------------------------

class TestTranscript(unittest.TestCase):

    def test_transcript_has_text_and_word_count(self):
        """Transcript exposes the full text and a word count."""
        from content_machine.asr.transcript import Transcript
        t = Transcript(text="Hello world how are you", model="faster-whisper/small",
                       audio_path="/tmp/a.wav", duration_s=5.0)
        self.assertEqual(t.word_count, 5)
        self.assertIn("Hello", t.text)

    def test_transcript_word_count_strips_punctuation_lines(self):
        """Word count ignores leading/trailing whitespace and newlines."""
        from content_machine.asr.transcript import Transcript
        t = Transcript(text="  one two\nthree  ", model="m", audio_path="/a.wav", duration_s=1.0)
        self.assertEqual(t.word_count, 3)

    def test_transcript_save_writes_markdown(self):
        """Transcript.save() writes a Markdown file with header + body."""
        from content_machine.asr.transcript import Transcript
        t = Transcript(text="Test body text.", model="faster-whisper/small",
                       audio_path="/a.wav", duration_s=3.0)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "transcript.md"
            t.save(out)
            content = out.read_text(encoding="utf-8")
        self.assertIn("Test body text.", content)
        self.assertIn("faster-whisper/small", content)

    def test_transcript_meets_minimum_target(self):
        """Transcript.meets_minimum() checks word count >= threshold."""
        from content_machine.asr.transcript import Transcript
        short = Transcript(text="only five words here now", model="m", audio_path="/a", duration_s=1.0)
        long_ = Transcript(text=" ".join(["word"] * 800), model="m", audio_path="/a", duration_s=60.0)
        self.assertFalse(short.meets_minimum(min_words=800))
        self.assertTrue(long_.meets_minimum(min_words=800))


# ---------------------------------------------------------------------------
# BatchTranscriber tests
# ---------------------------------------------------------------------------

FAKE_WHISPER_OUTPUT = """\
[00:00.000 --> 00:03.000]  Hello, this is a test transcript.
[00:03.000 --> 00:06.000]  It has multiple segments for testing.
"""

class TestBatchTranscriber(unittest.TestCase):

    def _make_transcriber(self, model: str = "small"):
        from content_machine.asr.batch import BatchTranscriber
        return BatchTranscriber(model=model)

    def test_transcribe_returns_transcript_object(self):
        """transcribe() returns a Transcript with non-empty text."""
        t = self._make_transcriber()
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=FAKE_WHISPER_OUTPUT, stderr=""
            )
            result = t.transcribe("/tmp/audio.wav")
        from content_machine.asr.transcript import Transcript
        self.assertIsInstance(result, Transcript)
        self.assertIn("Hello", result.text)

    def test_transcribe_strips_timestamp_markers(self):
        """Text output has timestamp markers stripped (plain prose only)."""
        t = self._make_transcriber()
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=FAKE_WHISPER_OUTPUT, stderr=""
            )
            result = t.transcribe("/tmp/audio.wav")
        self.assertNotIn("-->", result.text)
        self.assertNotIn("[00:", result.text)

    def test_transcribe_uses_correct_model_flag(self):
        """faster-whisper is called with --model matching constructor arg."""
        t = self._make_transcriber(model="base")
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            t.transcribe("/tmp/audio.wav")
        args = mock_run.call_args[0][0]
        self.assertIn("--model", args)
        model_idx = args.index("--model")
        self.assertEqual(args[model_idx + 1], "base")

    def test_transcribe_uses_int8_compute_type(self):
        """CPU-only mode: faster-whisper is called with --compute_type int8."""
        t = self._make_transcriber()
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            t.transcribe("/tmp/audio.wav")
        args = mock_run.call_args[0][0]
        self.assertIn("int8", " ".join(args))

    def test_transcribe_raises_on_nonzero_exit(self):
        """RuntimeError raised when faster-whisper exits with non-zero code."""
        t = self._make_transcriber()
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="model not found"
            )
            with self.assertRaises(RuntimeError):
                t.transcribe("/tmp/audio.wav")

    def test_transcribe_records_audio_path_in_transcript(self):
        """Transcript.audio_path matches the file passed to transcribe()."""
        t = self._make_transcriber()
        with patch("content_machine.asr.batch.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello world", stderr="")
            result = t.transcribe("/my/recording.wav")
        self.assertEqual(result.audio_path, "/my/recording.wav")


# ---------------------------------------------------------------------------
# LiveMonitor tests
# ---------------------------------------------------------------------------

class TestLiveMonitor(unittest.TestCase):

    def _make_monitor(self, model: str = "base"):
        from content_machine.asr.live import LiveMonitor
        return LiveMonitor(model=model)

    def test_monitor_calls_callback_with_text_chunks(self):
        """LiveMonitor invokes the callback once per line of whisper.cpp output."""
        monitor = self._make_monitor()
        received: list[str] = []

        fake_proc = MagicMock()
        fake_proc.stdout.__iter__ = MagicMock(
            return_value=iter([
                b"  Hello from the first chunk\n",
                b"  And a second chunk\n",
            ])
        )
        fake_proc.wait.return_value = 0
        fake_proc.returncode = 0

        with patch("content_machine.asr.live.subprocess.Popen") as mock_popen:
            mock_popen.return_value = fake_proc
            monitor.stream("/tmp/live.wav", callback=received.append)

        self.assertEqual(len(received), 2)
        self.assertIn("Hello from the first chunk", received[0])

    def test_monitor_strips_timestamps_from_chunks(self):
        """Timestamp tokens are stripped from each streamed chunk."""
        monitor = self._make_monitor()
        received: list[str] = []

        fake_proc = MagicMock()
        fake_proc.stdout.__iter__ = MagicMock(
            return_value=iter([b"[00:01.000 --> 00:02.000]  Clean text here\n"])
        )
        fake_proc.wait.return_value = 0
        fake_proc.returncode = 0

        with patch("content_machine.asr.live.subprocess.Popen") as mock_popen:
            mock_popen.return_value = fake_proc
            monitor.stream("/tmp/live.wav", callback=received.append)

        self.assertNotIn("-->", received[0])
        self.assertIn("Clean text here", received[0])

    def test_monitor_uses_model_flag(self):
        """whisper.cpp is invoked with -m / --model pointing to the model file."""
        monitor = self._make_monitor(model="small")
        fake_proc = MagicMock()
        fake_proc.stdout.__iter__ = MagicMock(return_value=iter([]))
        fake_proc.wait.return_value = 0
        fake_proc.returncode = 0

        with patch("content_machine.asr.live.subprocess.Popen") as mock_popen:
            mock_popen.return_value = fake_proc
            monitor.stream("/tmp/live.wav", callback=lambda _: None)

        args = mock_popen.call_args[0][0]
        joined = " ".join(str(a) for a in args)
        self.assertIn("small", joined)

    def test_monitor_skips_empty_lines(self):
        """Blank lines in whisper.cpp output do not trigger the callback."""
        monitor = self._make_monitor()
        received: list[str] = []

        fake_proc = MagicMock()
        fake_proc.stdout.__iter__ = MagicMock(
            return_value=iter([b"\n", b"   \n", b"  actual text\n"])
        )
        fake_proc.wait.return_value = 0
        fake_proc.returncode = 0

        with patch("content_machine.asr.live.subprocess.Popen") as mock_popen:
            mock_popen.return_value = fake_proc
            monitor.stream("/tmp/live.wav", callback=received.append)

        self.assertEqual(len(received), 1)
        self.assertIn("actual text", received[0])


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [TestTranscript, TestBatchTranscriber, TestLiveMonitor]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    for t, _ in result.failures + result.errors:
        print(f"FAIL {t.id().split('.')[-1]}")
    if result.wasSuccessful():
        print("ALL PASS")
    else:
        sys.exit(1)
