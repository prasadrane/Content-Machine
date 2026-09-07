# Content Machine

> Local-first, multi-model AI editorial engine transforming real engineering signals and lived experiences into high-signal content.

Content Machine is built around a single non-negotiable invariant:
**AI as extraction, synthesis, and editorial council anchored in authentic human experience — never an unconstrained text generator.**

---

## Subsystems Map

```
Content-Machine/
├── content_machine/
│   ├── oracle/          # Subsystem 1: Signal Ingestion & N-sample Scorer (RSS, GitHub, LinkedIn)
│   ├── asr/             # Subsystem 2: Voice Intake & CPU-int8 faster-whisper Transcription
│   ├── interview/       # Subsystem 3: Deep Technical Interview & Thesis Synthesis
│   ├── council/         # Subsystem 4: Writer's Council Multi-Model Deliberation Loop
│   ├── humanize/        # Subsystem 5: Two-tier Anti-AI Transformer & Burstiness Guardrails
│   ├── commenting/      # Subsystem 6: Grounded LinkedIn Comment Generation & History
│   ├── distribution/    # Subsystem 7: Multi-Channel Cross-Distribution (X threads, Video scripts)
│   ├── lessons/         # Subsystem 8: Governed Editorial Rule Store & Diff Extractor
│   ├── profile/         # Subsystem 9: Author Persona, Domains & Negative Constraints
│   ├── router/          # LLM Model Gateway & Anthropic Protocol Messages Adapter
│   ├── storage/         # SQLite State, Audit Log, Migrations & Local Paths
│   └── api/             # FastAPI REST Server & Static SPA Serving
├── ui/                  # Modular React + Vite + Tailwind CSS Editorial Cockpit
└── tests/               # 100% Offline-Capable Test Suite (220 backend, 67 frontend)
```

---

## Core Capabilities

- **The Oracle**: Multi-feed connector (RSS/Atom with ETag caching, GitHub PRs/issues, LinkedIn Voyager) with 3-sample median consensus scoring against technical relevance and novelty.
- **Author Voice Grounding**: Codified author persona (Prasad Rane) and hard invariants enforced across all generation:
  1. *Zero Company Attribution* (never cite previous employers).
  2. *No False Corporate Employment* (no "my company today" or "our team at work").
  3. *Job-Status Agnostic Senior Tone* (speaks with architectural authority).
  4. *Current Operational Reality* (hands-on AI systems builder).
  5. *Zero Generic Praise & Emojis* (straight into the technical crux).
- **Writer's Council**: 4-judge parallel review board running rubric-grounded evaluations:
  - **David Perell** (`qwen3.8-max`): Narrative arc, personal stake, hook velocity.
  - **Sahil Puri** (`qwen3.8-flash`): Directness, punchiness, visual rhythm.
  - **Morgan Housel** (`qwen3.8-max`): Substantive depth, empirical grounding, timelessness.
  - **Slop Allergist** (`qwen3.8-flash`): Lexical/syntactic purity, purging AI tells.
- **Humanize Transformer**: Two-tier guardrail system combining an LLM generative rewrite pass with a deterministic sanitizer:
  - Purges 35+ canonical AI tells (*delve, tapestry, pivotal, testament, cornerstone, robust, etc.*) and multi-word puffery.
  - Refined em-dash normalization that preserves CLI flags (`--flag`) and Markdown dividers (`---`).
  - Statistical burstiness enforcement ($\sigma \ge 3.5$) across sentence word lengths.
- **LinkedIn Commenting Tool**: Synthesizes 2–3 sentence senior comments from 3 strategic angles (`Insightful`, `Contrarian`, `Question`) with voice dictation and post-council polish.
- **Cross-Channel Distribution**: Transforms approved anchor posts into platform-native X/Twitter threads, spoken short-form video scripts (with `[Visual Cue]` and `[Camera Zoom]` markers), and newsletter digests.
- **Governed Lessons Store**: Human-approved negative constraint repository with diff analysis and vector deduplication.

---

## Quickstart

### Prerequisites
- Python 3.10+
- Node.js 18+
- Intel/AMD CPU or Apple Silicon (no GPU required; ASR runs CPU-int8)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/prasadrane/Content-Machine.git
cd Content-Machine

# 2. Setup Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Build UI
cd ui
npm install
npm run build
cd ..
```

### Configuration
Set your relay credentials in environment or `.env`:
```bash
export ANTHROPIC_BASE_URL="http://your-relay-host:port/apps/anthropic"
export ANTHROPIC_AUTH_TOKEN="your-bearer-token"
```

### Launch Server

```bash
python -m content_machine serve --port 8080
```
Open **`http://localhost:8080`** in your browser.

---

## CLI Usage

```bash
# Score ideas from developer RSS feeds
python -m content_machine oracle --rss https://dev.to/feed

# Run Writer's Council evaluation on a draft post
python -m content_machine council draft.md

# Generate a grounded LinkedIn comment
python -m content_machine comment --post "Kafka partition rebalance issues..." --angle insightful

# De-AI and humanize any draft text
python -m content_machine humanize draft.txt --channel linkedin_post --tone pragmatic_architect

# Extract editorial rules from draft vs published diff
python -m content_machine lessons diff draft_v1.md published.md

# Synthesize cross-channel derivative assets
python -m content_machine distribute post.md --slug my-post
```

---

## Quality & Test Suite

The entire test suite is 100% offline-capable and requires zero live network access:

```bash
# Run backend test discovery (220 tests, <2s)
python -m unittest discover -s tests

# Run frontend Vitest suite (22 suites, 67 tests)
cd ui
npm test

# Build production frontend bundle
npm run build
```

---

## License
MIT
