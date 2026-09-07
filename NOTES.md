# NOTES — Content Machine deep-research

## Completed
- Read `Content Machine Plan.md` (36.7KB blueprint: 6 Lieberman stages, local multi-LLM app).
- Scoped: focus = stack validation + pipeline patterns; platform = Windows local; goal = revised architecture.
- Workflow `deep-research` DONE (task `wr6j5mpjd`, run `wf_ef9b7ac4-ea5`): 104 agents, 22 sources fetched, 108 claims extracted, 25 verified, 21 confirmed, 4 refuted. Full report: `C:\Users\mamat\AppData\Local\Temp\claude\C--Users-mamat-Github-Content-Machine\4713280f-6bef-4b98-86f2-55dcaed8c658\tasks\wr6j5mpjd.output` (findings also in `findings.txt` beside it).

## Key results (confidence-ranked)
1. **LiteLLM supply-chain incident Mar 2026** (1.82.7/1.82.8, ~40min, poisoned Trivy CI, exfil to models.litellm.cloud). High, 3-0. → drop LiteLLM or pin >=1.83.0 + checksums + key rotation. Alternatives: direct provider SDKs + thin router, or OpenRouter.
2. **Failover must be 2-layer**: provider failover ≠ model-level errors (context overflow, moderation). Need explicit cross-model fallback array (OpenRouter pattern). High, 3-0.
3. **Writer's council bias fixes**: drafter + all 4 judges must be different model families; self-preference persists under objective rubrics (>50% wrong-pass own family; up to 10-pt skew). High, 3-0 x5. Bias partly perplexity/familiarity → add authorship obfuscation; provider diversity alone insufficient. Same-model sampling panels fail correlated/bimodal (9 judges ≈ 2 effective votes). Debate-beats-voting REFUTED 0-3 → independent scoring + aggregation only.
4. **9.0/10 absolute gate miscalibrated**: per-model score tendencies measured. → normalize per judge (z/percentile) or calibrate persona↔model to human anchors. Freeze rubric format in repo; frontier-class judges only (small judges swing >0.05 correlation on format perturbations).
5. **Structured outputs**: Anthropic GA grammar-constrained (output_config.format), zero parse errors, but no numeric/string-length constraints → keep Pydantic client-side; Instructor retry loop vestigial on Claude path. High, 3-0 x3.
6. **ASR**: NVIDIA Parakeet-TDT-0.6B-v3 (6.32% WER) / Canary-1B-v2 (7.15%) beat Whisper-large-v3 (7.44%) at 7-10x speed — batch only. Live dictation needs whisper.cpp-style streaming or Nemotron streaming. faster-whisper still sound (RTX 3070 Ti: 13-49x real-time batch). Medium/high, 2-1.

## Refuted (0-3 votes)
- Multi-agent debate beats static voting; Beta-Binomial convergence detector; two weaker structured-output claims.

## Coverage gaps (unvalidated — neither confirmed nor denied)
- Subsystem 2 FastAPI vs Node; 5 Tauri/Electron/web UI; 6 storage/vector DB (sqlite-vec/LanceDB); 7 connectors (Slack/Linear/GitHub/IMAP/RSS limits); 9 regex slop linters; 10 lessons diff loop; 11 spike-scoring rubric.

## Open questions
- Best council aggregation rule post debate-refutation; OpenAI/Gemini/Qwen structured-output parity; Windows streaming dictation (whisper.cpp vs Nemotron vs Wispr Flow); LiteLLM governance recovery.

## Pass 2 — DONE (task `wfs1g9vd5`, run `wf_11b7b570-101`)
113 agents, 22 claims verified, 8 findings + coverage report. Details: `findings2.txt` in temp tasks dir.
- **Slack**: `bookmarks.list` + scope `bookmarks:read`, channel-scoped, enumerate channels first, ~100 bookmarks/channel. Starred items DEAD: stars.list frozen/retiring, no Save-for-Later API. Drop starred requirement. [high]
- **Gmail**: OAuth 2.0 mandatory. Basic-auth IMAP/SMTP dead (Mar 14 2025), LSA ended May 1 2025. GCP OAuth client needed. [high]
- **GitHub**: PAT 5,000 req/hr covers daily pull. No App needed. Unauth 60/hr. [high]
- **Slop**: regex lints = weak pre-filter only. Paraphrase collapses surface detectors (DetectGPT 70.3→4.6% at 1% FPR). Closed-API stack: prompt constraints + lint + human gate. Antislop decode-time sampler (8k+ patterns, −69-96% throughput) needs open weights; FTPO (~90% reduction) needs fine-tune access. [high/medium]
- **Council aggregation (Q A)**: default = independent scoring + voting/ensemble, NOT debate (NeurIPS 2025 Spotlight). Debate only for contested/high-variance items (JudgeBench 63.66→68.06; loses on consensus tasks 72.20 vs 76.60). Continuous-score aggregation rule (trimmed mean/median/calibration) unanswerable from public evidence. [high]
- **Lessons loop**: evolving-memory failure modes — compounding errors, stale-rule conflicts, re-summarization drift. Governance: provenance+timestamps per rule, conflict detection, reconciliation/decay passes, cap/merge. Source = untested position paper; human-approve loop already mitigates worst class. [medium]
- **Idea scoring**: single unsampled score as ≥8.0 gate INVALID. Intra-rater Krippendorff α 0.26-0.79, identical judgments 61.3% max, "almost arbitrary in worst case". Fix: repeated sampling + aggregation or temp-0 + margin bands. Rubric weights themselves untested. [high]
- Linear/Jira: no surviving claims.

## Still unresolved after both passes (zero surviving claims)
Subsystem 2 (FastAPI vs Node), 5 (Tauri/Electron/web), 6 (vector DB/embeddings), open Q B (structured-output parity OpenAI/Gemini/Qwen), Q C (Windows streaming dictation whisper.cpp vs Nemotron vs Wispr Flow), Q D (LiteLLM governance recovery). Recommend pragmatic defaults marked as judgment, not evidence.

## Plan v2 — WRITTEN
- `Content Machine Plan v2.md` in project root. Merges both passes; ⚠ flags pragmatic defaults (backend FastAPI, UI browser-first, storage Markdown+SQLite no vector DB, persona-family assignment, build order).
- 14 sections: changes table, stack, 6 subsystems, gateway/failover, structured-output policy, cadence, privacy correction, pre-build spikes (§12), evidence register (P1-F1..F11, P2-F1..F8 + refuted + unresolved), build order (§14).

## Spikes — RUN (details in spikes/RESULTS.md)
- **Gateway reality**: only LLM route = Aliyun Token Plan gateway, Anthropic Messages protocol at /apps/anthropic. No OpenAI path (404/401). Catalog = Qwen family ONLY (3.6/3.7/3.8 max/plus/flash/opensource) + wan-video. Env maps Claude slots → qwen3.8-max/flash.
- **Structured outputs (relay, qwen3.8-max)**: messages.parse works. JSON 8/8 extracted; Pydantic-valid T1 2/3, T2 2/3, T3 2/2. No grammar guarantee (1 malformed JSON); no numeric-bound enforcement (emitted 26.94 vs le=10) → Pydantic-always rule (plan v2 §9) locally proven. Real Anthropic/OpenAI/Gemini parity blocked — no keys.
- **Hardware**: i7-1255U, 16GB, Iris Xe — no CUDA. ASR plan rewrite: faster-whisper int8 batch + whisper.cpp live; Parakeet dropped. Benchmark deferred (needs voice sample).
- **Blocked**: judge calibration (multi-family keys + 20 anchor drafts), Slack (token), Gmail (GCP console steps), DashScope native mode (standard API key).
- bl auto-updated 1.14.2 → 1.20.0 during config show despite keep-1.14.2 choice (CLI self-update).

## Plan v2 amended (post-spike)
- Operator decision: single-family Qwen panel, bias risk accepted. §5.1 rewritten (diversity within family, human gate = primary QC, scores advisory), §5.4 persona table → qwen3.8-max writer + 3.7-plus/3.8-flash/3.6-max/3.8-opensource judges.
- §3.1 rewritten CPU-only (faster-whisper int8 batch + whisper.cpp live; Parakeet dropped pending GPU).
- §8.2 route reality: Token Plan relay only, protocol adapters in ModelRouter, parse-failure retry. §9 item 4 local evidence added. §12 spike log updated.

## Build — steps 1-2 DONE (2026-09-04)
- Repo layout: `content_machine/` package (config.py, schemas.py, storage/{paths,db}.py, router/{base,messages_adapter}.py), `knowledge/` seeds, `tests/`, config.json, requirements.txt.
- Storage: tree at C:\Users\mamat\.content_machine initialized; SQLite schema = spikes/transcripts/iterations/judge_score_history/lessons(governance fields)/audit_log; FK + UNIQUE enforced; CONTENT_MACHINE_HOME override for tests.
- Router: ModelRouter 2-layer failover (ProviderError→next route; ModelError→next model; AllRoutesFailed log); MessagesAdapter = messages.parse + 1 retry on schema-invalid; bearer-token auth (ANTHROPIC_AUTH_TOKEN — ANTHROPIC_API_KEY in env is a 2-char placeholder, relay rejects x-api-key with 401).
- Tests: tests/test_storage.py + tests/test_router.py ALL PASS offline; CONTENT_MACHINE_LIVE=1 smoke OK (qwen3.8-max via relay → Pydantic-valid CouncilScores).

## Build — step 3 DONE (2026-09-04, session end)
- `council/rubric_v1.md` frozen in repo. `content_machine/council/`: obfuscate.py (model-token + generation-header stripping), normalize.py (per-judge z from history, min_samples gate), loop.py (parallel panel via router, quorum 3, margin-band resample ±0.3, max iterations + break-with-best, revision via writer, full persistence).
- Relay reality: catalog ≠ served. Live models: qwen3.8-max/3.8-flash/3.7-max/3.7-plus/3.6-flash. DEAD on relay: qwen3.7-flash, qwen3.6-plus (403), qwen3.6-max, qwen3.8-opensource ("Model not exist").
- qwen3.6-flash lacks structured parse: relay translates to response_format=json_object and 400s. Adapter fix: degrade to explicit JSON prompting + Pydantic validation (messages_adapter._plain_json_mode). Rubric output contract now says JSON explicitly.
- config.json council: perell=3.7-max, puri=3.8-flash, housel=3.7-plus, slop_allergist=3.6-flash; council_margin=0.3 added. Plan v2 §5.4 table updated to verified-live models.
- Tests: storage 3 + router 7 + council 7 ALL GREEN. Live council smoke 4/4 judges, composite 8.82, resample fired, break-with-best correct.

## Tomorrow — resume state
- Next: §14 step 4 connectors (Slack bookmarks needs token; GitHub PAT; Gmail OAuth console steps in spikes/RESULTS.md; RSS trivial).
- Blocked spikes still: #3 calibration (anchor drafts + external family), #4 Slack token, #5 Gmail.
- Run everything: `python tests/test_storage.py; python tests/test_router.py; python tests/test_council.py`; live: `CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py`.
- Real storage live at C:\Users\mamat\.content_machine; repo layout in NOTES sections above.


## Build — step 4 DONE (2026-09-04)
- `content_machine/connectors/`: base.py (ConnectorItem/ConnectorResult dataclasses + BaseConnector ABC), rss.py (RSSConnector: RSS+Atom auto-detect, ETag/If-None-Match caching, GUID dedup, 304 support), github.py (GitHubConnector: PAT Bearer auth, since filter, Link-header pagination).
- requirements.txt: added requests>=2.32.0.
- Tests: tests/test_connectors.py, 14 tests ALL GREEN; full suite 31/31 PASS.
- Blocked connectors (need tokens): SlackConnector (bookmarks:read token), GmailConnector (GCP OAuth client, see spikes/RESULTS.md Spike 6).

## Tomorrow — resume state
- Next: step 5, Idea scoring (N-sample aggregation, IdeaScore already in schemas.py, Oracle wiring connectors into staging, scoring, spike.json).
- Also consider: daily pull orchestrator (08:00 cadence per plan v2 Sec 10), staging dedup pipeline.
- Blocked spikes: Slack token, Gmail GCP OAuth, judge calibration (anchor drafts + external family).
- Run all: `python tests/test_storage.py; python tests/test_router.py; python tests/test_council.py; python tests/test_connectors.py`; live: `CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py`.
- Real storage live at C:\\Users\\mamat\\.content_machine; repo layout above.
## Build -- step 5 DONE (2026-09-04)
- content_machine/oracle/: scorer.py (IdeaScorer: N-sample aggregation, median composite, verdict bands pass/review/reject, prompt with full rubric), oracle.py (OracleOrchestrator: connector pull + URL dedup + score + SQLite persist + sorted return), __init__.py.
- IdeaScore schema was already in schemas.py; ScoredIdea dataclass carries item, all samples, median, and verdict.
- Tests: tests/test_oracle.py, 17 tests ALL GREEN; full suite 48/48 PASS.

## Tomorrow -- resume state
- Next: step 6, ASR dual path (faster-whisper int8 batch + whisper.cpp live streaming, CPU-only per plan v2 Sec 3.1). Benchmark deferred -- needs voice sample.
- Step 7 after: Lessons loop (differ, extractor, conflict-check append).
- Step 8 after: UI (React + FastAPI WebSocket).
- Blocked spikes: Slack token, Gmail GCP OAuth, judge calibration.
- Run all: python tests/test_storage.py; python tests/test_router.py; python tests/test_council.py; python tests/test_connectors.py; python tests/test_oracle.py
- Live smoke: CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py

## Build -- steps 6+7 DONE (2026-09-04)
- content_machine/asr/: transcript.py (Transcript: text, model, audio_path, word_count, meets_minimum, save to Markdown), batch.py (BatchTranscriber: faster-whisper subprocess, int8 compute_type, timestamp stripping, RuntimeError on nonzero exit), live.py (LiveMonitor: whisper.cpp Popen, per-line callback, timestamp strip, blank-line skip), __init__.py.
- content_machine/lessons/: differ.py (LessonsDiffer: structured diff prompt, ExtractedRules schema, 3-rule cap), store.py (LessonsStore: propose/approve/reject human-gate, conflict detection via cosine on numpy embeddings stored as SQLite BLOBs, hard cap, active/pending queries), __init__.py.
- Tests: test_asr.py 14 tests + test_lessons.py 12 tests ALL GREEN; full suite 74/74 PASS.

## Tomorrow -- resume state
- Next: step 8, UI (React + Vite frontend + FastAPI backend with WebSocket token streaming).
  Before that, consider wiring all subsystems into a CLI entrypoint (python -m content_machine run/score/council etc.) for manual daily use without a UI.
- Deferred benchmarks: faster-whisper WER on voice sample (needs ffmpeg + recording), judge calibration (anchor drafts), Slack/Gmail tokens.
- Run all: python tests/test_storage.py; python tests/test_router.py; python tests/test_council.py; python tests/test_connectors.py; python tests/test_oracle.py; python tests/test_asr.py; python tests/test_lessons.py
- Live smoke: CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py

## Build -- CLI entrypoint DONE (2026-09-04)
- content_machine/__main__.py: python -m content_machine entrypoint.
  Subcommands: oracle (--rss/--github/--all/--no-persist), council <draft>, transcribe <audio> [--model] [--save], lessons list/approve/reject/diff.
  _make_router() and _make_db() build live infra from config.json + env; all subsystems patchable in tests.
- Tests: tests/test_cli.py -- 18 tests ALL GREEN; full suite 92/92 PASS.

## Remaining: step 8 -- UI
- FastAPI backend + React/Vite frontend + WebSocket token streaming (plan v2 Sec 1).
- Suggested order: FastAPI app.py (endpoints: /oracle, /council/stream, /transcribe, /lessons), then React scaffolding.

## Quick start (works right now)
    python -m content_machine oracle --rss https://example.com/feed --no-persist
    python -m content_machine oracle --github owner/repo
    python -m content_machine council path/to/draft.md
    python -m content_machine transcribe recording.wav --model small --save transcript.md
    python -m content_machine lessons diff draft_v1.md published.md
    python -m content_machine lessons list
    python -m content_machine lessons approve 1
    CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py

## Build -- step 8 DONE: Minimalist Modern UI (2026-09-04)
- content_machine/api/app.py: FastAPI application with REST endpoints:
  - GET /api/health (service ping)
  - POST /api/oracle/run (RSS/GitHub ingestion + N-sample idea scoring)
  - POST /api/council/run (parallel judge scoring + z-normalization + revision cycle)
  - GET /api/lessons (active governed rules list)
  - POST /api/lessons/{id}/approve & /reject (human gate)
  - POST /api/lessons/diff (declarative rule extraction from draft vs published diff)
  - Catch-all static file & SPA fallback routing serving ui/dist.
- ui/ React + Vite + Tailwind SPA:
  - Minimalist, modern dark zinc aesthetic (zinc-950, zinc-900 cards, zinc-800 borders, Inter + JetBrains Mono).
  - Clean tabs for all 4 subsystems: Oracle, Council, Lessons, Audio.
  - Seamless inter-tab workflows (e.g. 1-click 'Draft with Council' from scored Oracle ideas).
  - Conflict warning badges, rule cap alerts, and approve/reject review queue for Governed Lessons.
  - Production build compiled to ui/dist (1.1kB index.html, 15kB CSS, 173kB JS).
- Tests: tests/test_api.py (10 tests ALL GREEN).
- Full Project Test Suite: 102/102 tests across 9 test suites ALL PASSING.

## How to Run the App & UI
1. Start the backend + frontend bundle together:
   python -m content_machine serve --port 8000
   Open browser at: http://127.0.0.1:8000

2. Or run Vite dev server separately with hot reload:
   cd ui && npm run dev
   Open browser at: http://localhost:5173

### Port Configuration Update (Occupied Port Mitigation)
- Backend port defaulted to 8080 (or any custom port via --port <port>).
- CORS updated to allow all local origins.
- Vite dev server updated to port 5174 with automatic fallback to next available port (strictPort: false) and proxying to 8080.

Run:
  python -m content_machine serve --port 8080
  Open http://127.0.0.1:8080

## Build -- LinkedIn Session Connector DONE (2026-09-04)
- content_machine/connectors/linkedin.py:
  - LinkedInConnector (BaseConnector): authenticates using local session cookie (li_at) + CSRF token.
  - Queries LinkedIn Voyager API directly: profile shares/updates or authenticated home feed.
  - Zero 3rd-party dependencies or external SaaS subscriptions needed.
  - Extracts title, full post text, URN guid, actor, and canonical post URL into ConnectorItem.
- Integrated into OracleOrchestrator, CLI (python -m content_machine oracle --linkedin <profile/feed> --li-at <cookie>), and UI.
- Tests: tests/test_linkedin_connector.py (6/6 tests passing). Full suite: 10/10 test suites ALL GREEN.

## Build -- Subsystem 6: Cross-Channel Distribution Engine DONE (2026-09-04)
- content_machine/distribution/engine.py:
  - DistributionEngine: transforms human-approved anchor post into 3 platform derivative formats.
  - 1. X (Twitter) Thread: hook + 6-8 numbered insight cards + operational takeaway.
  - 2. Short-Form Video Script: 60-90s spoken script with [Visual Cue], [Camera Zoom], and [Pause] production markers.
  - 3. Newsletter Digest: 300-400 word executive briefing with clean Markdown headers and bulleted takeaways.
  - Strictly grounded prompt design (zero hallucination of new facts or metrics).
  - save_bundle(): writes files directly to projects/{slug}/distribution/{format}.md.
- Integration:
  - FastAPI: POST /api/distribute/run.
  - CLI: python -m content_machine distribute <post_file> [--slug <slug>] [--no-save].
  - React UI: dedicated 'Distribute' tab with channel tabs and 1-click clipboard copy, plus 1-click bridge from Writer's Council passing verdict.
- Tests: tests/test_distribution.py (5/5 tests passing). Full suite: 11/11 test suites (107 tests) ALL GREEN.

## Build -- Developer RSS Feeds Expansion DONE (2026-09-04)
- Added top engineering and developer community feeds to config.json:
  - dev.to: https://dev.to/feed (DEV Community)
  - lobste.rs: https://lobste.rs/rss (Lobsters Engineering)
  - github.blog: https://github.blog/feed/ (GitHub Official Blog)
  - freecodecamp: https://www.freecodecamp.org/news/rss/ (freeCodeCamp)
  - hacker_news: https://news.ycombinator.com/rss (Hacker News)
- Tested RSSConnector live and offline parsing with dev.to CDATA and author namespaces (12 items extracted cleanly).
- Added test_fetch_parses_devto_style_feed to tests/test_connectors.py (20/20 tests passing).
- Updated React UI with instant developer feed preset pill buttons (+ dev.to, + Hacker News, + Lobsters, + GitHub Blog, + freeCodeCamp).
- Verified via browser tool and screenshot.

## Operation -- Developer Feeds Ingestion Stage Completed (2026-09-04)
- Ran ingestion stage across all 5 configured developer community RSS feeds.
- 87 fresh items successfully fetched and deduplicated:
  - dev.to: 12 items
  - hacker_news: 30 items
  - lobste.rs: 25 items
  - github.blog: 10 items
  - freecodecamp: 10 items
- Added --fetch-only CLI flag to python -m content_machine oracle for zero-token ingestion preview.
- Windows console UTF-8 emoji encoding safety handled in __main__.py.

---

## SDD checkpoint 2026-09-06 — UI modularization (STOPPED by user, handover)

Branch `refactor/ui-modularization`. Tasks 1-6 complete+reviewed (dd6bf63..ede333c): vitest infra, lib/topics, lib/constants, full api/ layer (fetch in App.jsx = 0), useCopyToClipboard. Task 7 implemented (b5ab0b6, useVoiceRecording, 33/33 tests) — review incomplete, opus reviewer killed at stop order; 7 flagged items await ruling. Tasks 8-19 not started.
Full handover: `.superpowers/sdd/2026-09-06-ui-modularization/HANDOVER.md`. Ledger: same dir `progress.md`. All 19 briefs pre-generated.
Resume: invoke superpowers:subagent-driven-development on `docs/superpowers/plans/2026-09-06-ui-modularization.md`; first action = re-dispatch Task 7 review (inputs on disk).

## UI Modularization Completed & CSS Theme Harmonization (2026-09-06)
- Completed all remaining tasks (Tasks 7–19) of the UI Modularization plan on `refactor/ui-modularization`:
  - Extracted hooks (`useVoiceRecording`, `useServerHealth`), UI primitives (`TabBtn`), and all feature tab orchestrators and subcomponents (`profile/`, `commenting/`, `audio/`, `lessons/`, `distribute/`, `council/`, `oracle/`).
  - Extracted shared workflow hook `useSharedFlow` and simplified `App.jsx` from 5,125 lines down to ~60 lines.
- Harmonized Draft Studio styling in `ui/src/components/council/DraftingStudio.jsx`:
  - Replaced dark `#141413` container, dark inputs, and dark chips with warm editorial paper theme (`#faf9f5`, `#f0eee6`, `#e3dacc`, `#141413`, `#c6613f`).
  - Added unit test suite `ui/src/components/council/DraftingStudio.test.jsx`.
  - Configured `maxWorkers: 4` in `ui/vite.config.js` to ensure reliable parallel worker execution under Windows.
  - Verification: 20/20 test suites (60/60 tests) pass in Vitest; 212/212 unit tests pass in Python; Vite production build succeeds cleanly.

