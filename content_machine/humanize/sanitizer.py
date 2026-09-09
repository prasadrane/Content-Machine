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
    "stop the bleeding": "fix the issue",
    "stops the bleeding": "fixes the issue",
    "stopping the bleeding": "fixing the issue",
    "the workflow that stops": "what works",
    "feels like pure velocity": "feels fast",
    "feels fast until": "seems quick until",
}

PRECOMPILED_PHRASE_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        phrase,
        re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE),
        PHRASE_REPLACEMENTS.get(phrase, "key factor"),
    )
    for phrase in BANNED_AI_PHRASES
]

PRECOMPILED_WORD_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        word,
        re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE),
        replacement,
    )
    for word, replacement in WORD_REPLACEMENTS.items()
]

PRECOMPILED_EXTRA_BANNED_WORDS: list[tuple[str, re.Pattern[str]]] = [
    (
        word,
        re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE),
    )
    for word in BANNED_AI_WORDS
    if word not in WORD_REPLACEMENTS
]

PROHIBITED_CORP_COMPILED: list[re.Pattern[str]] = [
    re.compile(pat, re.IGNORECASE) for pat in PROHIBITED_CORP_PATTERNS
]

SENTENCE_SPLIT_PATTERN: re.Pattern[str] = re.compile(r"(?<=[.!?])\s+|\n+")
WORD_TOKEN_PATTERN: re.Pattern[str] = re.compile(r"\b\w+\b")
MULTI_SPACE_PATTERN: re.Pattern[str] = re.compile(r"[ \t]+")
DOUBLE_COMMA_PATTERN: re.Pattern[str] = re.compile(r",\s*,+")
COMMA_DOT_PATTERN: re.Pattern[str] = re.compile(r",\s*\.")


def _match_case(original: str, replacement: str) -> str:
    """Preserve title or upper casing from matched token."""
    if original.isupper():
        return replacement.upper()
    if original and original[0].isupper():
        return replacement.capitalize()
    return replacement


def split_sentences(text: str) -> list[str]:
    """Tokenize text into distinct sentences on terminal punctuation and newlines."""
    if not text or not text.strip():
        return []
    raw_sentences = SENTENCE_SPLIT_PATTERN.split(text.strip())
    return [s.strip() for s in raw_sentences if s.strip()]


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """Deterministically scrub banned AI phrases, words, and em-dashes."""
    cleaned = text
    purged: list[str] = []

    # 1. Normalize em-dashes to commas with clean spacing
    if EM_DASH_PATTERN.search(cleaned):
        cleaned = EM_DASH_PATTERN.sub(", ", cleaned)
        cleaned = DOUBLE_COMMA_PATTERN.sub(",", cleaned)
        cleaned = COMMA_DOT_PATTERN.sub(".", cleaned)

    # 2. Check and purge banned multi-word phrases
    for phrase, pattern, replacement in PRECOMPILED_PHRASE_PATTERNS:
        if pattern.search(cleaned):
            purged.append(phrase)
            cleaned = pattern.sub(lambda m, r=replacement: _match_case(m.group(0), r), cleaned)

    # 3. Check and replace single banned words
    for word, pattern, replacement in PRECOMPILED_WORD_PATTERNS:
        if pattern.search(cleaned):
            purged.append(word)
            cleaned = pattern.sub(lambda m, r=replacement: _match_case(m.group(0), r), cleaned)

    # 4. Fallback check for any remaining BANNED_AI_WORDS not in WORD_REPLACEMENTS
    for word, pattern in PRECOMPILED_EXTRA_BANNED_WORDS:
        if pattern.search(cleaned):
            purged.append(word)
            cleaned = pattern.sub("", cleaned)

    # Cleanup any leftover double spaces
    cleaned = MULTI_SPACE_PATTERN.sub(" ", cleaned).strip()
    return cleaned, sorted(list(set(purged)))


def calculate_burstiness(text: str) -> float:
    """Compute standard deviation of sentence word counts in text."""
    sentences = split_sentences(text)
    if not sentences:
        return 0.0

    # Filter to sentences that contain at least one word
    sentence_word_counts = [len(WORD_TOKEN_PATTERN.findall(s)) for s in sentences]
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

    for pat in PROHIBITED_CORP_COMPILED:
        if pat.search(text_lower):
            violations.append(f"Prohibited corporate employment claim detected: pattern '{pat.pattern}'")

    return violations
