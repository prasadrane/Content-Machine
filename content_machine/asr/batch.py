"""BatchTranscriber: post-recording ASR via faster-whisper CLI (plan v2 §3.1).

Runs faster-whisper as a subprocess.  CPU-only: always uses --compute_type int8.
Model size: small → base → large-v3 as CPU budget allows; default small.

Install (when ready to use for real):
    pip install faster-whisper
    # or use the CLI wrapper: pip install faster-whisper[cli]
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Union

from content_machine.asr.transcript import Transcript

# Regex that matches faster-whisper / whisper.cpp timestamp lines, e.g.:
#   [00:00.000 --> 00:03.000]  Some text
#   [00:03.500 --> 00:06.000]  More text
_TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*")


def _strip_timestamps(raw: str) -> str:
    """Remove timestamp markers and return clean prose, one sentence per line."""
    lines = []
    for line in raw.splitlines():
        cleaned = _TIMESTAMP_RE.sub("", line).strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)


class BatchTranscriber:
    """Transcribe a completed audio file using the faster-whisper CLI.

    Args:
        model:        Whisper model size: "tiny", "base", "small", "medium", "large-v3".
        binary:       Path/name of the faster-whisper executable. Defaults to
                      "faster-whisper", which must be on PATH.
        extra_args:   Additional CLI arguments forwarded verbatim.
    """

    def __init__(
        self,
        model: str = "small",
        binary: str = "faster-whisper",
        extra_args: list[str] | None = None,
    ):
        self.model = model
        self.binary = binary
        self.extra_args = extra_args or []

    def transcribe(self, audio_path: Union[str, Path]) -> Transcript:
        """Run faster-whisper on *audio_path* and return a Transcript.

        Args:
            audio_path: Path to the audio file (WAV, MP3, M4A, etc.).

        Returns:
            Transcript with cleaned text (timestamps stripped).

        Raises:
            RuntimeError: if faster-whisper exits with a non-zero return code.
        """
        audio_path = str(audio_path)
        cmd = [
            self.binary,
            audio_path,
            "--model", self.model,
            "--compute_type", "int8",   # CPU-only per plan v2 §3.1
            "--output_format", "txt",
        ] + self.extra_args

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"faster-whisper failed (exit {proc.returncode}): {proc.stderr.strip()}"
            )

        text = _strip_timestamps(proc.stdout)

        return Transcript(
            text=text,
            model=f"faster-whisper/{self.model}",
            audio_path=audio_path,
            duration_s=0.0,  # faster-whisper stdout doesn't always report duration
        )
