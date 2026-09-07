"""Transcript dataclass — canonical output of both ASR paths (plan v2 §3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Transcript:
    """Text transcript produced by BatchTranscriber or assembled from LiveMonitor."""

    text: str
    model: str        # e.g. "faster-whisper/small" or "whisper.cpp/base"
    audio_path: str   # source audio file (absolute path string)
    duration_s: float # audio duration in seconds; 0.0 if unknown

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def meets_minimum(self, min_words: int = 800) -> bool:
        """Return True when transcript has at least min_words (plan v2 §3)."""
        return self.word_count >= min_words

    def save(self, path: str | Path) -> Path:
        """Write a Markdown file with YAML-like header + body text.

        Args:
            path: Destination file path; parent directories must exist.

        Returns:
            Path to the written file.
        """
        p = Path(path)
        header = (
            f"# Transcript\n\n"
            f"- model: {self.model}\n"
            f"- audio: {self.audio_path}\n"
            f"- duration_s: {self.duration_s:.1f}\n"
            f"- word_count: {self.word_count}\n\n"
            f"---\n\n"
        )
        p.write_text(header + self.text, encoding="utf-8")
        return p
