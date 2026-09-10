# Deployment

Content Machine ships in two distinct deployment models:

- **A — Local self-hosted**: the FastAPI backend (which also serves the built UI) on your own machine, backed by durable state in `~/.content_machine` and your own model relay credentials.
- **B — Vercel public demo**: a sanitized, Gemini-only showcase at `https://content-machine-chi-lac.vercel.app`, with ephemeral state and synthetic seeded data.

Everything below was verified against the repository and against the live demo on 2026-09-09.

## A. Local self-hosted deployment

### Prerequisites

- **Python.** `.python-version` declares `3.12`; CI pins `3.11` and the suite was verified locally on 3.11.9. Treat 3.11–3.12 as the supported window.
- **Node.js.** CI uses Node 22 for the UI; a comment in `.github/workflows/ci.yml` records Node >= 20.18 as a hard floor (jsdom/undici require `markAsUncloneable`). Use 22.
- Optional, only for the authenticated LinkedIn browser-session connector: `pip install "playwright>=1.40" && playwright install chromium` (deliberately commented out of `requirements.txt`; the production code imports it lazily).

### Setup

```powershell
# from the repository root
python -m venv .venv
.venv\Scripts\activate            # Windows; source .venv/bin/activate on POSIX
pip install -r requirements.txt

copy .env.example .env            # then fill in values (see Configuration below)

npm --prefix ui install
npm --prefix ui run build         # emits ui/dist
```

### Run

```powershell
python -m content_machine serve --port 8080
```

Notes verified in source:

- The `serve` subcommand wraps `uvicorn.run("content_machine.api.app:app", ...)`. Its argparse defaults are `--host 127.0.0.1` and `--port 8000`; the README command passes `--port 8080` explicitly because the Vite dev proxy and the documented workflow expect the backend on 8080. If you run on a different port, keep it consistent with `BACKEND_PORT` in dev mode.
- `--reload` is available for development.
- After `npm run build`, the same process serves the UI: `content_machine/api/app.py` mounts `/assets` from `ui/dist` and has a catch-all route returning `ui/dist/index.html` for SPA routing, both guarded on `ui/dist` existing. Without a build you get the API only.
- Open `http://localhost:8080`.

### Development mode (hot reload)

Two processes, per the README:

```powershell
python -m uvicorn content_machine.api.app:app --port 8080
npm --prefix ui run dev
```

`ui/vite.config.js` defines the dev server: port `PORT` (default **5174**, `strictPort: false` so it falls through when busy) and a `/api` proxy to `http://127.0.0.1:${BACKEND_PORT || 8080}` with 600-second connect/proxy timeouts (long LLM calls). Set `PORT` / `BACKEND_PORT` in the environment only if the defaults collide.

### Configuration

`config.json` (repo root) holds routing, model, and threshold settings and is loaded by `content_machine/config.py`. It never holds secrets; routes reference environment variables by name. Secrets live in `.env` (git-ignored), loaded via `python-dotenv`. Variable names from `.env.example` only — never commit or share values:

| Name | Purpose |
|---|---|
| `ANTHROPIC_BASE_URL` | Anthropic-Messages-protocol relay/gateway base URL |
| `ANTHROPIC_AUTH_TOKEN` | Bearer token for that relay |
| `GEMINI_API_KEY` | Native Gemini provider key (optional locally, required for the demo) |
| `DEMO_MODE` | Demo-behavior switch (see section B); leave unset locally |
| `CONTENT_MACHINE_HOME` | Storage root override; default `~/.content_machine` |
| `GITHUB_PAT` | GitHub connector token (optional) |
| `LINKEDIN_LI_AT` | LinkedIn `li_at` session cookie (optional) |
| `PORT`, `BACKEND_PORT` | Vite dev-server port and its proxy target (dev only) |

State layout under the storage root: `knowledge/` (runtime copies of repo `knowledge/*.md` seeds, refreshed on `ensure_tree`), `archive/`, and `projects/<slug>/` with `iterations/` and `distribution/` subdirectories, plus the SQLite database that is the source of truth for governed lesson rules once seeded.

## B. Vercel public demo

### Build and routing (`vercel.json`)

```json
{
  "framework": null,
  "buildCommand": "npm --prefix ui install && npm --prefix ui run build",
  "outputDirectory": "ui/dist",
  "functions": { "api/index.py": { "maxDuration": 60 } },
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/index.py" },
    { "source": "/:path*", "destination": "/index.html" }
  ]
}
```

One Vercel Python serverless function (`api/index.py`, `maxDuration` 60 s) serves every `/api/*` request; the SPA static export handles the rest.

### Cold start (`api/index.py`)

The module sets, via `os.environ.setdefault` (so an explicit platform value would win):

- `CONTENT_MACHINE_HOME=/tmp/cm` — Vercel's writable filesystem is ephemeral; nothing here survives instance death.
- `DEMO_MODE=1`.

It then imports the same ASGI `app` used locally and runs `_cold_start()` at import time: `paths.ensure_tree()` (skips seed-copy under demo mode, see below) opens the SQLite database and calls `content_machine.demo_seed.seed_demo(conn)`. Finally it installs `RateLimitMiddleware` with `limit_per_min=10`.

`seed_demo` is idempotent — it short-circuits when any `demo-%` spike row already exists — and inserts a wholly synthetic showcase: 10 demo spikes (scores/verdicts fabricated, some source URLs are real public articles), 6 style lessons, a 3-iteration council history with judge-score rows for one spike, 2 demo comments, and two distribution bundles. Before the idempotency guard it always rewrites the runtime voice guide to the synthetic "John Doe" persona (a fictional senior-engineer identity defined in `content_machine/demo_seed.py`), so a real author's guide can never surface in the demo.

### Rate limiting (`content_machine/api/rate_limit.py`)

In-memory, per application instance. POST requests to `/api/*` only. A sliding 60-second token window keyed by `request.client.host`, capped at `limit_per_min` (10). Over the cap the middleware returns HTTP 429 with `{"detail": "demo rate limit reached: try again in a minute"}`. GET requests (including `/api/meta`) are unthrottled. Because state is per-instance, cold starts and multiple instances reset or parallelize the cap — it is a quota guard, not a security boundary.

### What `DEMO_MODE=1` changes

- **Model routing** (`content_machine/config.py::_apply_demo_overrides`, active when `DEMO_MODE=1` and `GEMINI_API_KEY` is set): replaces routing with a single `gemini` route and maps every model glob to it; `writer`, `scanner`, `video_long`, and every council slot become `gemini-2.5-flash` (`DEMO_FLASH_MODEL`). Without a `GEMINI_API_KEY`, the override is skipped and the configured relay routing stays in place.
- **Council iterations** (`content_machine/api/app.py::demo_council_max_iterations`): forces a maximum of 1 iteration.
- **Seed sync** (`content_machine/storage/paths.py::sync_seed`): returns immediately under demo mode, so repo knowledge seeds never overwrite the synthetic persona files in the demo home.
- **UI banner**: `/api/meta` reports `{"demo_mode": true, "llm": "gemini"}` and the React app renders `DemoBanner`.

### Environment variables on Vercel

`GEMINI_API_KEY` and `DEMO_MODE` must be provided as Vercel project environment variables (dashboard or `vercel env`). Names only here; values are secrets and are not in this repository. `CONTENT_MACHINE_HOME` does not need dashboard configuration because `api/index.py` defaults it to `/tmp/cm`.

### Deployment workflow

The deployment path evidenced in the repo is the **Vercel CLI** (`vercel`, `vercel --prod` for a production release) run from a logged-in account. There is no repository-side GitHub auto-deploy configuration: `vercel.json` contains no git-integration settings, `.vercel/` is git-ignored (`.gitignore` line 22), and no CI job in `.github/workflows/ci.yml` deploys. Whether the Vercel project is additionally linked to the GitHub repository for automatic deployments is a dashboard-side setting that cannot be verified from this repository; treat CLI deploys as the documented mechanism.

### Live verification (2026-09-09)

`GET https://content-machine-chi-lac.vercel.app/api/meta` returned HTTP 200 with body `{"demo_mode":true,"llm":"gemini"}`, confirming the function, demo mode, and Gemini routing are live. (One request; GET is not rate-limited, but avoid load on the shared instance.)

## Local versus demo

| Aspect | Local self-hosted | Vercel public demo |
|---|---|---|
| State root | `~/.content_machine` (override `CONTENT_MACHINE_HOME`), durable | `/tmp/cm`, ephemeral — reset on every cold start, then reseeded |
| Models | Configured relay routes from `config.json` (`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN` relay; optional Gemini) | All roles forced to `gemini-2.5-flash` when `GEMINI_API_KEY` present |
| Council iterations | As requested (`demo_council_max_iterations` passes `requested or 1`) | Hard-capped at 1 |
| Rate limiting | None (middleware not installed by `content_machine/api/app.py`; only `api/index.py` adds it) | 10 POST /api requests per IP per 60 s, per instance |
| Data | Real author knowledge seeds (`knowledge/*.md`) synced into the runtime; lessons/DB from your own work | Synthetic "John Doe" persona and `demo-%` seeded showcase only |
| Seed sync | `ensure_tree` refreshes runtime knowledge copies from repo seeds, keeping `.bak` backups | `sync_seed` skipped entirely so synthetic persona survives |
| UI serving | Backend serves `ui/dist`, or Vite dev server on :5174 in dev | Static `ui/dist` via `outputDirectory`, SPA fallback rewrite |
| Demo banner | Absent (`/api/meta` reports `demo_mode: false`) | Rendered from `/api/meta` |

## Rollback

Nothing in this repository implements rollback (no release scripts, no versioned artifact storage, no migration-down tooling). The available mechanism is the Vercel platform's own deployment history: promoting a previous production deployment back to production is instant, and it restores that deployment's code and function configuration. State in `/tmp/cm` is not rolled back — it is ephemeral anyway and rebuilds from `seed_demo` on the next cold start. For local deployments, rollback is ordinary git plus re-running the build.
