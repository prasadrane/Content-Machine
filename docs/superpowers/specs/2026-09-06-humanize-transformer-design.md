# Design Specification: Humanize Transformer Subsystem (Full System Integration)

**Date:** 2026-09-06  
**Status:** Approved  
**Author:** Prasad Rane & Antigravity  

---

## 1. Executive Summary & Objective

Content Machine transforms real engineering signals and lived experiences into high-signal technical content. However, raw LLM outputs (even after 4-judge Writer's Council review) frequently exhibit subtle statistical and rhetorical "AI tells":
- Monotonous sentence length cadence (low burstiness; $\sigma < 2.5$).
- Predictable transition collocations (*"Furthermore"*, *"Moreover"*, *"In today's fast-paced world"*).
- Significance puffery (*"stands as a testament"*, *"marking a pivotal moment"*, *"evolving landscape"*).
- Formulaic punctuation like excessive em-dashes (`—`) and balanced 3-item lists.
- Latinate abstract verbs (*"utilize"*, *"facilitate"*, *"delve"*) instead of concrete mechanical actions (*"use"*, *"run"*, *"dig into"*).

This specification establishes a unified, system-wide **Humanize Transformer** subsystem (`content_machine/humanize/`) executing as a **post-council polish pass** for LinkedIn comments and Council anchor drafts, and as a **post-synthesis transform step** for LinkedIn posts and cross-channel derivatives. It couples a prompt-tier LLM rewrite with a deterministic regex sanitizer to enforce high burstiness, natural contractions, and a strict purge of AI fingerprint vocabulary while strictly preserving author voice invariants.

---

## 2. Empirical Research & The Mechanics of De-AI Craft

Based on peer-reviewed detection benchmarks (e.g., the *Binoculars* cross-perplexity paper from ACL 2024, *Fast-DetectGPT*), stylometric corpora, and Wikipedia’s *Signs of AI Writing* catalog:

### 2.1 Statistical Pillars
1. **High Burstiness (Rhythmic Asymmetry):** Human prose varies wildly in sentence length (e.g. 4 words, then 26 words, then 9 words). The transformer explicitly forces sentence length variance ($\sigma \ge 4.0$), prohibiting consecutive sentences of uniform word counts.
2. **High Localized Perplexity:** Eliminates high-probability cliché tokens in favor of conversational technical vocabulary, contractions (*it's, don't, we've*), and pragmatic qualifiers (*"in practice"*, *"the catch is"*).
3. **Organic Structural Asymmetry:** Breaks rigid 3-part bullet lists and balanced paragraphs. Replaces them with asymmetric blocks (e.g., a blunt 1-line hook, a dense 4-line mechanical explanation, and a 1-line takeaway).

### 2.2 Canonical Blacklist of AI Tells (Deterministic Purge)
- **Significance Inflation:** `stands as a testament`, `serves as a reminder`, `pivotal moment`, `crucial role`, `evolving landscape`, `indelible mark`, `transformative journey`, `focal point`, `deeply rooted`, `setting the stage for`.
- **Banned Vocabulary:** `delve`, `tapestry`, `beacon`, `cornerstone`, `robust`, `vibrant`, `realm`, `foster`, `harness`, `interplay`, `multifaceted`, `paramount`, `game-changer`, `revolutionize`, `seamlessly`, `plethora`, `nuanced tapestry`.
- **Canned Attribution / Meta-coverage:** `independent coverage`, `garnered significant attention`, `widely recognized`, `maintains an active social media presence`.
- **Punctuation Hygiene:** Strips uncontrolled em-dashes (`—`) and converts them into natural colons, commas, or clean hyphens.

### 2.3 Strict Author Invariant Preservation
- **Zero Company Attribution:** Never cites past employers (Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.).
- **No False Corporate Claims:** Never generates claims implying current employment at an organization.
- **Job-Status Agnostic Senior Tone:** Speaks with senior authority, craftsmanship, and pragmatic conviction.

---

## 3. Architecture & Subsystem Design

```
content_machine/
├── humanize/
│   ├── __init__.py           # Exports HumanizeTransformer, HumanizeTone, HumanizeChannel, HumanizeResult
│   ├── constants.py          # Blacklisted AI tells, punctuation regexes, tone system prompts
│   ├── sanitizer.py          # Deterministic scanner: word purge, em-dashes, burstiness metric
│   └── transformer.py        # Core HumanizeTransformer: LLM tone rewrite + sanitizer pass
```

### 3.1 Schemas & Data Types (`content_machine/schemas.py`)

```python
class HumanizeTone(str, Enum):
    PUNCHY_DIRECT = "punchy_direct"          # Short, crisp, zero fluff, high impact
    PRAGMATIC_ARCHITECT = "pragmatic_architect" # Technical depth, trade-off focus, senior peer
    CONVERSATIONAL_PEER = "conversational_peer" # Warm, collegial, accessible, reflective

class HumanizeChannel(str, Enum):
    LINKEDIN_COMMENT = "linkedin_comment"    # Clamped to 2-3 punchy sentences
    LINKEDIN_POST = "linkedin_post"          # Hook + asymmetric narrative spine + takeaway
    X_THREAD = "x_thread"                    # Conversational tweet hooks, no thread clichés
    VIDEO_SCRIPT = "video_script"            # Breathable spoken cadence with visual cues
    GENERAL = "general"                      # Generic technical text de-AI pass

class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=10)
    channel: HumanizeChannel = HumanizeChannel.LINKEDIN_POST
    tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT
    max_sentences: int | None = None

class HumanizeResult(BaseModel):
    original_text: str
    humanized_text: str
    channel: HumanizeChannel
    tone: HumanizeTone
    banned_words_purged: list[str] = Field(default_factory=list)
    burstiness_score: float = Field(0.0, description="Standard deviation of sentence word counts")
    sentence_count: int
    was_modified: bool = True
```

### 3.2 HumanizeTransformer API (`content_machine/humanize/transformer.py`)

```python
class HumanizeTransformer:
    def __init__(
        self,
        router: ModelRouter,
        model: str = "qwen3.8-max",
        voice_guide: str | None = None,
    ):
        self.router = router
        self.model = model
        self.voice_guide = voice_guide or ProfileManager().get_voice_guide_text()

    def transform(
        self,
        text: str,
        channel: HumanizeChannel = HumanizeChannel.LINKEDIN_POST,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
        max_sentences: int | None = None,
    ) -> HumanizeResult:
        """Core multi-channel humanization engine with two-tier guardrails."""
        ...

    def humanize_comment(
        self,
        comment: str,
        tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT,
        max_sentences: int = 3,
    ) -> HumanizeResult:
        return self.transform(comment, channel=HumanizeChannel.LINKEDIN_COMMENT, tone=tone, max_sentences=max_sentences)

    def humanize_post(
        self,
        post: str,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> HumanizeResult:
        return self.transform(post, channel=HumanizeChannel.LINKEDIN_POST, tone=tone)
```

### 3.3 Deterministic Sanitizer (`content_machine/humanize/sanitizer.py`)

- **`sanitize_text(text: str) -> tuple[str, list[str]]`**:
  - Replaces em-dashes (`—`) with commas, colons, or clean hyphens.
  - Scans for banned AI words using case-insensitive `\b` word boundaries; replaces or strips them.
  - Asserts author invariants (zero company mentions, no fake corporate claims).
- **`calculate_burstiness(text: str) -> float`**:
  - Splits text into sentences, tokenizes words, and computes standard deviation:
    $$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (w_i - \bar{w})^2}$$
  - Returns burstiness score (target $\ge 4.0$ for multi-sentence posts).

---

## 4. Pipeline Hook Points & System Integration

### 4.1 LinkedIn Comments (`content_machine/commenting/engine.py`)
- `GenerateCommentRequest` accepts `humanize: bool = True` and `tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT`.
- In `generate_comment()`:
  - Takes peak draft from Council loop.
  - If `humanize=True`, invokes `HumanizeTransformer.humanize_comment()`.
  - Enforces sentence clamping (2–3 sentences max) and saves to SQLite `comments`.

### 4.2 Writer's Council & Anchor Posts (`content_machine/council/` & `api/app.py`)
- Exposes `POST /api/humanize` standalone endpoint.
- In the Council Tab UI: A dedicated **"🪄 Humanize Peak Draft"** button appears next to the approved Council draft, allowing the author to apply humanization to the master anchor post with 1 click.

### 4.3 Derivative Channels (`content_machine/distribution/engine.py`)
- `DistributionEngine` accepts `humanize: bool = True` and `tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT`.
- `generate_linkedin_post`, `generate_x_thread`, and `generate_video_script_short` pass their outputs through `HumanizeTransformer.transform(..., channel=channel)`.

### 4.4 Governed Lessons Synergy (`content_machine/lessons/`)
- When the human edits or approves a humanized draft, purged tells are recorded.
- Recurring patterns can be proposed into `03_content-lessons.md`.

---

## 5. UI Controls Across the Application (`ui/src/App.jsx`)

1. **Commenting Tab**:
   - Clean toggle pill: `🪄 Humanize Polish [ON / OFF]` (default: ON).
   - Tone selector pills: `⚡ Punchy & Direct` | `🏛️ Pragmatic Architect` | `☕ Conversational Peer`.
   - Editorial Polish Card: displays `Humanized ✨` badge with burstiness score tooltip.
2. **Council Tab**:
   - Added **"🪄 Humanize Peak Draft"** action button in Council Deliberation view.
   - Shows before/after side-by-side view with purged words highlighted.
3. **Distribution Tab**:
   - Tone selector and Humanize toggle for LinkedIn posts, X threads, and Video scripts.

---

## 6. Testing & Verification Strategy (Strict TDD)

1. **`tests/test_humanize.py`**:
   - Sanitizer tests: 35+ banned words purge, em-dash normalization, burstiness scoring, invariant checking.
   - Transformer tests: mock router calls for comments (2-3 sentences max), posts, X threads, video scripts across all 3 tones.
   - Fallback tests: graceful degradation to deterministic sanitizer if router call fails.
2. **`tests/test_commenting.py`**:
   - End-to-end comment generation with `humanize=True` and `humanize=False`.
3. **`tests/test_distribution.py`**:
   - LinkedIn post, X thread, and video script generation with `humanize=True`.
4. **`tests/test_api.py`**:
   - `POST /api/humanize` endpoint.
   - `POST /api/comments/generate` with `humanize` and `tone`.
   - `POST /api/distribute/run` with `humanize` and `tone`.
5. **Frontend & Regression**:
   - `npm run build` in `ui/` (0 errors).
   - `python -m unittest discover -s tests` (100% passing).
