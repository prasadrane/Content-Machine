# Humanize Transformer Subsystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and integrate a dedicated, two-tier Humanize Transformer subsystem (`content_machine/humanize/`) that purges AI tells (low burstiness, puffery, Latinate clichés, excessive em-dashes) and injects natural human cadence across LinkedIn comments, Council peak drafts, and derivative channels.

**Architecture:** A prompt-tier LLM rewrite powered by `qwen3.8-max` (enforcing rhythmic burstiness and authentic contractions) combined with a deterministic regex/statistical sanitizer (purging 35+ banned AI words, normalizing punctuation, computing sentence standard deviation $\sigma$, and guaranteeing author voice invariants). The engine is exposed via a standalone `POST /api/humanize` endpoint, integrated into `CommentingEngine` and `DistributionEngine`, and equipped with UI controls across the Council, Commenting, and Distribution views.

**Tech Stack:** Python 3.11, Pydantic v2, FastAPI, SQLite3, React 18, Vite, Tailwind CSS, unittest.

## Global Constraints

- Never cite past employers (Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.).
- Never claim current corporate team employment (*"My team at work..."*, *"At my company..."*).
- Maintain job-status agnostic senior authority and craftsmanship.
- Maintain comment sentence limit (strictly 2–3 sentences max).
- 100% offline-capable unit tests (use `FakeRouter` for router mocks).
- All changes must pass `python -m unittest discover -s tests` with 0 failures.
- Frontend production bundle must build cleanly (`npm run build` with 0 errors).

---

### Task 1: Schemas, Constants & Anti-AI Blacklist

**Files:**
- Modify: `content_machine/schemas.py:100-150`
- Create: `content_machine/humanize/__init__.py`
- Create: `content_machine/humanize/constants.py`
- Create: `tests/test_humanize.py`

**Interfaces:**
- Produces: `HumanizeTone`, `HumanizeChannel`, `HumanizeRequest`, `HumanizeResult` schemas in `content_machine.schemas`.
- Produces: `BANNED_AI_WORDS`, `BANNED_AI_PHRASES`, `EM_DASH_PATTERN`, `TONE_SYSTEM_PROMPTS`, `CHANNEL_PROMPTS` in `content_machine.humanize.constants`.

- [ ] **Step 1: Write the failing test for schemas and constants**

Create `tests/test_humanize.py`:
```python
"""Tests for Humanize Transformer schemas, constants, sanitizer, and engine."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.schemas import (
    HumanizeTone,
    HumanizeChannel,
    HumanizeRequest,
    HumanizeResult,
)
from content_machine.humanize.constants import (
    BANNED_AI_WORDS,
    BANNED_AI_PHRASES,
    TONE_SYSTEM_PROMPTS,
    CHANNEL_PROMPTS,
)


class TestHumanizeSchemasAndConstants(unittest.TestCase):
    def test_humanize_enums(self):
        self.assertEqual(HumanizeTone.PUNCHY_DIRECT.value, "punchy_direct")
        self.assertEqual(HumanizeTone.PRAGMATIC_ARCHITECT.value, "pragmatic_architect")
        self.assertEqual(HumanizeTone.CONVERSATIONAL_PEER.value, "conversational_peer")

        self.assertEqual(HumanizeChannel.LINKEDIN_COMMENT.value, "linkedin_comment")
        self.assertEqual(HumanizeChannel.LINKEDIN_POST.value, "linkedin_post")
        self.assertEqual(HumanizeChannel.X_THREAD.value, "x_thread")
        self.assertEqual(HumanizeChannel.VIDEO_SCRIPT.value, "video_script")
        self.assertEqual(HumanizeChannel.GENERAL.value, "general")

    def test_humanize_request_and_result(self):
        req = HumanizeRequest(
            text="This is a test post that needs to be humanized.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
        )
        self.assertEqual(req.channel, HumanizeChannel.LINKEDIN_POST)
        self.assertEqual(req.tone, HumanizeTone.PUNCHY_DIRECT)

        res = HumanizeResult(
            original_text=req.text,
            humanized_text="Test post rewritten.",
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=HumanizeTone.PUNCHY_DIRECT,
            banned_words_purged=["delve"],
            burstiness_score=4.2,
            sentence_count=1,
            was_modified=True,
        )
        self.assertEqual(res.burstiness_score, 4.2)
        self.assertEqual(res.banned_words_purged, ["delve"])

    def test_banned_constants_presence(self):
        self.assertIn("delve", BANNED_AI_WORDS)
        self.assertIn("tapestry", BANNED_AI_WORDS)
        self.assertIn("pivotal", BANNED_AI_WORDS)
        self.assertIn("testament", BANNED_AI_WORDS)
        self.assertIn("cornerstone", BANNED_AI_WORDS)
        self.assertIn("robust", BANNED_AI_WORDS)
        self.assertTrue(len(BANNED_AI_WORDS) >= 25)

        # Check phrases
        phrases_str = " ".join(BANNED_AI_PHRASES).lower()
        self.assertIn("stands as a testament", phrases_str)
        self.assertIn("evolving landscape", phrases_str)

        # Check prompts
        self.assertIn(HumanizeTone.PUNCHY_DIRECT, TONE_SYSTEM_PROMPTS)
        self.assertIn(HumanizeChannel.LINKEDIN_COMMENT, CHANNEL_PROMPTS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_humanize.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'content_machine.humanize'` or `ImportError`.

- [ ] **Step 3: Implement schemas and constants**

1. In `content_machine/schemas.py`, append the humanize models:
```python
class HumanizeTone(str, Enum):
    PUNCHY_DIRECT = "punchy_direct"
    PRAGMATIC_ARCHITECT = "pragmatic_architect"
    CONVERSATIONAL_PEER = "conversational_peer"


class HumanizeChannel(str, Enum):
    LINKEDIN_COMMENT = "linkedin_comment"
    LINKEDIN_POST = "linkedin_post"
    X_THREAD = "x_thread"
    VIDEO_SCRIPT = "video_script"
    GENERAL = "general"


class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=10, description="Draft text to humanize")
    channel: HumanizeChannel = Field(default=HumanizeChannel.LINKEDIN_POST)
    tone: HumanizeTone = Field(default=HumanizeTone.PRAGMATIC_ARCHITECT)
    max_sentences: Optional[int] = Field(default=None, description="Optional hard sentence clamp")


class HumanizeResult(BaseModel):
    original_text: str
    humanized_text: str
    channel: HumanizeChannel
    tone: HumanizeTone
    banned_words_purged: list[str] = Field(default_factory=list)
    burstiness_score: float = Field(default=0.0, description="Standard deviation of sentence word counts")
    sentence_count: int = Field(default=0)
    was_modified: bool = Field(default=True)
```

2. Create `content_machine/humanize/constants.py`:
```python
"""Constants, blacklists, and system prompts for the Humanize Transformer."""

from __future__ import annotations

import re
from content_machine.schemas import HumanizeChannel, HumanizeTone

BANNED_AI_WORDS: set[str] = {
    "delve", "delves", "delving",
    "tapestry", "tapestries",
    "pivotal",
    "testament",
    "cornerstone",
    "robust",
    "vibrant",
    "realm", "realms",
    "foster", "fosters", "fostering",
    "harness", "harnessing",
    "interplay",
    "multifaceted",
    "paramount",
    "game-changer", "gamechanger",
    "revolutionize", "revolutionizing",
    "seamlessly", "seamless",
    "plethora",
    "beacon",
    "underscores", "underscoring",
    "synergy", "synergies",
    "utilize", "utilizes", "utilizing",
    "facilitate", "facilitates", "facilitating",
    "holistic",
    "endeavor", "endeavors",
}

BANNED_AI_PHRASES: list[str] = [
    "stands as a testament",
    "serves as a testament",
    "serves as a reminder",
    "pivotal moment",
    "crucial role",
    "key role",
    "evolving landscape",
    "rapidly evolving",
    "indelible mark",
    "transformative journey",
    "focal point",
    "deeply rooted",
    "setting the stage",
    "in today's fast-paced",
    "in today's world",
    "it is important to note",
    "it's important to remember",
    "not only that, but",
    "a testament to the power",
    "unlock value",
]

EM_DASH_PATTERN = re.compile(r"\s*—\s*|\s*--\s*")

TONE_SYSTEM_PROMPTS: dict[HumanizeTone, str] = {
    HumanizeTone.PUNCHY_DIRECT: (
        "You are an elite technical editor turning draft content into human-level craft. "
        "Tone: PUNCHY & DIRECT. Short, crisp sentences, high burstiness, zero fluff, immediate mechanical point. "
        "Use contractions (it's, don't, we've). Ban all corporate cheerleading and clichés."
    ),
    HumanizeTone.PRAGMATIC_ARCHITECT: (
        "You are a senior principal systems engineer rewriting draft content in your authentic voice. "
        "Tone: PRAGMATIC ARCHITECT. Focus on production realities, trade-offs, architecture trade-offs, "
        "and concrete mechanics. Asymmetric rhythm: mix sharp observations with detailed explanations."
    ),
    HumanizeTone.CONVERSATIONAL_PEER: (
        "You are a friendly senior engineer chatting with a colleague over coffee. "
        "Tone: CONVERSATIONAL PEER. Warm, reflective, accessible, candid, and grounded. "
        "Use conversational qualifiers ('in practice,', 'the catch is,', 'honestly,')."
    ),
}

CHANNEL_PROMPTS: dict[HumanizeChannel, str] = {
    HumanizeChannel.LINKEDIN_COMMENT: (
        "Transform this into a 2-3 sentence LinkedIn comment. "
        "Jump straight into the technical argument or counter-point. Never say 'Great post!' or 'Spot on!'. "
        "Never exceed 3 sentences. High burstiness."
    ),
    HumanizeChannel.LINKEDIN_POST: (
        "Transform this into an authentic LinkedIn post. "
        "Hook fast with a 1-line observation. Use asymmetric paragraph blocks (1 line, then 3 lines, then 1 line). "
        "Close on a blunt operational takeaway. Zero decorative bullet emojis."
    ),
    HumanizeChannel.X_THREAD: (
        "Transform this into a natural X/Twitter thread. "
        "Hook fast without thread clichés like '1/ A masterclass in...'. Keep tweets tight and punchy."
    ),
    HumanizeChannel.VIDEO_SCRIPT: (
        "Transform this into a spoken, breathable short-form video script. "
        "Preserve visual cues in square brackets (e.g., [Visual Cue], [Camera Zoom]). Natural spoken rhythm."
    ),
    HumanizeChannel.GENERAL: (
        "Rewrite this technical text to sound completely human. "
        "Vary sentence lengths dramatically. Purge all AI tells."
    ),
}
```

3. Create `content_machine/humanize/__init__.py`:
```python
"""Humanize Transformer subsystem."""

from content_machine.schemas import (
    HumanizeChannel,
    HumanizeRequest,
    HumanizeResult,
    HumanizeTone,
)

__all__ = [
    "HumanizeTone",
    "HumanizeChannel",
    "HumanizeRequest",
    "HumanizeResult",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_humanize.py`  
Expected: OK (3 tests passing).

- [ ] **Step 5: Commit**

```bash
git add content_machine/schemas.py content_machine/humanize/ constants.py tests/test_humanize.py
git commit -m "feat(humanize): add schemas, constants, and anti-AI tells catalog"
```

---

### Task 2: Deterministic Sanitizer & Burstiness Metric

**Files:**
- Create: `content_machine/humanize/sanitizer.py`
- Modify: `content_machine/humanize/__init__.py`
- Test: `tests/test_humanize.py`

**Interfaces:**
- Consumes: `BANNED_AI_WORDS`, `BANNED_AI_PHRASES`, `EM_DASH_PATTERN` from `content_machine.humanize.constants`.
- Produces: `sanitize_text(text: str) -> tuple[str, list[str]]`
- Produces: `calculate_burstiness(text: str) -> float`
- Produces: `check_author_invariants(text: str) -> list[str]` (returns violations if any)

- [ ] **Step 1: Write failing tests for sanitizer and burstiness**

In `tests/test_humanize.py`, add `TestHumanizeSanitizer`:
```python
class TestHumanizeSanitizer(unittest.TestCase):
    def test_sanitize_text_purges_banned_words(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = (
            "We must delve into this tapestry of ideas. "
            "It stands as a testament to our robust architecture, marking a pivotal moment."
        )
        cleaned, purged = sanitize_text(text)
        self.assertNotIn("delve", cleaned.lower())
        self.assertNotIn("tapestry", cleaned.lower())
        self.assertNotIn("stands as a testament", cleaned.lower())
        self.assertIn("delve", purged)
        self.assertIn("tapestry", purged)

    def test_sanitize_text_normalizes_em_dashes(self):
        from content_machine.humanize.sanitizer import sanitize_text

        text = "This pattern — which is often overlooked — solves the issue."
        cleaned, _ = sanitize_text(text)
        self.assertNotIn("—", cleaned)
        self.assertIn(",", cleaned)

    def test_calculate_burstiness_variance(self):
        from content_machine.humanize.sanitizer import calculate_burstiness

        # Monotone AI text: every sentence is exactly 5 words
        monotone = "One two three four five. Six seven eight nine ten. Eleven twelve thirteen fourteen fifteen."
        score_monotone = calculate_burstiness(monotone)
        self.assertEqual(score_monotone, 0.0)

        # Bursty human text: 2 words, then 14 words, then 4 words
        bursty = "It broke. The entire distributed cluster failed because the queue dropped partition messages under load. We fixed it."
        score_bursty = calculate_burstiness(bursty)
        self.assertTrue(score_bursty > 4.0)

    def test_check_author_invariants(self):
        from content_machine.humanize.sanitizer import check_author_invariants

        clean_text = "Kafka partition lag spikes when consumer threads block on database I/O."
        self.assertEqual(check_author_invariants(clean_text), [])

        # Prohibited company mention
        dirty_text = "When I was building microservices at Rocket Mortgage, we used Kafka."
        violations = check_author_invariants(dirty_text)
        self.assertTrue(any("Rocket Mortgage" in v for v in violations))

        # Prohibited current corporate employment claim
        corp_text = "My team at work today just migrated our cluster."
        violations_corp = check_author_invariants(corp_text)
        self.assertTrue(any("team at work" in v for v in violations_corp))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_humanize.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'content_machine.humanize.sanitizer'`.

- [ ] **Step 3: Implement `content_machine/humanize/sanitizer.py`**

Create `content_machine/humanize/sanitizer.py`:
```python
"""Deterministic pre/post sanitizer and statistical burstiness calculator."""

from __future__ import annotations

import math
import re
from typing import Tuple, List

from .constants import BANNED_AI_WORDS, BANNED_AI_PHRASES, EM_DASH_PATTERN

PROHIBITED_COMPANIES = [
    "Rocket Mortgage",
    "London Computer Systems",
    "EXFO",
    "Tanish Infotech",
]

PROHIBITED_CORP_PATTERNS = [
    r"\bmy team at work\b",
    r"\bmy company today\b",
    r"\bat my current job\b",
    r"\bat my company\b",
    r"\bour team at work\b",
]

WORD_REPLACEMENTS = {
    "delve into": "explore",
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
    "harness": "use",
    "harnessing": "using",
    "interplay": "dynamics",
    "multifaceted": "complex",
    "paramount": "vital",
    "game-changer": "major shift",
    "revolutionize": "transform",
    "seamlessly": "smoothly",
    "seamless": "smooth",
    "plethora": "variety",
    "beacon": "model",
    "underscores": "highlights",
    "underscoring": "highlighting",
    "synergy": "alignment",
    "utilize": "use",
    "utilizes": "uses",
    "utilizing": "using",
    "facilitate": "run",
    "facilitates": "runs",
    "facilitating": "running",
    "holistic": "complete",
    "endeavor": "effort",
}


def sanitize_text(text: str) -> Tuple[str, List[str]]:
    """Deterministically scrub banned AI phrases, words, and em-dashes."""
    cleaned = text
    purged: list[str] = []

    # 1. Normalize em-dashes to commas with clean spacing
    if EM_DASH_PATTERN.search(cleaned):
        cleaned = EM_DASH_PATTERN.sub(", ", cleaned)
        # Fix potential multiple commas
        cleaned = re.sub(r",\s*,", ",", cleaned)

    # 2. Check and purge banned multi-word phrases
    for phrase in BANNED_AI_PHRASES:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
        if pattern.search(cleaned):
            purged.append(phrase)
            # Remove or replace with simple neutral word
            cleaned = pattern.sub("key factor", cleaned)

    # 3. Check and replace single banned words
    for word, replacement in WORD_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        if pattern.search(cleaned):
            purged.append(word)
            cleaned = pattern.sub(replacement, cleaned)

    # Cleanup any leftover double spaces
    cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
    return cleaned, sorted(list(set(purged)))


def calculate_burstiness(text: str) -> float:
    """Compute standard deviation of sentence word counts in text."""
    # Split text into sentences using common delimiters (. ! ?)
    raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip() and len(s.split()) > 0]

    if len(sentences) < 2:
        return 0.0

    lengths = [len(re.findall(r"\b\w+\b", s)) for s in sentences]
    mean_length = sum(lengths) / len(lengths)
    variance = sum((l - mean_length) ** 2 for l in lengths) / len(lengths)
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
```

Update `content_machine/humanize/__init__.py` to export `sanitize_text`, `calculate_burstiness`, `check_author_invariants`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_humanize.py`  
Expected: OK (7 tests passing).

- [ ] **Step 5: Commit**

```bash
git add content_machine/humanize/sanitizer.py content_machine/humanize/__init__.py tests/test_humanize.py
git commit -m "feat(humanize): add deterministic sanitizer, burstiness calculator, and invariant checker"
```

---

### Task 3: Core HumanizeTransformer Engine

**Files:**
- Create: `content_machine/humanize/transformer.py`
- Modify: `content_machine/humanize/__init__.py`
- Test: `tests/test_humanize.py`

**Interfaces:**
- Consumes: `ModelRouter` from `content_machine.router.base`, `ProfileManager` from `content_machine.profile.manager`, `sanitizer` and `constants`.
- Produces: `HumanizeTransformer` class with `transform(...)`, `humanize_comment(...)`, `humanize_post(...)`.

- [ ] **Step 1: Write failing tests for HumanizeTransformer**

In `tests/test_humanize.py`, add `TestHumanizeTransformer`:
```python
class FakeRouter:
    def __init__(self, response_text: str = ""):
        self.response_text = response_text
        self.calls = []

    def complete(self, models, prompt="", system="", **kwargs):
        self.calls.append({"models": models, "prompt": prompt, "system": system})
        if self.response_text == "RAISE":
            raise RuntimeError("LLM Failure")
        return self.response_text


class TestHumanizeTransformer(unittest.TestCase):
    def test_transform_comment_enforces_max_sentences(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        fake_reply = "Here is point one. Here is point two. Here is point three. Here is point four that should be dropped."
        router = FakeRouter(response_text=fake_reply)
        transformer = HumanizeTransformer(router=router, voice_guide="Author voice guide")

        res = transformer.humanize_comment("Raw comment text", max_sentences=3)
        self.assertEqual(res.channel, HumanizeChannel.LINKEDIN_COMMENT)
        self.assertEqual(res.tone, HumanizeTone.PUNCHY_DIRECT)
        self.assertEqual(res.sentence_count, 3)
        self.assertNotIn("point four", res.humanized_text)

    def test_transform_tones_and_channels(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        fake_reply = "A pragmatic take on distributed event logs. You need backpressure."
        router = FakeRouter(response_text=fake_reply)
        transformer = HumanizeTransformer(router=router)

        res = transformer.humanize_post(
            "Draft post text about distributed event logs",
            tone=HumanizeTone.PRAGMATIC_ARCHITECT,
        )
        self.assertEqual(res.channel, HumanizeChannel.LINKEDIN_POST)
        self.assertEqual(res.tone, HumanizeTone.PRAGMATIC_ARCHITECT)
        self.assertIn("backpressure", res.humanized_text)

        # Verify prompt contained tone system instructions
        last_call = router.calls[-1]
        self.assertIn("PRAGMATIC ARCHITECT", last_call["system"])

    def test_transform_fallback_on_router_failure(self):
        from content_machine.humanize.transformer import HumanizeTransformer

        router = FakeRouter(response_text="RAISE")
        transformer = HumanizeTransformer(router=router)

        raw = "We must delve into this — it is a pivotal moment."
        res = transformer.transform(raw, channel=HumanizeChannel.GENERAL)
        # Should gracefully fall back to sanitizer output
        self.assertNotIn("delve", res.humanized_text)
        self.assertNotIn("—", res.humanized_text)
        self.assertIn("delve", res.banned_words_purged)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_humanize.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'content_machine.humanize.transformer'`.

- [ ] **Step 3: Implement `content_machine/humanize/transformer.py`**

Create `content_machine/humanize/transformer.py`:
```python
"""HumanizeTransformer engine: prompt-tier LLM rewrite + deterministic sanitizer."""

from __future__ import annotations

import logging
import re
from typing import Optional

from content_machine.profile.manager import ProfileManager
from content_machine.schemas import (
    HumanizeChannel,
    HumanizeRequest,
    HumanizeResult,
    HumanizeTone,
)
from .constants import CHANNEL_PROMPTS, TONE_SYSTEM_PROMPTS
from .sanitizer import (
    calculate_burstiness,
    check_author_invariants,
    sanitize_text,
)

logger = logging.getLogger(__name__)


class HumanizeTransformer:
    def __init__(
        self,
        router: any,
        model: str = "qwen3.8-max",
        voice_guide: Optional[str] = None,
    ):
        self.router = router
        self.model = model
        if voice_guide is not None:
            self.voice_guide = voice_guide
        else:
            try:
                self.voice_guide = ProfileManager().get_voice_guide_text()
            except Exception:
                self.voice_guide = ""

    def transform(
        self,
        text: str,
        channel: HumanizeChannel = HumanizeChannel.LINKEDIN_POST,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
        max_sentences: Optional[int] = None,
    ) -> HumanizeResult:
        """Transform text into human-level craft, purging AI tells and enforcing voice."""
        original = text.strip()
        if not original:
            return HumanizeResult(
                original_text=original,
                humanized_text="",
                channel=channel,
                tone=tone,
                sentence_count=0,
                was_modified=False,
            )

        # 1. Assemble prompt
        tone_sys = TONE_SYSTEM_PROMPTS.get(tone, TONE_SYSTEM_PROMPTS[HumanizeTone.PRAGMATIC_ARCHITECT])
        chan_prompt = CHANNEL_PROMPTS.get(channel, CHANNEL_PROMPTS[HumanizeChannel.GENERAL])

        system = f"{tone_sys}\n\nCHANNEL CONSTRAINT:\n{chan_prompt}"
        if self.voice_guide:
            system += f"\n\nAUTHOR VOICE & NEGATIVE CONSTRAINTS:\n{self.voice_guide}"

        prompt = (
            f"Rewrite the following draft to make it sound completely human and authentic.\n"
            f"Rules:\n"
            f"1. Break uniform sentence lengths; vary cadence dramatically (high burstiness).\n"
            f"2. Use contractions (don't, it's, we've) and concrete mechanical verbs.\n"
            f"3. Eliminate ALL AI tells: no 'delve', 'tapestry', 'pivotal', 'testament', or em-dashes (—).\n"
            f"4. Never hallucinate facts or mention unverified employers.\n"
            f"5. Output ONLY the rewritten text. No meta-commentary, code fences, or preamble.\n\n"
            f"DRAFT TO HUMANIZE:\n{original}"
        )

        humanized_raw = ""
        try:
            res = self.router.complete(
                [self.model],
                prompt=prompt,
                system=system,
            )
            humanized_raw = str(res).strip()
        except Exception as e:
            logger.warning("HumanizeTransformer LLM call failed, falling back to sanitizer: %s", e)
            humanized_raw = original

        # 2. Deterministic sanitize pass
        cleaned, purged = sanitize_text(humanized_raw)

        # 3. Enforce author invariants
        invariants = check_author_invariants(cleaned)
        if invariants:
            logger.warning("Author invariant warning in humanized text: %s", invariants)

        # 4. Optional sentence clamping
        if max_sentences is not None and max_sentences > 0:
            sentences = re.split(r"(?<=[.!?])\s+", cleaned)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) > max_sentences:
                cleaned = " ".join(sentences[:max_sentences])

        # 5. Metrics calculation
        burstiness = calculate_burstiness(cleaned)
        sent_count = len([s for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()])

        return HumanizeResult(
            original_text=original,
            humanized_text=cleaned,
            channel=channel,
            tone=tone,
            banned_words_purged=purged,
            burstiness_score=burstiness,
            sentence_count=sent_count,
            was_modified=(cleaned != original),
        )

    def humanize_comment(
        self,
        comment: str,
        tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT,
        max_sentences: int = 3,
    ) -> HumanizeResult:
        return self.transform(
            comment,
            channel=HumanizeChannel.LINKEDIN_COMMENT,
            tone=tone,
            max_sentences=max_sentences,
        )

    def humanize_post(
        self,
        post: str,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> HumanizeResult:
        return self.transform(
            post,
            channel=HumanizeChannel.LINKEDIN_POST,
            tone=tone,
        )
```

Export `HumanizeTransformer` in `content_machine/humanize/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_humanize.py`  
Expected: OK (10 tests passing).

- [ ] **Step 5: Commit**

```bash
git add content_machine/humanize/transformer.py content_machine/humanize/__init__.py tests/test_humanize.py
git commit -m "feat(humanize): implement HumanizeTransformer with two-tier guardrails and fallback"
```

---

### Task 4: Integration with CommentingEngine

**Files:**
- Modify: `content_machine/schemas.py:50-90`
- Modify: `content_machine/commenting/engine.py:150-250`
- Test: `tests/test_commenting.py`

**Interfaces:**
- Consumes: `HumanizeTransformer`, `HumanizeTone` from `content_machine.humanize`.
- Modifies: `GenerateCommentRequest` (adds `humanize: bool = True`, `tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT`).
- Modifies: `CommentRunResponse` (adds `humanized: bool = True`, `humanize_tone: str = "punchy_direct"`, `burstiness_score: float = 0.0`).

- [ ] **Step 1: Write failing tests in `tests/test_commenting.py`**

In `tests/test_commenting.py`, append tests:
```python
    def test_generate_comment_with_humanizer_enabled(self):
        engine = CommentingEngine(cfg=self.cfg, router=self.router, db_conn=self.db_conn)
        res = engine.generate_comment(
            post_content="Valid technical post about message queues and backpressure buffering.",
            angle="insightful",
            humanize=True,
            tone="punchy_direct",
        )
        self.assertTrue(res.humanized)
        self.assertEqual(res.humanize_tone, "punchy_direct")
        self.assertTrue(res.burstiness_score >= 0.0)
        # Sentence limit maintained
        sentences = [s for s in res.final_comment.split(".") if s.strip()]
        self.assertTrue(len(sentences) <= 3)

    def test_generate_comment_with_humanizer_disabled(self):
        engine = CommentingEngine(cfg=self.cfg, router=self.router, db_conn=self.db_conn)
        res = engine.generate_comment(
            post_content="Valid technical post about message queues and backpressure buffering.",
            angle="insightful",
            humanize=False,
        )
        self.assertFalse(res.humanized)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_commenting.py`  
Expected: FAIL (`TypeError: unexpected keyword argument 'humanize'`).

- [ ] **Step 3: Update `GenerateCommentRequest`, `CommentRunResponse`, and `CommentingEngine`**

1. In `content_machine/schemas.py`:
Update `GenerateCommentRequest`:
```python
class GenerateCommentRequest(BaseModel):
    post_content: str = Field(..., min_length=10)
    angle: CommentAngle = CommentAngle.INSIGHTFUL
    perspective_text: Optional[str] = None
    humanize: bool = Field(default=True, description="Apply Humanize Transformer polish pass")
    tone: HumanizeTone = Field(default=HumanizeTone.PUNCHY_DIRECT, description="Target human tone")
```

Update `CommentRunResponse`:
```python
class CommentRunResponse(BaseModel):
    id: str
    angle: CommentAngle
    initial_draft: str
    final_comment: str
    peak_score: float
    verdict: str
    iteration_count: int
    judge_scores: dict[str, float] = Field(default_factory=dict)
    judge_critiques: dict[str, str] = Field(default_factory=dict)
    humanized: bool = Field(default=True)
    humanize_tone: str = Field(default="punchy_direct")
    burstiness_score: float = Field(default=0.0)
```

2. In `content_machine/commenting/engine.py`:
Import `HumanizeTransformer` and `HumanizeTone`.
In `CommentingEngine.__init__`:
```python
from content_machine.humanize import HumanizeTransformer, HumanizeTone
...
self.humanizer = HumanizeTransformer(router=self.router, model=self.writer_model)
```

In `CommentingEngine.generate_comment`:
```python
    def generate_comment(
        self,
        post_content: str,
        angle: str | CommentAngle = "insightful",
        perspective_text: str | None = None,
        humanize: bool = True,
        tone: str | HumanizeTone = HumanizeTone.PUNCHY_DIRECT,
    ) -> CommentRunResponse:
        ...
        final_comment = getattr(council_res, "draft", initial_draft)
        burstiness_score = 0.0
        tone_enum = HumanizeTone(tone) if isinstance(tone, str) else tone

        if humanize:
            h_res = self.humanizer.humanize_comment(final_comment, tone=tone_enum, max_sentences=3)
            final_comment = h_res.humanized_text
            burstiness_score = h_res.burstiness_score
        else:
            final_comment = _sanitize_sentences(final_comment, max_sentences=3)

        # Return CommentRunResponse with humanized, humanize_tone, and burstiness_score
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_commenting.py`  
Expected: OK (all tests passing).

- [ ] **Step 5: Commit**

```bash
git add content_machine/schemas.py content_machine/commenting/engine.py tests/test_commenting.py
git commit -m "feat(commenting): integrate HumanizeTransformer into post-council resolution"
```

---

### Task 5: Standalone API Endpoint, Distribution & CLI

**Files:**
- Modify: `content_machine/distribution/engine.py:120-180`
- Modify: `content_machine/api/app.py:535-620, 765-790`
- Modify: `content_machine/__main__.py:320-380`
- Test: `tests/test_api.py`, `tests/test_distribution.py`, `tests/test_cli.py`

**Interfaces:**
- Exposes: `POST /api/humanize` in `content_machine/api/app.py`.
- Exposes: `python -m content_machine humanize <file.md>` in `content_machine/__main__.py`.
- Modifies: `DistributionEngine.generate_linkedin_post` to take `humanize: bool = True, tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT`.

- [ ] **Step 1: Write failing tests for standalone humanize API, distribution, and CLI**

1. In `tests/test_api.py`:
```python
    def test_post_humanize_endpoint(self):
        client = TestClient(app)
        res = client.post(
            "/api/humanize",
            json={
                "text": "We must delve into this tapestry of microservices. It is a pivotal moment.",
                "channel": "linkedin_post",
                "tone": "punchy_direct",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("humanized_text", data)
        self.assertIn("banned_words_purged", data)
        self.assertEqual(data["tone"], "punchy_direct")
```

2. In `tests/test_distribution.py`:
```python
    def test_generate_linkedin_post_with_humanize(self):
        engine = DistributionEngine(router=self.router, model="qwen3.8-flash")
        post = engine.generate_linkedin_post(
            anchor_post="Post about Kafka backpressure.",
            humanize=True,
            tone="pragmatic_architect",
        )
        self.assertIsInstance(post, str)
        self.assertTrue(len(post) > 0)
```

3. In `tests/test_cli.py`:
```python
    def test_cli_humanize_command(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write("We must delve into this tapestry of queues.")
            temp_path = f.name
        try:
            # Invoking parser
            from content_machine.__main__ import main
            # Test that humanize parser accepts the arguments
            parser = build_parser()
            args = parser.parse_args(["humanize", temp_path, "--tone", "punchy_direct"])
            self.assertEqual(args.path, temp_path)
            self.assertEqual(args.tone, "punchy_direct")
        finally:
            Path(temp_path).unlink(missing_ok=True)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests/test_api.py tests/test_distribution.py tests/test_cli.py`  
Expected: FAIL (missing `/api/humanize` route and `humanize` CLI parser).

- [ ] **Step 3: Implement endpoints, distribution methods, and CLI command**

1. In `content_machine/distribution/engine.py`:
```python
from content_machine.humanize import HumanizeTransformer, HumanizeTone, HumanizeChannel
...
# In DistributionEngine.__init__:
self.humanizer = HumanizeTransformer(router=self.router, model=self.model)

# In generate_linkedin_post:
def generate_linkedin_post(
    self,
    anchor_post: str,
    humanize: bool = True,
    tone: str | HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
) -> str:
    prompt = f"Transform this anchor post into a high-performing LinkedIn post:\n\n{anchor_post.strip()}"
    res = self.router.complete([self.model], prompt=prompt, system=_LINKEDIN_SYSTEM)
    raw = str(res).strip()
    if not humanize:
        return raw
    tone_enum = HumanizeTone(tone) if isinstance(tone, str) else tone
    h_res = self.humanizer.humanize_post(raw, tone=tone_enum)
    return h_res.humanized_text
```

2. In `content_machine/api/app.py`:
Add endpoint:
```python
@app.post("/api/humanize", response_model=HumanizeResult)
def humanize_text_endpoint(req: HumanizeRequest):
    from content_machine.humanize import HumanizeTransformer
    router = _make_router()
    transformer = HumanizeTransformer(router=router)
    return transformer.transform(
        text=req.text,
        channel=req.channel,
        tone=req.tone,
        max_sentences=req.max_sentences,
    )
```

3. In `content_machine/__main__.py`:
Add `humanize` subparser:
```python
humanize_parser = subparsers.add_parser("humanize", help="Transform text to eliminate AI tells and enforce burstiness")
humanize_parser.add_argument("path", help="Path to markdown or text file")
humanize_parser.add_argument("--channel", default="linkedin_post", choices=["linkedin_post", "linkedin_comment", "x_thread", "video_script", "general"])
humanize_parser.add_argument("--tone", default="pragmatic_architect", choices=["punchy_direct", "pragmatic_architect", "conversational_peer"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests/test_api.py tests/test_distribution.py tests/test_cli.py`  
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add content_machine/distribution/engine.py content_machine/api/app.py content_machine/__main__.py tests/test_api.py tests/test_distribution.py tests/test_cli.py
git commit -m "feat(humanize): add POST /api/humanize endpoint, CLI subcommand, and distribution integration"
```

---

### Task 6: Frontend UI Controls (Council, Commenting, Distribution)

**Files:**
- Modify: `ui/src/App.jsx`
- Build & Test: `cd ui; npm run build; cd ..`

**Interfaces:**
- In `CommentingTab`: Humanize toggle (`🪄 Humanize Polish [ON/OFF]`), tone selector pills, and `Humanized ✨` badge with burstiness tooltip.
- In `CouncilTab`: **"🪄 Humanize Peak Draft"** button next to approved draft with side-by-side de-AI preview.
- In `DistributionTab`: Tone selector and toggle for channel derivative generation.

- [ ] **Step 1: Update `ui/src/App.jsx`**

1. In `CommentingTab`:
   - Add state: `const [humanize, setHumanize] = useState(true)` and `const [tone, setTone] = useState('punchy_direct')`.
   - Pass `humanize` and `tone` in payload to `/api/comments/generate`.
   - Display `Humanized ✨ (Burstiness: {result.burstiness_score})` badge in the Editorial Polish card.
2. In `CouncilTab`:
   - Add state: `const [humanizing, setHumanizing] = useState(false)` and `const [humanizedDraft, setHumanizedDraft] = useState(null)`.
   - Add action button `🪄 Humanize Peak Draft` that calls `POST /api/humanize` with `text: peak_draft, channel: 'linkedin_post', tone: 'pragmatic_architect'`.
   - Display side-by-side or drawer view showing purged tells and burstiness score.
3. In `DistributeTab`:
   - Add humanize toggle and tone dropdown for LinkedIn post generation.

- [ ] **Step 2: Run frontend build**

Run: `cd ui; npm run build; cd ..`  
Expected: Vite build succeeds with 0 errors.

- [ ] **Step 3: Commit**

```bash
git add ui/src/App.jsx ui/dist/
git commit -m "feat(ui): add humanize controls, tone selectors, and council de-ai action"
```

---

### Task 7: Full Regression Verification & Codebase Memory Index

**Files:**
- Re-index: `codebase-memory` MCP

- [ ] **Step 1: Run full offline test discovery**

Run: `python -m unittest discover -s tests`  
Expected: All tests passing (185+ green, 0 failures).

- [ ] **Step 2: Re-index codebase memory**

Call `codebase-memory` `index_repository(repo_path="C:/Users/mamat/Github/Content-Machine")`.

- [ ] **Step 3: Live server verification**

Test `POST /api/humanize` on `http://127.0.0.1:8080` via python curl.

- [ ] **Step 4: Commit and finalize**

```bash
git commit --allow-empty -m "chore(humanize): complete verification of humanize transformer subsystem"
```
