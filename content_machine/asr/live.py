"""LiveMonitor: real-time streaming ASR via whisper.cpp (plan v2 §3.1).

Wraps whisper.cpp (the `whisper-stream` binary or `main` with --stream)
as a subprocess and calls a user-supplied callback for each text chunk.

Expect seconds-level latency per utterance on CPU; fine for transcript
monitoring while the operator dictates.

Install (when ready to use for real):
    # Build whisper.cpp from source: https://github.com/ggerganov/whisper.cpp
    # Place the `main` or `whisper-stream` binary on PATH as "whisper-cpp"
"""

from __future__ import annotations

import re
import subprocess
from typing import Callable, Union
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*")


def _strip_timestamps(line: str) -> str:
    return _TIMESTAMP_RE.sub("", line).strip()


class LiveMonitor:
    """Stream a whisper.cpp transcription and emit text chunks via a callback.

    Args:
        model:   Model identifier (e.g. "base", "small").  LiveMonitor
                 constructs the whisper.cpp model filename automatically as
                 ``ggml-{model}.bin`` and passes it as the ``-m`` flag.
        binary:  Name/path of the whisper.cpp binary.  Defaults to
                 "whisper-cpp" (must be on PATH).
        models_dir: Directory containing the ggml model files.  Defaults to
                 "~/.content_machine/models".
    """

    def __init__(
        self,
        model: str = "base",
        binary: str = "whisper-cpp",
        models_dir: str | None = None,
    ):
        self.model = model
        self.binary = binary
        self.models_dir = models_dir or str(Path.home() / ".content_machine" / "models")

    def _model_path(self) -> str:
        return str(Path(self.models_dir) / f"ggml-{self.model}.bin")

    def stream(
        self,
        audio_path: Union[str, Path],
        callback: Callable[[str], None],
    ) -> None:
        """Run whisper.cpp on *audio_path* and call *callback* per text chunk.

        Lines that are blank after timestamp stripping are skipped.
        The process is waited on after all output has been consumed.

        Args:
            audio_path: Path to the audio file (WAV format recommended for
                        whisper.cpp compatibility).
            callback:   Callable that receives one cleaned text string per chunk.
        """
        audio_path = str(audio_path)
        cmd = [
            self.binary,
            "-m", self._model_path(),
            "-f", audio_path,
            "--no-timestamps-markers",  # some builds support this; ignored if not
        ]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        for raw_bytes in proc.stdout:
            line = raw_bytes.decode("utf-8", errors="replace")
            cleaned = _strip_timestamps(line)
            if cleaned:
                callback(cleaned)

        proc.wait()
