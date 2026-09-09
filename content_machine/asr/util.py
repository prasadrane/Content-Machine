"""Shared ASR text utilities (plan v2 §3.1).

Used by both batch (faster-whisper) and live (whisper.cpp) transcription —
previously each module carried its own copy of the timestamp regex.
"""

from __future__ import annotations

import re

# Regex that matches faster-whisper / whisper.cpp timestamp lines, e.g.:
#   [00:00.000 --> 00:03.000]  Some text
#   [00:03.500 --> 00:06.000]  More text
_TIMESTAMP_RE = re.compile(r"\[\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}\]\s*")


def strip_timestamps(text: str) -> str:
    """Remove timestamp markers and return clean prose.

    Per-line stripping + blank-line dropping; surviving lines are joined
    with a single space.  For a single input line (live streaming use) this
    is exactly strip-and-clean; for multi-line output (batch transcripts)
    it folds to one prose block.
    """
    lines = []
    for line in text.splitlines():
        cleaned = _TIMESTAMP_RE.sub("", line).strip()
        if cleaned:
            lines.append(cleaned)
    return " ".join(lines)
