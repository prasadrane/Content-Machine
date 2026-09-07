"""ASR subsystem — dual-path transcription (plan v2 §3.1, CPU-only).

Two paths, both offline-capable, no CUDA required:

Batch (post-recording):
    BatchTranscriber  wraps faster-whisper CLI with --compute_type int8.
    Use for canonical transcripts before drafting.

Live (streaming during dictation):
    LiveMonitor  wraps whisper.cpp, emitting text chunks via callback.
    Use for real-time display while operator dictates.

Shared output type:
    Transcript  — text, model label, source path, word_count, save().

Install (deferred — requires voice sample for WER benchmark):
    pip install faster-whisper      # batch path
    # Build whisper.cpp from source for live path.
"""

from content_machine.asr.transcript import Transcript
from content_machine.asr.batch import BatchTranscriber
from content_machine.asr.live import LiveMonitor

__all__ = ["Transcript", "BatchTranscriber", "LiveMonitor"]
