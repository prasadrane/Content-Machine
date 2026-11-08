# C47: registered route and creator-isolation audit

Scope: worker checkout, 2026-11-07. This is an HTTP/data-selection boundary audit,
not hosted authentication provisioning, PostgreSQL integration, persistence durability,
or a deployed security certification. The parent runs final regression.

Evidence is exact worker source inspection plus the actual `app.routes` inventory
printed by `LegacyHttpTest.test_registered_surface_inventory`. The supplied graph
project is `C-Users-mamat-Github-Content-Machine`, generation
`2026-11-07T16:23:13Z`; `.orchestration` is explicitly excluded. No graph completeness
claim is made for this worker. Relevant source: `content_machine/api/app.py`,
`api/index.py`, `vercel.json`, `workflow/{routes,action_routes,discovery_routes,
preference_routes,settings_routes,writing_routes,operation_recovery,access,http,
context,operations,settings,preferences,runtime,writing_adapters,reviews}.py`,
`storage/paths.py`, `profile/manager.py`, `knowledge/provider.py`.

## Complete registration inventory

There are 59 registrations with the checked-in UI build present: 29 workflow,
22 legacy, two public API, four framework documentation, one static mount, one SPA.
Multiple methods on the same path are shown together below; each method is an
independent registration except the framework GET/HEAD pairs. No other mount or
file-serving route appeared in the runtime inventory.

All workflow paths below have prefix `/api/workflow`. They resolve the trusted
principal; data routes open a request-scoped connection after authentication.

| Methods | Relative path | Private material / protection |
|---|---|---|
| POST, GET | `/items` | Owner-bound create/list, item titles/context/artifacts |
| GET, PATCH | `/items/{item_id}` | Owner-bound item plus owned review/approval; CAS saves |
| GET | `/capabilities` | Authenticated principal and static format/provider capability metadata; no DB |
| GET | `/items/{item_id}/versions` | Owned immutable history |
| GET | `/items/{item_id}/versions/{version_id}` | Owned item/version snapshot |
| GET | `/items/{item_id}/exports/{version_id}` | Owned approved exact bytes or JSON; no caller-selected file path |
| POST | `/items/{item_id}/skip-review` | Owned decision and frozen input |
| POST | `/items/{item_id}/approve` | Owned exact artifact/revision approval |
| POST | `/items/{item_id}/restore` | Owned source version and target item |
| POST | `/items/{item_id}/adapt` | Owned approved anchor and derivative |
| POST | `/discovery/refresh` | Only enabled owned sources; no global connector history |
| GET, POST | `/preferences` | Owner-filtered preference list/create |
| GET | `/preferences/{preference_id}/history` | Owned preference/event history |
| PATCH | `/preferences/{preference_id}` | Owned revision-checked edit |
| POST | `/preferences/{preference_id}/activate` | Owned consent/revision-checked activation |
| POST | `/preferences/{preference_id}/stop` | Owned revision-checked stop |
| POST | `/preferences/{preference_id}/reject` | Owned revision-checked rejection |
| GET | `/settings` | Owned profile and configured source list |
| PUT | `/settings/profile` | Profile keyed by resolved owner; no caller owner selection |
| POST | `/settings/sources` | Creates source for resolved owner |
| PATCH | `/settings/sources/{source_id}` | Owned source ID plus expected revision |
| GET | `/items/{item_id}/operations` | Owned generation/review result history |
| GET | `/items/{item_id}/operations/{operation_id}` | Owned operation and frozen editorial input |
| POST | `/items/{item_id}/generate` | Owned frozen input, proposal only; no global persona |
| POST | `/items/{item_id}/review` | Owned frozen input/review result; no global persona |
| POST | `/items/{item_id}/operations/{operation_id}/abandon` | Owned confirmed terminal outcome; late completion cannot replace it |

The 22 legacy registrations below are intentionally unsupported when hosted.
Middleware returns `410 legacy_unavailable` before route parsing, dependencies,
storage, connector/browser access or model execution, including mismatched methods.
Local legacy callers retain their existing single-operator semantics.

| Methods | Path | Global private data or side effects denied in hosted mode |
|---|---|---|
| POST | `/api/oracle/run` | Global spikes/feed caches, connector credentials, model router |
| GET, POST | `/api/oracle/scan-stream` | Same; streamed results and request/environment LinkedIn cookie |
| GET | `/api/oracle/history` | SQLite spikes and raw score/sample history |
| POST | `/api/council/run` | Global profile/knowledge, iterations, draft content and model calls |
| GET | `/api/council/history/{spike_id}` | Iterations and draft bytes, including database `draft_path` file fallback |
| GET | `/api/council/spikes` | Unscoped project/score history |
| GET | `/api/lessons` | Global SQLite active/pending rules |
| POST | `/api/lessons/{rule_id}/approve` | Global lesson approval |
| POST | `/api/lessons/{rule_id}/reject` | Global lesson rejection |
| POST | `/api/lessons/custom` | Global rules and optional automatic approval |
| POST | `/api/lessons/diff` | Draft/published input, model extraction and global proposals |
| POST | `/api/distribute/run` | Anchor input/model context and project Markdown bundle writes |
| GET | `/api/distribute/history` | Global SQLite and filesystem enumeration, anchor/draft/bundle contents |
| GET | `/api/linkedin/status` | Global browser/session metadata and local profile directory |
| POST | `/api/linkedin/sync` | Browser cookie/session extraction and persistence |
| POST | `/api/interview/brief` | Input/source material and global model configuration |
| POST | `/api/interview/synthesize` | Raw lived-experience notes, global voice/model context and transcript/project writes |
| POST | `/api/interview/transcribe` | Uploaded audio, temporary files, local speech model execution |
| GET, POST | `/api/profile` | Reads/updates process-global `knowledge/02_voice-guide.md` |
| POST | `/api/humanize` | Draft/model processing with global editorial context |

Remaining registrations:

| Methods | Path | Exposure |
|---|---|---|
| GET | `/api/health` | Public constant health status; no storage |
| GET | `/api/meta` | Public demo/model-route category from server environment; no creator data |
| GET, HEAD | `/openapi.json` | Framework schema; route/model shapes, no stored creator records |
| GET, HEAD | `/docs` | Public Swagger HTML |
| GET, HEAD | `/docs/oauth2-redirect` | Public Swagger redirect HTML |
| GET, HEAD | `/redoc` | Public ReDoc HTML |
| MOUNT (GET/HEAD static handling) | `/assets` | Only `_UI_DIST/assets`; conditional on built UI, `follow_symlink=False` |
| GET | `/{full_path:path}` | Fixed `_UI_DIST/index.html` or UI-not-built message; never requested path bytes. API paths explicitly 404. |

`FileResponse` occurs only for the fixed SPA index. Export uses a plain response
from owned stored artifact bytes. No production home, projects, knowledge, audio,
archive or SQLite directory is mounted. The static build directory is public:
private files must never be placed in it. Static containment and symlink safety
remain Starlette's responsibility. Vercel serves `ui/dist` and rewrites `/api/*`
to `api/index.py`; source inspection covers that configuration, not a live deploy.

## Identity and global-state selection

`access.resolve_principal` accepts only the server-owned hosted authenticator's
`hosted_verified` Principal. Headers, query/body owner IDs and forwarding headers
are not identity selectors. Missing auth fails closed before opening storage.
Explicit trusted-local identity requires an actual loopback peer and configured
owner and is forbidden in hosted mode, including presence of `VERCEL`.

The old SQLite tables, project files and Markdown persona lack creator isolation;
C47 denies their HTTP entry points instead of relabeling them as multi-user.
Supported workflow reads use owner predicates and nested item/version/operation
relationships. `context.build_editorial_snapshot` captures owned profile,
preferences, version/context and title. `writing_adapters` serializes that snapshot;
review uses explicit snapshot editorial context rather than loading global voice
Markdown. Shared model credentials/configuration and the frozen rubric are server
configuration, not creator identity selectors. A browser never sets a DB path.

The connection factory is trusted server configuration. If absent,
`http.get_workflow_connection` still falls back to the legacy `_make_db` seam;
owner-filtered workflow tables protect this SQLite use, but the fallback is NOT
proof of hosted durable storage. Hosted auth adapter wiring, PostgreSQL service
coverage/RLS, restart durability and platform persistence are separate work.
Likewise, explicit future `import_legacy` service usage is not exposed as a route
and requires its own authorized migration decision.

## Reproduced failure and repair

A failing test demonstrated that the old broad prefix gate changed unknown API
paths into 410, including `/api`, `/api/not-a-route`, `/api/profile/not-a-route`
and `/api/workflow-other`. The repaired middleware checks actual API registrations
using Starlette route matching. Known private routes, even wrong HTTP methods,
remain 410; unknown non-workflow API paths are 404. This prevents the SPA catch-all
from defining a private route. Workflow unknown paths continue normal API routing.
The fix touches no app/bootstrap/static registration code.

## Verification and practical limits

All checks use the serialized production-storage guard, disposable SQLite storage,
injected authenticators/providers and no external services. The red run reproduced
the unknown-API regression (plus corrected an initial route-count expectation from
25 to the actual 22). Final focused command:

```powershell
& 'C:/Users/mamat/AppData/Local/Microsoft/WindowsApps/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/python.exe' 'C:/Users/mamat/Github/Content-Machine/.orchestration/controller/batch-test-runner.py' --kind backend --worker c47 -- -m pytest tests/test_workflow_legacy_http.py tests/test_workflow_legacy_boundary.py tests/test_workflow_legacy_selectors.py tests/test_hosted_entry.py tests/test_workflow_api_actions_ownership.py tests/test_workflow_access.py tests/test_workflow_settings.py tests/test_workflow_preferences.py tests/test_workflow_context.py tests/test_workflow_operation_recovery_api.py tests/test_workflow_operations.py tests/test_workflow_writing_api.py -q -s
```

Log: `.orchestration/controller/direct/ten-c47-focused.txt` (from repository root).
Final result: **70 passed in 10.49s**; the log contains all 59 registration lines.
The only emitted warning was pytest-asyncio's unset default fixture loop scope.

Coverage exercised:

- Actual registration inventory, all 22 legacy registrations across GET/POST/PUT/
  PATCH/DELETE/HEAD with forged identity and invalid JSON, asserting no DB/router/
  profile construction. Vercel-presence gating and local legacy compatibility.
- Creator B cannot retrieve A's item, source/profile/settings or preference history,
  mutate A's source/preference, select A via headers/query/configured local owner,
  or contaminate B's generation snapshot by changing the global home. Legacy path
  access is patched to fail. A's settings/preferences remain intact afterward.
- Existing owned history/export/restore/adapt/approval nested-ID denial, immutable
  context, request authentication and local-loopback rejection, settings/preferences
  owner filtering, operation read denial, and abandoned operation late completion.
- Only build assets mounted with symlink following disabled; SPA deep links and
  private-looking paths return the fixed UI. Unknown API GET paths remain 404.
- Hosted entry does not seed a synthetic home, shared demo data or ephemeral DB.

Not performed: full suite/build (parent-owned), live auth/JWKS, real provider calls,
real user storage inspection, real-hosted persistence, Vercel request/asset tests,
or operating-system hostile symlink races. This bounded route/data-selection audit
must not be represented as those checks.
