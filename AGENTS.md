# AGENTS.md — Content Machine Guide for Autonomous Agents

This document is the primary operational guide for AI agents working in this repository. Follow the conventions, protocols, and architectural invariants documented below.

---

## 1. System Overview & Core Philosophy

**Content Machine** is a local-first, multi-model AI editorial engine designed to transform real engineering signals and lived experiences into high-signal content (LinkedIn posts, X/Twitter threads, short-form video scripts, newsletter digests).

### Core Invariant
> **AI as extraction, synthesis, and editorial engine anchored in lived human experience; NEVER an unconstrained text generator.**
> Never hallucinate metrics, personal anecdotes, or technical facts. All output must be strictly grounded in raw transcripts, connector items, or approved drafts.

---

## 2. Architecture & Subsystems Map

The codebase is organized under `content_machine/` with companion UI, tests, and frozen knowledge:

```
Content-Machine/
├── AGENTS.md                     # Agent guide & operational instructions (this file)
├── NOTES.md                      # Chronological research, spike logs, and build log
├── "Content Machine Plan v2.md"  # Full architectural specification & evidence register
├── config.json                   # Router routes, model mappings, thresholds, RSS feeds
├── requirements.txt              # Backend dependencies
├── content_machine/              # Core Python package
│   ├── __main__.py               # CLI entrypoint (oracle, council, transcribe, lessons, distribute, serve)
│   ├── config.py                 # Configuration loader (Pydantic-based)
│   ├── schemas.py                # Pydantic schemas (scores, council, rules, items)
│   ├── api/
│   │   └── app.py                # FastAPI app (REST API + static file SPA fallback)
│   ├── asr/                      # Subsystem 2: Audio Speech Recognition
│   │   ├── batch.py              # faster-whisper int8 batch transcription
│   │   ├── live.py               # whisper.cpp streaming monitor callback
│   │   └── transcript.py         # Transcript formatting & validation
│   ├── connectors/               # Subsystem 1: Input Ingestion
│   │   ├── base.py               # BaseConnector, ConnectorItem, ConnectorResult
│   │   ├── rss.py                # RSS/Atom connector with ETag/If-None-Match caching
│   │   ├── github.py             # GitHub closed issues/PRs connector
│   │   └── linkedin.py           # LinkedIn Voyager API session connector
│   ├── council/                  # Subsystem 4: Writer's Council
│   │   ├── loop.py               # Council iteration loop, quorum, revision, break-with-best
│   │   ├── obfuscate.py          # Authorship & model-fingerprint stripping
│   │   └── normalize.py          # Per-judge historical z-score normalization
│   ├── distribution/             # Subsystem 6: Derivative Channel Formats
│   │   └── engine.py             # X threads, short-form video scripts, newsletters
│   ├── lessons/                  # Subsystem 5: Governed Lessons Store
│   │   ├── differ.py             # Diff analysis between draft and published post
│   │   └── store.py              # Human approval gate, cosine embedding conflict checks
│   ├── oracle/                   # Subsystem 1: Idea Scoring & Ranking
│   │   ├── scorer.py             # N-sample aggregated idea scoring
│   │   └── oracle.py             # Oracle orchestrator (connectors -> dedup -> score)
│   ├── router/                   # LLM Routing Foundation
│   │   ├── base.py               # ModelRouter with 2-layer failover (provider + model)
│   │   └── messages_adapter.py   # Anthropic Messages protocol adapter & retry logic
│   └── storage/                  # Local State & SQLite
│       ├── paths.py              # Filesystem paths under CONTENT_MACHINE_HOME
│       └── db.py                 # SQLite connection, migrations, FK/schema enforcement
├── council/
│   └── rubric_v1.md              # Frozen versioned rubric for Writer's Council
├── knowledge/                    # Voice & style seeds copied to user storage
│   ├── 01_style-guide.md
│   ├── 02_voice-guide.md
│   └── 03_content-lessons.md
├── tests/                        # Full test suite (129+ tests, 100% offline-capable)
└── ui/                           # Minimalist React + Vite + Tailwind CSS SPA
    ├── src/                      # App.jsx, components, style tokens
    ├── package.json
    └── vite.config.js
```

---

## 3. Critical Environment Realities & Gotchas

Be aware of the local deployment realities before running code or suggesting modifications:

### 1. Model Gateway & Auth
- **Route**: Model requests route through a custom relay (`token_plan_relay`) implementing the Anthropic Messages protocol at `/apps/anthropic`.
- **Authentication Header**: Uses Bearer token via `ANTHROPIC_AUTH_TOKEN` (read from env or config). `ANTHROPIC_API_KEY` in env is often a placeholder and will fail with 401 if passed as `x-api-key`.
- **Allowed Models**: Only specific models are active on the relay:
  - Writer: `qwen3.8-max`
  - Council Judges: `qwen3.8-max` (Perell, Housel), `qwen3.8-flash` (Puri, Slop Allergist)
  - Scanner: `qwen3.8-flash`
  - *Do NOT route to*: `qwen3.6-plus` (403), `qwen3.6-max`, `qwen3.7-plus`, `qwen3.6-flash`, or `qwen3.8-opensource`.
- **Structured Outputs**:
  - `qwen3.6-flash` cannot use `messages.parse` / `response_format=json_object` (returns HTTP 400). `MessagesAdapter` automatically degrades to explicit JSON prompting and local Pydantic validation.
  - Pydantic validation is mandatory on all outputs client-side; models do not enforce numeric bounds (e.g. `le=10`) natively.

### 2. Hardware & Platform
- **OS**: Windows (PowerShell / cmd).
- **Console Encoding**: When printing to stdout, avoid unhandled raw Unicode/emojis that could cause `UnicodeEncodeError` on Windows consoles. Use safe ASCII fallbacks or encoding handlers.
- **Hardware**: CPU-only Intel Core i7 (Iris Xe, no CUDA GPU).
  - ASR must use `faster-whisper` with `compute_type="int8"` or `whisper.cpp`.
  - Do NOT introduce GPU-only libraries like NeMo Parakeet unless running in an external CUDA environment.

### 3. State & Storage Isolation
- Production data is stored in `~/.content_machine/` (`CONTENT_MACHINE_HOME`).
- **In tests**, always isolate storage by setting `os.environ["CONTENT_MACHINE_HOME"] = tempfile.mkdtemp(...)` before importing `content_machine.storage` modules.

---

## 4. Development Workflow & TDD Mandate

### Test-Driven Development (TDD)
- **Every new feature, bug fix, or refactor must follow TDD**:
  1. Write failing tests in `tests/test_<subsystem>.py`.
  2. Implement the minimal code in `content_machine/<subsystem>/`.
  3. Run the test suite and verify all tests pass.
  4. Refactor if necessary while maintaining green tests.

### Running Tests
All unit tests run offline without network access or live API calls:
```powershell
# Run entire test suite (fast, <1s)
python -m unittest discover -s tests

# Run a specific subsystem test
python tests/test_storage.py
python tests/test_router.py
python tests/test_council.py
python tests/test_connectors.py
python tests/test_oracle.py
python tests/test_asr.py
python tests/test_lessons.py
python tests/test_api.py
python tests/test_distribution.py
python tests/test_linkedin_connector.py
python tests/test_cli.py
```

### Live Smoke Verification
To run the live council smoke test with actual LLM calls (requires active relay & credentials):
```powershell
$env:CONTENT_MACHINE_LIVE="1"
python tests/live_council_smoke.py
```

---

## 5. Running & Interacting with the Application

### 1. Web Application & API
```powershell
# Start FastAPI backend + bundled React UI (default port 8080)
python -m content_machine serve --port 8080

# Browser access
http://127.0.0.1:8080
```

### 2. Frontend Development (Vite Dev Server)
```powershell
cd ui
npm install
npm run dev
# Proxy is configured to forward /api requests to http://127.0.0.1:8080
```

### 3. Rebuilding Frontend
```powershell
cd ui
npm run build
# Compiles SPA to ui/dist, which is served statically by FastAPI
```

### 4. CLI Subcommands
```powershell
# Ingest and score ideas from developer RSS feeds
python -m content_machine oracle --rss https://dev.to/feed --no-persist
python -m content_machine oracle --all --fetch-only

# Ingest GitHub closed issues/PRs
python -m content_machine oracle --github owner/repo

# Ingest LinkedIn feed/profile updates (requires session cookie)
python -m content_machine oracle --linkedin feed --li-at "<cookie>"

# Run Writer's Council on a draft
python -m content_machine council path/to/draft.md

# Transcribe audio file (CPU-int8)
python -m content_machine transcribe recording.wav --model small --save transcript.md

# Governed lessons store management
python -m content_machine lessons diff draft_v1.md published_final.md
python -m content_machine lessons list
python -m content_machine lessons approve <rule_id>
python -m content_machine lessons reject <rule_id>

# Cross-channel distribution engine
python -m content_machine distribute path/to/post.md --slug my-post
```

---

## 6. Subsystem Architectural Invariants

1. **The Oracle**:
   - Never rely on a single score pass. Always use N-sample median aggregation (`idea_samples: 3`).
   - RSS connector must use ETag / If-None-Match headers to prevent duplicate pulls.
2. **Writer's Council**:
   - Authorship must be obfuscated before passing drafts to judges (strips model tags, author hints).
   - Rubric format (`council/rubric_v1.md`) is frozen; do not modify rubric markdown dynamically during execution.
   - Raw scores are z-normalized against historical per-judge distribution once `min_samples >= 30`.
   - Never show a judge its prior scores on the same draft.
3. **Governed Lessons Store**:
   - `03_content-lessons.md` must **never** be auto-appended directly without a human approval gate.
   - Proposed rules must be checked for semantic duplication/conflict using cosine similarity over embeddings.
   - Hard cap of active rules (default: 50) is strictly enforced to prevent context bloat and rule drift.
4. **Distribution Engine**:
   - All derivative assets (X threads, video scripts, newsletters) must be strictly grounded in the approved anchor post.
   - Scripts must include production visual markers (`[Visual Cue]`, `[Camera Zoom]`, `[Pause]`).
5. **Slop Suppression**:
   - Negative constraints live in `02_voice-guide.md`.
   - Surface regex lints are weak pre-filters; primary quality control is the human approval gate.

---

## 7. Protocol for Autonomous Agents

Before beginning work:
1. **Codebase Orientation**: Query `codebase-memory` MCP (`list_projects`, `get_architecture`) to inspect the current graph.
2. **Consult History**: Check `NOTES.md` for recent build states, verified findings, or known roadblocks.
3. **Strict TDD**: Write or update tests in `tests/` before modifying implementation code.
4. **Preserve Documentation**: Keep comments, docstrings, and plan alignments intact.
5. **Regression Verification**: Run `python -m unittest discover -s tests` and verify 0 failures before reporting task completion.
