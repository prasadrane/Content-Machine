# Security Policy

## Scope

Content Machine is a personal, local-first portfolio project: a single-user
editorial engine with a public Vercel demo. This document describes the
security-relevant properties of the code as it exists. The project makes no
security certification and offers no guarantees of confidentiality,
integrity, or availability.

## Reporting a vulnerability

Prefer GitHub's private vulnerability reporting on
[github.com/prasadrane/Content-Machine](https://github.com/prasadrane/Content-Machine)
("Report a vulnerability" under the Security tab), if enabled for this
repository. The repository publishes no security contact address; if private
reporting is unavailable, reach the owner through the contact channels on their
GitHub profile ([github.com/prasadrane](https://github.com/prasadrane)).

## Security posture

This is a description of mechanisms, not a claim of security.

### Local deployment

- The tool is a single-user local application. It implements no
  authentication or authorization layer, by design for that use case.
- The API server (`python -m content_machine serve`) runs uvicorn bound to
  `127.0.0.1` on port `8000` by default (see `--host`/`--port` in
  `content_machine/__main__.py`). Anything reachable at that address can call
  every endpoint; do not expose the port on untrusted networks.
- State is a local SQLite database plus markdown files under
  `CONTENT_MACHINE_HOME` (default `~/.content_machine`).

### Secrets

- Provider credentials are read from environment variables only
  (`GEMINI_API_KEY`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`; see
  `config.json` route definitions). No secret values are committed.
- `.gitignore` excludes `.env` and `.vercel/`.
- The demo Gemini key lives only in the Vercel project's environment
  configuration, not in this repository.

### Public demo

- The deployed demo (`content-machine-chi-lac.vercel.app`) runs the same code
  with `DEMO_MODE=1` (`api/index.py`), which switches all model routes to
  Gemini flash (`content_machine/config.py`) and serves purely synthetic
  data (`content_machine/demo_seed.py`): fictional persona, invented
  comments/drafts/lessons; scores and verdicts are synthetic.
- POST `/api/*` requests are limited per client IP to 10 per 60-second
  window (`content_machine/api/rate_limit.py`), bounding free-tier LLM quota
  consumption. The limit is in-memory, so it applies per serverless instance.
- The demo depends on a free-tier quota and may degrade or stop mid-request;
  this is stated in the README.

### Input handling

- All API request bodies are validated by Pydantic models at the FastAPI
  boundary (`content_machine/api/app.py`), and model output is schema-checked
  before use (`content_machine/router/`).
- Project slugs are rejected if they contain path separators or lead dots
  (`content_machine/storage/paths.py: project_dir`).

### Data handling

- Voice and knowledge files (`knowledge/*.md`, the runtime persona guide) can
  contain personal editorial constraints. They stay in local storage; under
  `DEMO_MODE` seed syncing is disabled (`content_machine/storage/paths.py`)
  and the persona file is replaced with the synthetic guide
  (`content_machine/demo_seed.py`), so real persona content is not served by
  the demo.

## Dependencies

Python dependencies are pinned/tracked in `requirements.txt`, UI
dependencies in `ui/package.json` / `ui/package-lock.json`. The CI workflow
(`.github/workflows/ci.yml`) runs backend and UI tests only; no automated
dependency-vulnerability scanning (Dependabot alerts, CodeQL, audit jobs) is
currently configured.
