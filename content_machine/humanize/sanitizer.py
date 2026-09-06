"""Deterministic pre/post sanitizer and statistical burstiness calculator."""

from __future__ import annotations

import math
import re
from typing import List, Tuple

from .constants import BANNED_AI_WORDS, BANNED_AI_PHRASES, EM_DASH_PATTERN

PROHIBITED_COMPANIES: list[str] = [
    "Rocket Mortgage",
    "London Computer Systems",
    "EXFO",
    "Tanish Infotech",
]

PROHIBITED_CORP_PATTERNS: list[str] = [
    r"\bmy team at work\b",
    r"\bmy company today\b",
    r"\bat my current job\b",
    r"\bat my company\b",
    r"\bour team at work\b",
    r"\bat our company\b",
    r"\bour company today\b",
]

WORD_REPLACEMENTS: dict[str, str] = {
    "delve": "dig",
    "delves": "digs",
    "delving": "digging",
    "tapestry": "structure",
    "tapestries": "structures",
    "pivotal": "crucial",
    "testament": "evidence",
    "cornerstone": "foundation",
    "robust": "resilient",
    "vibrant": "active",
    "realm": "domain",
    "realms": "domains",
    "foster": "encourage",
    "fosters": "encourages",
    "fostering": "encouraging",
    "harness": "use",
    "harnessing": "using",
    "interplay": "dynamics",
    "multifaceted": "complex",
    "paramount": "vital",
    "game-changer": "major shift",
    "gamechanger": "major shift",
    "revolutionize": "transform",
    "revolutionizing": "transforming",
    "seamlessly": "smoothly",
    "seamless": "smooth",
    "plethora": "variety",
    "beacon": "model",
    "underscores": "highlights",
    "underscoring": "highlighting",
    "synergy": "alignment",
    "synergies": "alignments",
    "utilize": "use",
    "utilizes": "uses",
    "utilizing": "using",
    "facilitate": "run",
    "facilitates": "runs",
    "facilitating": "running",
    "holistic": "complete",
    "endeavor": "effort",
    "endeavors": "efforts",
}

PHRASE_REPLACEMENTS: dict[str, str] = {
    "stands as a testament": "serves as proof",
    "serves as a testament": "serves as proof",
    "serves as a reminder": "reminds us",
    "a testament to the power": "proof of the power",
    "pivotal moment": "turning point",
    "crucial role": "vital role",
    "key role": "vital role",
    "evolving landscape": "changing landscape",
    "rapidly evolving": "fast-changing",
    "indelible mark": "lasting mark",
    "transformative journey": "major shift",
    "focal point": "center",
    "deeply rooted": "grounded",
    "setting the stage": "preparing the ground",
    "in today's fast-paced": "in today's",
    "in today's world": "today",
    "it is important to note": "note that",
    "it's important to remember": "remember that",
    "not only that, but": "also,",
    "unlock value": "deliver value",
}


def _match_case(original: str, replacement: str) -> str:
    """Preserve title or upper casing from matched token."""
    if original.isupper():
        return replacement.upper()
    if original and original[0].isupper():
        return replacement.capitalize()
    return replacement


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """Deterministically scrub banned AI phrases, words, and em-dashes."""
    cleaned = text
    purged: list[str] = []

    # 1. Normalize em-dashes to commas with clean spacing
    if EM_DASH_PATTERN.search(cleaned):
        cleaned = EM_DASH_PATTERN.sub(", ", cleaned)
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        cleaned = re.sub(r",\s*\.", ".", cleaned)

    # 2. Check and purge banned multi-word phrases
    for phrase in BANNED_AI_PHRASES:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        if pattern.search(cleaned):
            purged.append(phrase)
            replacement = PHRASE_REPLACEMENTS.get(phrase, "key factor")
            cleaned = pattern.sub(lambda m: _match_case(m.group(0), replacement), cleaned)

    # 3. Check and replace single banned words
    for word, replacement in WORD_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        if pattern.search(cleaned):
            purged.append(word)
            cleaned = pattern.sub(lambda m: _match_case(m.group(0), replacement), cleaned)

    # 4. Fallback check for any remaining BANNED_AI_WORDS not in WORD_REPLACEMENTS
    for word in BANNED_AI_WORDS:
        if word not in WORD_REPLACEMENTS:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(cleaned):
                purged.append(word)
                cleaned = pattern.sub("", cleaned)

    # Cleanup any leftover double spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned, sorted(list(set(purged)))


def calculate_burstiness(text: str) -> float:
    """Compute standard deviation of sentence word counts in text."""
    if not text or not text.strip():
        return 0.0

    raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    # Filter to sentences that contain at least one word
    sentence_word_counts = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    sentence_word_counts = [cnt for cnt in sentence_word_counts if cnt > 0]

    if len(sentence_word_counts) < 2:
        return 0.0

    mean_length = sum(sentence_word_counts) / len(sentence_word_counts)
    variance = sum((l - mean_length) ** 2 for l in sentence_word_counts) / len(sentence_word_counts)
    return round(math.sqrt(variance), 2)


def check_author_invariants(text: str) -> List[str]:
    """Verify that zero prohibited employers or corporate claims appear."""
    violations: list[str] = []
    text_lower = text.lower()

    for comp in PROHIBITED_COMPANIES:
        if comp.lower() in text_lower:
            violations.append(f"Prohibited employer mention detected: {comp}")

    for pat in PROHIBITED_CORP_PATTERNS:
        if re.search(pat, text_lower):
            violations.append(f"Prohibited corporate employment claim detected: pattern '{pat}'")

    return violations
