# Workflow AI runtime

Workflow generation and Council review use committed operation inputs. A generated result is a proposal. Accepting it saves a new working revision, and the author must approve that revision before export.

## Configuration

Set `CONTENT_MACHINE_WORKFLOW_AI=1` on the server to enable the existing configured model router for workflow requests. Leave it unset to retain manual drafting with explicit review skip. The runtime loads `config.json` through the existing configuration loader and resolves server-side credential references through the existing bootstrap. Provider failures become failed operation records with generic public messages.

The runtime uses `models.writer` for drafting and `models.council` for independent Council judges. The frozen rubric stays in `council/rubric_v1.md`. Council advice reports its raw 0–10 basis. Owner-specific score calibration remains pending, so normalized scores are absent.

Server integrations and offline tests can inject `app.state.workflow_generator(snapshot)` and `app.state.workflow_reviewer(snapshot)`. Explicitly setting either to `None` disables that action even when the environment opt-in is present. Capability responses expose `can_generate` and `can_review` from these installed callables. They describe configured actions. Individual requests can still fail, including unavailable model credentials or provider outages.

## Retry behavior

Generation and review require an `Idempotency-Key` and the acknowledged working revision. The operation and immutable editorial input commit before provider work starts. Replaying a completed or failed request returns its stored outcome. A pending operation remains pending after an interrupted process. The current status endpoint reports that state, and does not repeat a possibly completed provider request automatically.

Provider output never replaces the working draft automatically. The proposal retains its original item and input-version identity. Changed or unsaved content makes the proposal earlier advice, and explicit acceptance is refused until the author returns to a matching saved version or starts a fresh request.

## Verification boundaries

Offline HTTP and adapter checks use recorded provider fixtures. Real relay calls, Cloudflare model availability and quality, hosted private storage, and deployment configuration require separate verification. Keep tokens outside repository files and browser bundles.
