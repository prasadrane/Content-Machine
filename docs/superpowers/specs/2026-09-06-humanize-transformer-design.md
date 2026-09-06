# Design Specification: Humanize Transformer Subsystem

**Date:** 2026-09-06  
**Status:** Approved  
**Author:** Prasad Rane & Antigravity  

---

## 1. Executive Summary & Objective

Content Machine generates high-signal engineering thoughts and LinkedIn commentary grounded in the author's real lived experience and voice profile. However, raw LLM outputs (even after 4-judge Writer's Council review) frequently exhibit subtle statistical and rhetorical "AI tells":
- Monotonous sentence length cadence (low burstiness).
- Predictable transition markers (*"Furthermore"*, *"Moreover"*, *"In today's fast-paced world"*).
- Unearned significance puffery (*"stands as a testament"*, *"marking a pivotal moment"*, *"evolving landscape"*).
- Formulaic punctuation like excessive em-dashes (`—`) and balanced 3-item lists.

This specification establishes a dedicated **Humanize Transformer** subsystem (`content_machine/humanize/`) executing as a **post-council polish pass** for LinkedIn comments and a **post-synthesis transform step** for LinkedIn posts. It couples a prompt-tier LLM rewrite with a deterministic regex sanitizer to enforce high burstiness, natural contractions, and a strict purge of AI fingerprint vocabulary while preserving author voice invariants.

---

## 2. Core Linguistic Principles (The "Humanize" Skill)

Based on empirical LLM detector research, prompt engineering benchmarks, and Wikipedia's *Signs of AI Writing* catalog:

1. **High Burstiness (Rhythmic Asymmetry):** Human prose varies wildly in sentence length (e.g. 4 words, then 26 words, then 9 words). The transformer explicitly forces sentence length variance, prohibiting consecutive sentences of uniform word counts.
2. **High Perplexity & Conversational Nuance:** Eliminates high-probability cliché tokens in favor of conversational technical vocabulary, contractions (*it's, don't, we've*), and pragmatic qualifiers.
3. **Deterministic Banned Vocabulary Purge:** Zero tolerance for AI tells:
   - *Puffery:* `stands as a testament`, `serves as a reminder`, `pivotal moment`, `crucial role`, `evolving landscape`, `indelible mark`, `transformative journey`.
   - *Words:* `delve`, `tapestry`, `beacon`, `cornerstone`, `robust`, `vibrant`, `realm`, `foster`, `harness`, `interplay`, `multifaceted`, `paramount`, `game-changer`.
4. **Punctuation Hygiene:** Strips uncontrolled em-dashes (`—`) and converts them into natural colons, commas, or parentheses.
5. **Strict Author Invariant Preservation:** Never leaks prohibited company names (Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.), never claims corporate employment, and maintains senior practitioner conviction.

---

## 3. Architecture & Subsystem Design

```
content_machine/
├── humanize/
│   ├── __init__.py           # Exports HumanizeTransformer, HumanizeTone, HumanizeResult
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

class HumanizeResult(BaseModel):
    original_text: str
    humanized_text: str
    tone: HumanizeTone
    banned_words_purged: list[str] = Field(default_factory=list)
    burstiness_score: float = Field(0.0, description="Standard deviation of sentence word counts")
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

    def humanize_comment(
        self,
        comment: str,
        tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT,
        max_sentences: int = 3,
    ) -> HumanizeResult:
        """Humanize a LinkedIn comment, enforcing 2-3 sentence limit and burstiness."""
        ...

    def humanize_post(
        self,
        post: str,
        tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT,
    ) -> HumanizeResult:
        """Humanize a LinkedIn long-form post, breaking robotic paragraph/sentence symmetry."""
        ...
```

### 3.3 Deterministic Sanitizer (`content_machine/humanize/sanitizer.py`)

- **`sanitize_text(text: str) -> tuple[str, list[str]]`**:
  - Replaces em-dashes (`—`) with commas, colons, or standard hyphens.
  - Scans for banned AI words using case-insensitive `\b` word boundaries; replaces or strips them.
  - Asserts author invariants (zero company mentions, no fake corporate claims).
- **`calculate_burstiness(text: str) -> float`**:
  - Splits text into sentences, tokenizes words, and computes standard deviation:
    $$\sigma = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (w_i - \bar{w})^2}$$
  - Returns burstiness score (target $\ge 3.5$ for multi-sentence posts).

---

## 4. Pipeline Hook Points

### 4.1 LinkedIn Comments (`content_machine/commenting/engine.py`)

1. `GenerateCommentRequest` updated with:
   - `humanize: bool = True`
   - `tone: HumanizeTone = HumanizeTone.PUNCHY_DIRECT`
2. `CommentingEngine.generate_comment()`:
   - Evaluates initial draft through Writer's Council loop (up to 2 iterations).
   - If `humanize=True`: passes peak council draft to `HumanizeTransformer.humanize_comment()`.
   - Clamps final output to at most 3 sentences.
   - Saves final comment and metadata to SQLite `comments` table.
3. `CommentRunResponse`: includes `humanized: bool`, `humanize_tone: str`, `burstiness_score: float`.

### 4.2 LinkedIn Posts (`content_machine/distribution/engine.py`)

1. `generate_linkedin_post(anchor_post: str, humanize: bool = True, tone: HumanizeTone = HumanizeTone.PRAGMATIC_ARCHITECT) -> str`:
   - Synthesizes LinkedIn hook, spine, and takeaway.
   - If `humanize=True`: applies `HumanizeTransformer.humanize_post(..., tone=tone)`.
   - Returns polished text.

---

## 5. UI Controls (`ui/src/App.jsx`)

1. **`CommentingTab`**:
   - Clean toggle pill: `🪄 Humanize Polish [ON / OFF]` (default: ON).
   - Tone selector pills: `⚡ Punchy & Direct` | `🏛️ Pragmatic Architect` | `☕ Conversational Peer`.
   - Editorial Polish Card: displays `Humanized ✨` badge with tooltip showing burstiness score.
2. **`DistributionTab`**:
   - LinkedIn Post card includes identical toggle and tone selector before generation.

---

## 6. Testing & Verification Strategy (Strict TDD)

1. **`tests/test_humanize.py`**:
   - Sanitizer tests: banned words purge, em-dash normalization, burstiness scoring, invariant checking.
   - Transformer tests: mock router calls for comments (2-3 sentences max) and posts across all 3 tones.
   - Fallback tests: graceful degradation to sanitizer on router error.
2. **`tests/test_commenting.py`**:
   - End-to-end comment generation with `humanize=True` and `humanize=False`.
3. **`tests/test_distribution.py`**:
   - LinkedIn post generation with `humanize=True` and `humanize=False`.
4. **`tests/test_api.py`**:
   - API endpoints accepting `humanize` and `tone`.
5. **Frontend & Regression**:
   - `npm run build` in `ui/` (0 errors).
   - `python -m unittest discover -s tests` (100% passing).
