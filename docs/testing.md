# Testing

This document describes the test suite as it exists in the repository: the layers, the offline guarantee, the exact commands, and what the CI pipeline runs. All counts and outcomes below were measured by running the suite on 2026-09-09.

## Strategy: offline-first

The entire suite runs with zero live network calls and zero real LLM API usage. This is achieved structurally, not by convention:

- Every outbound HTTP call in production code goes through `requests` (connectors) or the model router (LLM calls). Tests replace those seams with `unittest.mock.patch` on the exact import location (for example `patch("content_machine.connectors.rss.requests.get")`) and return `MagicMock` responses carrying inline XML/JSON fixtures.
- API-level tests use FastAPI's `TestClient` (in-process ASGI, no real server socket), with all subsystem calls mocked. The module docstring of `tests/test_api.py` states this explicitly, and 16 of the 30 test files import `TestClient`.
- Storage tests rely on the `CONTENT_MACHINE_HOME` environment-variable override (declared for this purpose in `content_machine/storage/paths.py`) so no test touches the real `~/.content_machine` state.
- Live checks are opt-in and excluded by naming: `tests/live_council_smoke.py` does not match the `test_*.py` collection pattern, and `tests/test_connectors.py` documents a `CONTENT_MACHINE_LIVE=1` gate for live smoke runs. Neither path executes in CI.

There is no pytest configuration file in the repository (no `pytest.ini`, `pyproject.toml`, `setup.cfg`, or root `conftest.py`); collection uses pytest defaults.

## Layers

### Backend unit tests (`tests/`, plain `unittest`, 30 files)

Coverage is organized around the pipeline subsystems: `test_oracle.py`, `test_oracle_classifier.py`, `test_oracle_dedup.py`, `test_council.py`, `test_council_gate.py`, `test_council_history.py`, `test_commenting.py`, `test_humanize.py`, `test_distribution.py`, `test_distribute_history.py`, `test_editorial_rules.py`, `test_editorial_context.py`, `test_lessons.py`, `test_interview.py`, `test_asr.py`, `test_image_prompts.py`, `test_profile.py`, `test_storage.py`, `test_bootstrap.py`, `test_connectors.py`, `test_idea_bank_connector.py`, `test_linkedin_connector.py`, `test_linkedin_automation.py`, `test_rate_limit.py`, `test_router.py`, `test_router_gemini.py`, `test_cli.py`, `test_api.py`, `test_demo_mode.py`, `test_doc_drift.py`.

Notable: `test_cli.py` exercises the argparse command surface of `python -m content_machine` with patched components, and `test_demo_mode.py` pins the behavior of `DEMO_MODE` (model overrides in `content_machine/config.py`, the `/tmp` demo home, seeded-data survival).

### API-level tests

`test_api.py` (and related files) drive the FastAPI app through `TestClient`, covering `/api/health`, `/api/meta`, and the domain endpoints without binding a socket. This is an in-process integration layer, not a live-server test.

### Documentation-consistency tests (`tests/test_doc_drift.py`)

A session audit on 2026-09-09 found five documentation-versus-code conflicts. They were fixed by hand, and this file makes recurrence fail the suite instead of drifting silently. Six pinned checks plus failure-logic proofs:

1. The `AGENTS.md` claim "Hard cap of active rules (default: N)" must equal `content_machine.lessons.store.DEFAULT_CAP` (currently 150).
2. Each README council-judge line (display name plus backticked model id: Narrative Judge, Punch Judge, Depth Judge, Slop Allergist) must match the corresponding `models.council` key (`perell`, `puri`, `housel`, `slop_allergist`) in `config.json`.
3. Every `config.json models.council` model id must appear in the AGENTS.md allowed-models section, sliced so that the "Do NOT route to" blacklist cannot satisfy the check.
4. The word-limit truth "280" must appear in `knowledge/01_style-guide.md`, `02_voice-guide.md`, `03_content-lessons.md`, and none of the scanned files (those three plus `interview/engine.py`, `council/loop.py`, `distribution/engine.py`, `humanize/constants.py`) may contain the stale range spellings `120-250`, `120–250`, or "120 and 250".
5. `requirements.txt` must not pin `openai==` (the relay is Anthropic-Messages-protocol only).
6. `content_machine/editorial/rules.py` must define `WORD_COUNT_MIN = 120` and `WORD_COUNT_MAX = 280`. It is read as text (regex), not imported. Note: the module docstring still describes this check as "expected-RED until task-1 lands"; the file exists and the check passes, so that comment is stale.

Six additional `test_failure_logic_*` tests mutate inline fixtures to prove each guard fires on drift, on missing claims, and on blacklisted ids — without touching disk.

### UI tests (`ui/`, 25 files, vitest)

Vitest 5.0.0 with `jsdom` environment, configured in `ui/vite.config.js` (`test.environment: 'jsdom'`, `setupFiles: './src/setupTests.js'`, globals on, 15 s timeout, max 4 workers). `src/setupTests.js` imports `@testing-library/jest-dom/vitest`; component assertions use `@testing-library/react` and `@testing-library/user-event`. Test files cover the API client, SSE handling, tab wiring, each feature tab component (oracle, council, commenting, lessons, distribute, profile, audio), the demo banner, shared hooks, and the `lib/` helpers (`textStats`, `angles`, `constants`, `topics`).

No network is made from UI tests: the API client is exercised against stubbed `fetch`/transport seams.

## Commands and measured results

Run date: 2026-09-09, Windows 11, local Python 3.11.9, Node with `ui/node_modules` already installed (`npm ci` state).

Backend:

```powershell
python -m pytest tests -q
```

Result: **389 passed**, exit code 0, ~19.5 s. One non-failing `PytestDeprecationWarning` appears locally because `pytest-asyncio` is installed in the local environment; that package is not in `requirements.txt` and the suite does not depend on it (all tests are synchronous `unittest` style).

UI:

```powershell
cd ui
npx vitest run
```

Result: **78 tests passed across 25 test files**, exit code 0, ~47 s. A benign jsdom notice ("Not implemented: Window's scrollTo() method") is printed; it does not affect any assertion.

If `ui/node_modules` is absent, install first with `npm --prefix ui install` (or `npm ci` inside `ui/`).

## CI behavior (`.github/workflows/ci.yml`)

Triggers: `push` to `main`, `fix/**`, or `feat/**`, and all `pull_request` events. Concurrency group `ci-${{ github.ref }}` with `cancel-in-progress: true`.

| Job | Runner | Runtime | Install | Test command |
|---|---|---|---|---|
| `backend` | ubuntu-latest | Python 3.11 (pip cache) | `pip install -r requirements.txt && pip install pytest` | `python -m pytest tests -q` |
| `ui` | ubuntu-latest | Node 22 (npm cache, `cache-dependency-path: ui/package-lock.json`) | `npm ci` in `ui/` | `npm test` (= `vitest run`) |

Both jobs mirror the local commands exactly and run offline-capable suites, so CI needs no credentials. Note two small version discrepancies, stated honestly: `.python-version` declares `3.12` while CI pins `3.11`, and the CI comment records Node 22 as required because jsdom/undici need `markAsUncloneable` from Node >= 20.18.

## What does not exist

Verified absent as of 2026-09-09; do not assume any of these:

- **No coverage reporting**: no `.coveragerc`, no `--cov` flag in CI or local commands, no coverage dependency in `requirements.txt` or `ui/package.json`.
- **No end-to-end browser tests**: Playwright appears only as an optional production connector dependency (lazy imports in `connectors/linkedin_session.py` / `linkedin_public.py`, deliberately left commented out of `requirements.txt`) and as a setup note in `.env.example`; it is not a UI devDependency, and no e2e spec files or CI job exist.
- **No contract/schema tests** against external provider APIs (OpenAPI snapshots, recorded cassettes, or live relay checks).
- **No load or performance tests.**
- **No live-network test job in CI**; the `CONTENT_MACHINE_LIVE` gate and `live_council_smoke.py` are local, opt-in only.
