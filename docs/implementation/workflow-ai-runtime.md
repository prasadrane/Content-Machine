# Workflow AI runtime

Workflow generation and Council review use committed operation inputs. A generated result is a proposal. Accepting it saves a new working revision, and the author must approve that revision before export.

## Configuration

`CONTENT_MACHINE_WORKFLOW_AI` selects the router:

| Value | Behavior |
| --- | --- |
| `0` | Off. Manual drafting with explicit review skip. |
| `1` | Legacy: the configured `config.json` router (relay), exactly as before. |
| `auto` | Free-provider router (`router/free_providers.py`). Never uses the relay or a paid route. |
| unset or blank | `auto` on a hosted deployment (`CONTENT_MACHINE_DEPLOYMENT_MODE=hosted` or `VERCEL`), otherwise off, so local development and tests are unchanged. |

In `auto` mode the actions are available (`can_generate` / `can_review`) only when at least one free provider has credentials. The legacy runtime loads `config.json` and resolves credential references through the existing bootstrap. Provider failures become failed operation records with generic public messages.

### Free providers (auto mode)

Providers are tried in registry order; any provider or model failure falls through to the next. Override the order or subset with `CONTENT_MACHINE_AI_PROVIDERS` (comma-separated names). A provider is available only when its credentials are set.

| Provider | Credential variables | Pool | Unit | Timeout |
| --- | --- | --- | --- | --- |
| `cloudflare_workers_ai` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | `cloudflare-guest` | millineurons | 30 s |
| `gemini` | `GEMINI_API_KEY` | `gemini-guest` | requests | 25 s |

### Quota metering

Every verified hosted principal (anonymous guest and signed-in user) is metered against the shared free tiers; per-subject caps stop one identity draining a pool. Trusted-local mode (no hosted verifier) is unmetered. If the signed session cannot be verified the request fails closed with `ai_session_unavailable`.

All quota variables are optional. Missing values use the default; a present but invalid value fails closed with `503 guest_budget_unconfigured`.

| Variable | Default | Meaning |
| --- | --- | --- |
| `CONTENT_MACHINE_GUEST_AI_MAX_INPUT_BYTES` | 12000 | Largest request payload (UTF-8 bytes) |
| `CONTENT_MACHINE_GUEST_AI_PER_CALL_MILLINEURONS` | 1200000 | Cloudflare reservation per call (must cover the input bound plus 2000 output tokens) |
| `CONTENT_MACHINE_GUEST_AI_DAILY_MILLINEURONS` | 9000000 | Cloudflare daily pool (at most 10000000, at least the per-call value) |
| `CONTENT_MACHINE_GUEST_AI_MAX_INFLIGHT` | 4 | Cloudflare concurrent calls (1 to 4) |
| `CONTENT_MACHINE_GUEST_AI_GEMINI_DAILY_REQUESTS` | 100 | Gemini requests per UTC day (1 to 1000000) |
| `CONTENT_MACHINE_GUEST_AI_GEMINI_MAX_INFLIGHT` | 4 | Gemini concurrent calls (1 to 8) |

Each call reserves units before dispatch: Cloudflare reserves the per-call bound, Gemini reserves one request. Per-subject daily cap is `max(units * inflight * 2, daily // 4)`; per-subject in-flight cap equals the pool in-flight cap. Output is capped at 2000 tokens.

Changing a daily limit mid-day makes that pool answer `guest_budget_policy_conflict` until the next UTC day, because the first reservation of the day commits the spend policy. Change it at the UTC day boundary. A changed in-flight value is a concurrency limit, not a spend commitment: the next reservation updates the stored policy for the day and proceeds.

In-flight slots are leased. The reservation key is `<operation_id>:<epoch_seconds>:<hex>`. A row in state reserved, dispatched or uncertain holds a pool and per-subject slot only while `now - epoch <= 120` seconds (`LEASE_S`), so timeouts or crashes free their slot after two minutes instead of blocking the pool until midnight. Rows whose key does not parse (written before this change) or that are older than the lease hold no slot. Spend accounting is unchanged: such rows still count their charged units toward the daily limit. A call that settles normally frees its slot immediately.

### Fallthrough, settlement and time budget

- Quota rejections on one pool (`guest_budget_exhausted`, `guest_budget_busy`, `guest_budget_subject_exhausted`, `guest_budget_subject_busy`) do not fail the request: the router tries the next provider. If every provider was unavailable for quota and nothing was dispatched, the most informative quota error (HTTP 429) is returned. Other workflow errors stay fatal.
- A provider that answered with an HTTP rejection and produced nothing (`ProviderRejected`) is settled at 0 units, freeing its in-flight slot. A timeout, network failure or unknown error stays `uncertain`: the full reservation is charged and the slot is held, because the provider may still have run.
- A request has about 50 s overall. Each attempt gets `min(provider timeout, remaining - 3 s)`. With under 5 s left no further provider is dispatched, and Council review falls back to local cleanup wording.

### Adding a provider

1. Add an adapter under `content_machine/router/` exposing `complete(model, prompt, *, system, schema, **kwargs)` that raises `ProviderRejected` for responses without output and `ProviderError` otherwise.
2. Add a builder (keyed by protocol in `_BUILDERS`, or a `builder` on the entry) and a `FreeProvider` entry in `REGISTRY` with its pool name, unit label, native models, `free-strong` / `free-fast` aliases, timeout and `cost`.
3. Add its pool policy to `ProviderExecution._policy` and optional quota variables to `_DEFAULTS` in `workflow/provider_execution.py`. Pools are free-text rows, so no schema migration is needed.
4. Add tests next to `tests/test_workflow_free_provider_execution.py`.

The runtime uses `models.writer` for drafting and `models.council` for independent Council judges. The frozen rubric stays in `council/rubric_v1.md`. Council advice reports its raw 0–10 basis. Owner-specific score calibration remains pending, so normalized scores are absent.

Server integrations and offline tests can inject `app.state.workflow_generator(snapshot)` and `app.state.workflow_reviewer(snapshot)`. Explicitly setting either to `None` disables that action even when the environment opt-in is present. Capability responses expose `can_generate` and `can_review` from these installed callables, or from the selected mode and credentials. They describe configured actions. Individual requests can still fail, including unavailable model credentials or provider outages.

## Retry behavior

Generation and review require an `Idempotency-Key` and the acknowledged working revision. The operation and immutable editorial input commit before provider work starts. Replaying a completed or failed request returns its stored outcome. A pending operation remains pending after an interrupted process. The current status endpoint reports that state, and does not repeat a possibly completed provider request automatically.

Provider output never replaces the working draft automatically. The proposal retains its original item and input-version identity. Changed or unsaved content makes the proposal earlier advice, and explicit acceptance is refused until the author returns to a matching saved version or starts a fresh request.

## Verification boundaries

Offline HTTP and adapter checks use recorded provider fixtures. Real relay calls, Cloudflare model availability and quality, hosted private storage, and deployment configuration require separate verification. Keep tokens outside repository files and browser bundles.
