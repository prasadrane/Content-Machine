# Architectural Decision Records

This repository has no formal ADR history. Several important architectural
decisions are visible in the implementation, but their historical rationale is
not documented. This directory captures those decisions as **candidates**.

Status convention: every entry starts as **Candidate**. An entry becomes
**Accepted** only when the project owner confirms (or corrects) its rationale.
Nothing here should be read as recorded history until that happens.

When formalizing, keep records minimal — three sections suffice:
**Context** (problem and constraints), **Decision** (what was chosen),
**Consequences** (trade-offs accepted). "Observed implementation" below is
derived from reading the code; "Unresolved rationale" lists what the code
cannot tell us.

## Candidate ADRs

### 1. Local-first SQLite state under CONTENT_MACHINE_HOME

Status: Candidate (owner confirmation required)

Observed implementation: All persistent state lives in a SQLite database and a
small file tree under a single home directory, resolved from the
`CONTENT_MACHINE_HOME` environment variable and defaulting to
`~/.content_machine`. The schema (spikes, transcripts, iterations,
judge_score_history, lessons, audit_log, feed caches, comments) is created
idempotently with hand-rolled `ALTER TABLE` column migrations rather than a
migration framework. No hosted database or ORM is used.

Evidence: `content_machine/storage/db.py`, `content_machine/storage/paths.py`
(`home_root`, `db_path`, `init_db`), `content_machine/bootstrap.py` (`make_db`).

Unresolved rationale:
- Was multi-user or hosted deployment ever considered and rejected, or was the
  single-operator model a premise from the start?
- Why in-code `ALTER TABLE` migrations instead of a migration tool, and is
  there an expected point where that stops scaling?

### 2. Repo `knowledge/*.md` seeds are authoritative; sha256 sync to runtime copies

Status: Candidate (owner confirmation required)

Observed implementation: Style/voice/lessons markdown files in the repo's
`knowledge/` directory are treated as the source of truth and synced by
content-hash into `~/.content_machine/knowledge/`, the copies that prompts
actually read. `sync_seed` compares sha256 of seed vs. runtime file, backs the
runtime copy up as `<name>.bak`, and overwrites on drift; the docstring notes
an earlier size-based heuristic silently kept stale copies. The knowledge
provider re-syncs on every resolution, and sync is skipped entirely under
`DEMO_MODE=1` so synthetic demo persona files are never overwritten by real
seeds.

Evidence: `content_machine/storage/paths.py` (`sync_seed`, `ensure_tree`),
`content_machine/knowledge/provider.py` (`_resolve_file`), `knowledge/`
directory contents.

Unresolved rationale:
- Is the runtime copy meant to be user-editable at all, given every drift is
  reverted to the seed on next read (with only a `.bak` preserved)?
- What triggered replacing the size heuristic with sha256 — a specific stale-
  prompt incident?

### 3. N-sample median consensus for idea scoring

Status: Candidate (owner confirmation required)

Observed implementation: Instead of gating on a single LLM scoring call,
`IdeaScorer` issues `n_samples` (default 3, config `thresholds.idea_samples`)
independent scanner calls in parallel threads and takes the `statistics.median`
of the composite scores. The docstring cites measured unreliability of single
samples ("alpha 0.26-0.79"). Verdict bands: pass at median >= 8.0, review in
the 0.5-wide band below the gate, reject below it. Results and per-sample
scores are persisted to `spikes.scores_json`; already-seen URLs rehydrate from
cache without LLM calls.

Evidence: `content_machine/oracle/scorer.py`, `content_machine/oracle/oracle.py`
(`_find_cached_spike`, `_persist`), `content_machine/config.py`
(`ThresholdsConfig.idea_gate/idea_margin/idea_samples`).

Unresolved rationale:
- Where does the alpha 0.26-0.79 figure come from — an internal calibration
  experiment whose data is not in the repo?
- Was N=3 vs. 5 or temp-0 single-call + margin band actually compared (the
  docstring mentions both options)?

### 4. Frozen rubric v1, four-judge council, raw gate with z-normalization fallback

Status: Candidate (owner confirmation required)

Observed implementation: Draft evaluation runs a parallel independent-scoring
council (no judge debate, `MIN_QUORUM = 3`) of four named slots — perell, puri,
housel, slop_allergist — against `council/rubric_v1.md`, marked "FROZEN"; new
rubric versions get a new file and never mix within one rewrite loop. The pass
gate compares the mean raw composite against `council_min_score_raw = 9.0`,
with a `council_margin = 0.3` band below the gate triggering one resample
averaged with the first pass, up to `council_max_iterations = 3`. Per-judge
z-normalization exists (`normalization_stats` requires
`normalization_min_samples = 30` history rows per judge slot/model/dimension)
but the default gate mode is deliberately `"raw"`: the code comments state that
switching to the z-gate at `council_min_score_z = 0.0` would silently drop the
pass bar to about the 50th percentile once history accumulates, so normalized
composites are recorded for monitoring until the owner opts in after
calibration.

Evidence: `content_machine/council/loop.py`, `content_machine/council/gate.py`,
`content_machine/council/normalize.py`, `content_machine/council/rubric_v1.md`,
`content_machine/config.py`, `config.json`.

Unresolved rationale:
- Why a 9.0 absolute gate on a 10-point scale — is that a deliberate "only
  exceptional ships" rule, and what false-pass rate motivated calibration?
- Are the four judge personas (perell/puri/housel/slop_allergist) meaningful
  evaluation axes or just memorable slot names?
- What calibration would justify switching `council_gate_mode` to normalized?

### 5. Two-protocol model router with ProviderError/ModelError failover split

Status: Candidate (owner confirmation required)

Observed implementation: `ModelRouter` tries each model in a layer, and per
model each configured route, with a two-layer error contract: `ProviderError`
(outage, rate limit, network) advances to the next route for the same model;
`ModelError` (context overflow, refusal, schema-invalid output) breaks to the
next model. Routes speak two protocols today — Anthropic-style `messages`
(via the `anthropic` SDK) and native `gemini`; `openai` is noted as future.
A rolling 300-second health window records per-route/model latency and success,
and routes whose p50 latency exceeds `preferred_max_latency_s` (90.0) are
skipped when alternatives exist.

Evidence: `content_machine/router/base.py`,
`content_machine/router/messages_adapter.py`, `content_machine/bootstrap.py`
(`make_router`), `content_machine/config.py` (`RouteConfig.protocol`).

Unresolved rationale:
- Was the Provider/Model split derived from an incident (e.g. refusals being
  retried across routes wastefully), or designed a priori?
- Why treat unexpected exceptions as model-level (break) rather than
  provider-level?

### 6. Native REST Gemini adapter with httpx instead of the official SDK

Status: Candidate (owner confirmation required)

Observed implementation: Gemini support is a hand-written adapter over the
`generateContent` REST endpoint using `httpx` only — no Google SDK
dependency. It maps Pydantic schemas to Gemini `responseSchema` (an OpenAPI
type subset), classifies HTTP outcomes into the router's error split
(429/5xx and transport errors -> `ProviderError`; other non-200 and
schema-invalid JSON -> `ModelError`), and mirrors `MessagesAdapter`'s call
shape so router failover is unchanged.

Evidence: `content_machine/router/gemini.py`, `requirements.txt`
(httpx present, no Google SDK).

Unresolved rationale:
- Was "zero new dependencies" the deciding factor, or were SDK behavior
  problems (auth, streaming, structured-output gaps) observed?
- Is the adapter's minimal feature surface (non-streaming, no
  function-calling) a deliberate scope choice?

### 7. Two-tier humanize: LLM rewrite plus deterministic sanitizer

Status: Candidate (owner confirmation required)

Observed implementation: Humanization is a prompt tier (tone system prompts +
channel constraints instructing the model to purge AI tells) followed by a
deterministic sanitizer. `sanitize_text` normalizes em-dashes to commas
(`EM_DASH_PATTERN` substitution), then replaces banned AI words
(`BANNED_AI_WORDS`, ~40 entries incl. delve/tapestry/robust/seamlessly) and
banned phrases (`BANNED_AI_PHRASES`, e.g. "stands as a testament") with
case-preserving replacements, and purges any remaining banned words. A
`check_author_invariants` pass flags prohibited employer mentions and false
corporate-employment claims as warnings. Burstiness is *measured* as the
standard deviation of sentence word counts and stored on results/rows
(`schemas.py`, comments table) — no enforcement threshold was found in the
pipeline; variation is prompted, not gated.

Evidence: `content_machine/humanize/transformer.py`,
`content_machine/humanize/sanitizer.py`, `content_machine/humanize/constants.py`,
`content_machine/schemas.py`.

Unresolved rationale:
- Em-dash purge vs. preserve: the sanitizer actively removes em-dashes — was
  that a response to a specific detection tell, and is preservation ever wanted?
- Why record burstiness without acting on it (a threshold/re-rewrite loop) —
  planned but unbuilt, or monitoring only?
- How was the banned-word list curated, and who maintains it?

### 8. DEMO_MODE config overrides plus synthetic seed for the public demo

Status: Candidate (owner confirmation required)

Observed implementation: Rather than a separate demo codebase, the same app
runs in demo mode. The Vercel entrypoint sets `DEMO_MODE=1` and
`CONTENT_MACHINE_HOME=/tmp/cm`; `_apply_demo_overrides` then rewrites the
route table to a single Gemini flash route (`gemini-2.5-flash`) when
`GEMINI_API_KEY` is present, and `demo_seed.seed_demo` installs a fully
synthetic dataset — fictional spikes with synthetic scores, a "John Doe"
persona voice guide, invented lessons/comments/drafts — replacing any synced
real persona files, with `sync_seed` itself skipping under DEMO_MODE. A
per-IP rate limit middleware (10 POST `/api/*` requests per 60 s) guards the
free-tier quota on the same code path.

Evidence: `api/index.py`, `content_machine/config.py`
(`_apply_demo_overrides`, `DEMO_FLASH_MODEL`), `content_machine/demo_seed.py`,
`content_machine/storage/paths.py` (DEMO_MODE guard),
`content_machine/api/rate_limit.py`, `vercel.json`.

Unresolved rationale:
- Some demo spike titles/URLs are snapshots of real public articles (the
  module docstring says scores/verdicts are synthetic); was displaying real
  article metadata to anonymous visitors weighed and accepted?
- Was a fork/separate app ever considered before the flag-driven override?

### 9. External-CLI local ASR: faster-whisper (int8 CPU) and whisper.cpp

Status: Candidate (owner confirmation required)

Observed implementation: Speech-to-text runs entirely on local CPU via
subprocess wrappers rather than a cloud transcription API or an in-process
Python dependency. `BatchTranscriber` shells out to the `faster-whisper` CLI
with `--compute_type int8` (model sizes tiny..large-v3, default small);
`LiveMonitor` streams through a whisper.cpp binary on PATH. Neither
`faster-whisper` nor whisper.cpp appears in `requirements.txt` — install
instructions live in the module docstrings, keeping the ASR path optional.

Evidence: `content_machine/asr/batch.py`, `content_machine/asr/live.py`,
`content_machine/asr/transcript.py`, `requirements.txt`.

Unresolved rationale:
- Why subprocess isolation rather than depending on the `faster-whisper`
  Python package directly (model-cache control, CTranslate2 weight, or
  serverless exclusion)?
- Was any cloud ASR option benchmarked on cost or privacy grounds, and where
  is the privacy motivation documented?
