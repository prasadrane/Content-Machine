# Content Machine implementation plan for Freebuff

Prasad will give this document to Freebuff directly. Freebuff implements one assigned checkpoint and returns its evidence. Prasad accepts the checkpoint or requests a repair, with an independent code review when needed. Read the common instructions and the currently assigned checkpoint, then stop at its boundary.

- Product decisions are in `docs/ui-workflow-plan.md`.
- Record and endpoint contracts are in `docs/implementation/workflow-contract.md`.
- The full machine-readable task inventory is in `docs/implementation/workflow-tasks.json`.
- Supabase and guest decisions are in `docs/implementation/hosted-workspace-decision.md`.
- Cloudflare candidates and setup are in `docs/research/free-ai-providers-2026-11-06.md` and `docs/implementation/cloudflare-workers-ai-setup.md`.

This handoff governs task order, current filenames and review procedure. The frozen contract governs existing records, API payloads and approval semantics. Confirmed product decisions in this document and the hosted decision record supersede older open-decision notes. The manifest's historical controller/session metadata is background evidence. Keep implementation aligned with the current source and record any necessary contract amendment before changing a shared API or migration.

## Current handoff state

- The original checkout is `C:\Users\mamat\Github\Content-Machine`. The implementation checkout is `C:\Users\mamat\Github\Content-Machine\.orchestration\worker` on branch `codex/workflow-implementation`.
- The last inspected implementation commit is `362814e1e0220cad84795be519bde264ead8262e`. C00 through C09 were accepted in earlier checkpoints. Verify the current HEAD and status before beginning because both can change. Their acceptance is historical evidence and does not imply that later uncommitted changes are accepted.
- C10 and parts of C11 through C19 and C43 have uncommitted, unreviewed work. Those edits include API actions, the API client, platform icons, emoji removal, the application shell and a partial workflow hook. `ui/src/app/tabs.js` imports `ui/src/components/workflow/WorkflowTab.jsx`, which is absent in the current checkout. The current production build fails at that missing import. Start with the recovery task below.
- The tracked planning changes in the original checkout and the untracked implementation files are intentional working state. Inspect staged, unstaged and untracked files before changing anything. Preserve work already present and review each change before replacing it.
- In the last inspection, 18 workflow action/item API tests passed. The frontend build failed at the missing `WorkflowTab` import. Recheck both results against the current files during R00. Treat that frontend failure as a recorded baseline defect until the owning UI checkpoint repairs it.

## Execution order and review ownership

1. Prasad submits the first prompt at the end of this document. Freebuff performs the read-only R00 audit and returns a report.
2. Prasad reviews that report and assigns C10. Accept and repair C10 before proceeding through C11 to C20.
3. Complete C21 through C29 for creator settings, preferences, discovery, dictation and editorial context.
4. Complete F01 and F02 for the Cloudflare adapter and explicit configuration. Complete C30a, C30b and C30c, then C31 through C37. Existing supported routes can be exercised offline with mocked providers while Cloudflare credentials are pending.
5. Complete C38 through C44. Review existing navigation and emoji changes within their owning checkpoints instead of repeating completed edits.
6. Complete C45's hosted design and configuration checklist, then H01 through H06 as the implementation children of C46. Use H07 as the C47 isolation audit. Complete F04 before enabling public guest AI.
7. Run F03 when the Cloudflare account is configured. Complete C48, C49 and C50 after the required hosted and provider prerequisites are available.

The first local milestone is C20, a verified manual Idea → Draft & review → Approve → Export journey. Hosted release readiness requires the later live identity, durable storage, guest-budget, recovery and accessibility checks. Use the same acceptance gates if a checkpoint is already partly implemented.

## Product outcome

The first page is Workflow with four stages named Idea, Draft & review, Approve and Export. Lessons and Settings remain available in the main navigation. Resume begins from actual saved work. An author's own material and discovery are equally prominent starting points. Select one platform first and support optional linked adaptations later.

The application serves engineering and technical creators first. Keep LinkedIn, X, YouTube, newsletter and generic script formats, and add Instagram captions and Reel scripts. Platform choices use recognizable logos with visible labels. Remove decorative UI emoji and the separate Audio page. Place dictation beside the actual input fields.

AI output uses real source material and user-supplied experience. The user may explicitly skip AI review. Human approval binds the precise saved item, version, destination, format and digest. Export copies or downloads the exact approved text for manual publication.

Hosted creator workspaces use Supabase Auth and Postgres, with Google sign-in. Guest mode is explicit, has clearly labelled example ideas and drafts, allows live AI, preserves guest work across visits and offers a user-controlled transfer after sign-in. Private creator workspaces contain actual creator records. Keep guest and creator ownership isolated.

## Recovery task R00

R00 is an audit with evidence collection. It produces an inventory and a proposed sequence of scoped repairs. Application and test edits begin with the next assigned checkpoint.

1. In the implementation checkout, run `git status --short --untracked-files=all`, `git diff --check` and `git diff`. Include untracked files in review. Exclude `.worker-evidence/` and `worker-report.json` from product commits, while preserving them as evidence.
2. Inspect `content_machine/workflow/action_routes.py`, `skip_review.py`, `routes.py`, `tests/test_workflow_api_actions.py`, `ui/src/api/workflow.js`, `ui/src/components/workflow/`, `ui/src/lib/platforms.js`, `ui/src/components/ui/PlatformIcon.jsx`, `ui/src/App.jsx`, `ui/src/app/tabs.js`, and the changed Oracle/Council files. Identify which changes are complete, incomplete or inconsistent with the frozen contract.
3. Identify the work needed to finish the existing changes. The workflow component is missing, so the current shell cannot build. Use `WorkflowTab.test.jsx`, the existing `useWorkflow.js` and `workflowUtils.js` as starting evidence. Check their behavior before choosing whether to adapt or reorganize them.
4. Run the existing C10 action/item API tests. Inspect whether they cover ownership, compare-and-set, idempotency replay/conflict, explicit skip, exact approval/export, adaptation/restore and a real deferred commit failure. List missing scenarios for C10 to implement. Preserve the actual failing and passing output.
5. Check actual capability readiness. The new workflow generation route has not yet been connected. A platform must report `can_generate: false` until the selected-format workflow adapter really works through the normal API.
6. Run the focused backend checks, the relevant frontend tests and a Vite build. Record exact commands, exit codes, counts and any unperformed checks. A successful test for one slice does not accept the entire branch.
7. Return the base commit, changed-file inventory, checks run, observed defects, missing test coverage and the proposed first C10 scope. Prasad accepts the audit report and assigns the next checkpoint. Existing files receive the same review as new implementation.

## Working protocol for every checkpoint

1. Read `AGENTS.md`, applicable scoped instruction files, the relevant contract section, the checkpoint below and existing source. Determine the current HEAD and the files already changed.
2. Work in the implementation checkout. The listed paths define the feature scope. Small helpers and tests in the same feature may be added when needed for correctness or the size target, and must be listed in the report. Shared schema, authentication, storage, dependency or cross-feature changes require a concrete scope update from Prasad before editing. Preserve changes made by others.
3. Write meaningful failing tests before implementation. Keep the actual failing command and output. Implement the smallest complete change, then run the same checks to green. Use real temporary SQLite for persistence tests and mock only external boundaries.
4. Send frontend network calls through `ui/src/api/`. Reuse existing backend services and `cm-*` style tokens. Keep new feature modules readable and within the repository's file-size rules. Preserve existing caller behavior and historical data.
5. Use the guarded launcher for every Python test command. It creates disposable `CONTENT_MACHINE_HOME`, blocks access to the creator's real storage and credential files, and disables dotenv discovery. Preserve this test launcher as supplied.
6. Check the diff, including untracked files. Report the exact changed paths, test commands, exit codes, passing/failing counts and unresolved issues. Report a missing credential or external dependency as a blocker. Keep secrets out of prompts, source, logs and reports.
7. Stop at the checkpoint boundary. Prasad or the designated reviewer inspects the exact diff and evidence and records acceptance or a concrete repair request. Make that repair, rerun the affected checks and return for review. Advance after acceptance.

Each report must name the checkpoint, base commit, changed files, behavior implemented, commands and exit codes, test counts, unresolved issues and unperformed checks. A failed external prerequisite leaves that check pending. Never replace a failure with fabricated content or a passing status. Commit, push, real-data migration and deployment require Prasad's applicable instruction at the release step.

Use these PowerShell commands. Verify that the named executables and launcher exist before the first run. If a temporary executable path has expired, locate an installed compatible Python or Node executable and report the resolved path. If the guarded launcher is missing, request its restoration before Python tests.

```powershell
Set-Location -LiteralPath 'C:\Users\mamat\Github\Content-Machine\.orchestration\worker'
$cmPython = 'C:\Users\mamat\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe'
$cmGuard = 'C:\Users\mamat\Github\Content-Machine\.orchestration\controller\guarded-test-runner.py'
& $cmPython $cmGuard -m pytest tests/test_workflow_api_actions.py -q
& $cmPython $cmGuard -m unittest discover -s tests
```

```powershell
Set-Location -LiteralPath 'C:\Users\mamat\Github\Content-Machine\.orchestration\worker\ui'
$cmNode = 'C:\Users\mamat\AppData\Local\Temp\content-machine-node22\node_modules\node\bin\node.exe'
& $cmNode node_modules/vitest/vitest.mjs run src/api/workflow.test.js --maxWorkers=2
& $cmNode node_modules/vite/bin/vite.js build --outDir 'C:\Users\mamat\Github\Content-Machine\.orchestration\controller\plan-build'
```

For a Python checkpoint, replace the focused pytest path with that checkpoint's listed test and retain the guarded unittest regression. For a frontend checkpoint, pass its listed test relative to `ui` into Vitest. C50 additionally runs guarded full pytest, the entire frontend suite and the production build. Record a known baseline failure separately from a new regression.

Before live checks, the reviewer confirms the chosen account, free allocation and model availability. Offline tests use fixtures and mocks. Live results, browser checks, hosted tests and deployment checks are recorded separately from offline results.

## Cloudflare implementation packets

Cloudflare Workers AI is the selected first free-provider evaluation. Add these bounded packets after the local editorial context exists and before claiming workflow generation is ready.

1. **F01, compatible adapter.** Add an explicit OpenAI-compatible Chat Completions adapter and tests for authentication headers, provider-native model IDs, timeouts, bounded retries, rate-limit responses, malformed responses and local schema validation. Exercise both the shared API/CLI bootstrap and the retained router factory. Preserve existing Messages and Gemini routes.
2. **F02, explicit routing.** Add configuration for the selected Cloudflare account, token environment variable and approved model IDs. Resolve credentials only in the server process. Record actual model/provider metadata with each operation. Keep existing routes until a configured new route passes its checks.
3. **F03, bounded evaluation.** With the configured account and free-eligible model, run a small opt-in live evaluation using non-sensitive engineering fixtures. Record actual response quality, grounding, JSON validity, latency, usage and failure handling. Do not infer editorial quality from model listings.
4. **F04, guest budget.** Enforce a durable server-side shared guest budget across instances. Check concurrency, retry and quota exhaustion. A free-only route requires an explicit configuration decision before paid fallback. Preserve saved input and show actionable failures when AI is unavailable.

The local Cloudflare account ID and token are pending configuration. The Windows setup guide describes the controller-owned encrypted credential file. The implementer receives only variable names and test fixtures.

## Hosted implementation packets

C45 records the Supabase design and known configuration prerequisites. C46 consists of H01 through H06 below. Complete offline code, migrations and tests using configuration variables and disposable data. The actual Supabase project, region, redirects, connection mode and credentials are required for live hosted verification. Keep the local SQLite entry point working.

1. **H01, storage contract.** Map every owned item, version, review, approval, operation, preference, idempotency and guest-transfer record to Postgres. Add versioned additive migrations, foreign keys, immutable history, uniqueness and owner-scoped row policies. Test repeat migration, rollback, concurrent CAS and retry behavior.
2. **H02, verified identity.** Verify Supabase access tokens against the configured issuer, audience, expiry and signing keys. Resolve the principal once on the server. Test missing, forged, expired, wrong-audience and cross-owner requests. Server credentials and privileged roles require explicit owner filtering even where database policies are bypassed.
3. **H03, durable workflow services.** Implement transactional Postgres persistence for every accepted workflow operation. An HTTP success follows a committed write. Test actual concurrent writes and idempotency replay. Never use Vercel's temporary filesystem as the durable source of truth.
4. **H04, browser session.** Add Google sign-in, session refresh and sign-out through supported Supabase APIs. Restore the signed-in creator's own workspace after reload. Test expired sessions, callback failures and unavailable services without erasing unsaved input.
5. **H05, guest workspace.** Create a distinct anonymous identity and an idempotent, clearly labelled example bootstrap for that guest. Preserve guest-created edits across return visits. Live AI writes real operation records under the guest owner.
6. **H06, guest transfer.** After Google sign-in, offer transfer explicitly. Verify both identities, preserve content and provenance, make transfer transactional and retry-safe, and retain recoverable guest work on failure. Exercise duplicate requests and cross-owner attacks.
7. **H07, legacy isolation and recovery.** Inventory every old route and file path. Scope or explicitly disable unsupported global-data surfaces in hosted mode. Rehearse legacy import only on a backup with explicit ownership assignments. Verify A/B isolation, restart durability and rollback before hosted release.

Use these initial file scopes for the hosted children. H01 must settle the persistence interface and transaction ownership before any service refactor. Existing services contain SQLite-specific SQL and connection behavior, so test the selected database boundary explicitly. Preserve the accepted local behavior while adding Postgres.

| Child | Initial file scope | Required evidence |
| --- | --- | --- |
| H01 | `docs/implementation/hosted-workspace-decision.md`, `supabase/migrations/202611060001_workflow.sql`, `tests/test_workflow_postgres_schema.py` | Reviewed storage interface, complete table/policy migration, repeated migration, immutable history and owner constraints |
| H02 | `content_machine/workflow/hosted_auth.py`, `content_machine/workflow/access.py`, `content_machine/api/app.py`, `tests/test_workflow_hosted_auth.py` | Existing authenticator boundary verifies signed sessions, rejects forged/expired tokens, opens no workspace before authentication |
| H03a | `content_machine/workflow/postgres.py`, `content_machine/workflow/http.py`, `tests/test_workflow_postgres.py` | Real disposable Postgres connection/transaction tests, rollback and committed acknowledgements |
| H03b | `content_machine/workflow/persistence.py`, `items.py`, `versions.py` and their tests | Each service works against the reviewed database interface, with real CAS, unique request keys and immutable snapshots on both supported stores |
| H03c | Existing approval, export, history, adaptation, skip, generation, review, settings and preference services, one service per review | The original ownership, exact-text, retry and rollback cases pass for each migrated service |
| H04 | `ui/src/api/auth.js`, `ui/src/api/client.js`, `ui/src/app/useAuthSession.js`, `ui/src/components/auth/WorkspaceAccess.jsx`, app integration and focused tests, `ui/package.json` and lockfile | Google callback, session refresh, authenticated transport, sign-out and session-expiry tests preserve the right creator's work |
| H05 | `content_machine/workflow/guest_bootstrap.py`, its focused tests, authenticated route registration and guest entry UI | Idempotent labelled examples for one verified guest, preserved edits on return visits, no fabricated AI operation results |
| H06 | `content_machine/workflow/guest_transfer.py`, its focused tests, a versioned transfer migration, route and transfer dialog | Verified source/destination ownership, explicit consent, atomic retry-safe transfer, recovery on failure |
| H07 / C47 | `content_machine/workflow/route_access.py`, `content_machine/api/app.py`, `tests/test_workflow_route_access.py` | Complete route/file inventory and direct cross-owner attack tests for every retained hosted surface |

The paths above identify starting scopes. H03c is deliberately implemented as separate service packets, each named in its report. Prasad reviews changes to shared contracts or dependencies. Project credentials and live deployment access remain prerequisites for the live hosted gate.

## Splitting generation and retirement work

C30 and C43 are larger than one implementer packet. Use the following children in order, with a review after each child.

1. **C30a, generation snapshot purpose.** Start with `content_machine/workflow/schema_types.py`, `content_machine/workflow/migrations.py`, `tests/test_workflow_schemas.py`, `tests/test_workflow_migrations.py` and the contract document. Add an honest generation snapshot purpose. Write a migration test against a populated pre-change database, then an interrupted-migration and repeat-migration test. Preserve all versions, approvals, foreign keys and immutability triggers. Review the migration before applying it to any real data.
2. **C30b, operation lifecycle.** Start with new `content_machine/workflow/generation.py` and its focused test file. Freeze the owned acknowledged input, record an actual operation and request ID, and bind any proposal to that version. Define pending, failed, retry and concurrent-request behavior against the contract before writing the service. Keep network calls outside long database write transactions. A failed or duplicated request cannot create a false success or overwrite the creator's working content.
3. **C30c, generation API and UI.** Add the owned route in `content_machine/workflow/writing_routes.py`, register it through `content_machine/workflow/routes.py`, and add real TestClient cases. Connect the workflow client and stage only after the route passes. Set `can_generate` for each destination and format only when its complete adapter is exercised through this route.
4. **C43a, navigation.** Review the existing `ui/src/App.jsx`, `ui/src/app/tabs.js` and their tests. Expose Workflow, Lessons and Settings. Preserve the active workflow state on navigation, and preserve the separate hosted guest entry for its later packet.
5. **C43b, input and retirement.** Remove the standalone Audio registration while placing microphone controls beside real input fields. Verify recording permission denial, cancellation, delayed transcription and switching items cannot insert text into the wrong field.
6. **C43c, labels and icons.** Review the existing Oracle and Council edits, then inspect every remaining destination for decorative emoji. Keep stored creator text and legacy data unchanged. Use labelled, accessible icons and update tests for the intended UI text.

For F01 and F02, the initial review scope is `content_machine/router/`, `content_machine/bootstrap.py`, `content_machine/config.py`, `config.json` and focused router/bootstrap tests. For F03 use a separately named opt-in live test and redacted result. For F04 name the budget migration, backend service and concurrency tests in the packet after the durable store is selected. Apply the working protocol's rule for small helpers and shared-file scope changes.

## Checkpoint tasks

The following tasks retain the manifest's product requirements and acceptance checks, with handoff scopes corrected for the current files. C10 onward is pending review even when partial files exist. Reuse `useWorkflow.js`, `workflowUtils.js` and `WorkflowTab.test.jsx` while completing C13 through C19. The root workflow component is `WorkflowTab.jsx`. Split stage presentation into small components as needed. Include the existing icon license and Oracle/Council changes in their owning reviews.

### C10 — Expose history, approval and export actions

Dependencies C09

Work

- Write tests for version history, restore, approve, export and adaptation endpoints.
- Apply the same principal and revision contract to every action.
- Return exact text downloads with safe filenames and appropriate content types.
- Provide explicit review-skip state through the versioned workflow action contract.
- Register the subrouter in the workflow router and exercise it through TestClient against the normal app.
- Expose /api/workflow/capabilities from the backend registry and cover it through the normal app entry point.

Acceptance checks

- An unapproved working item cannot use the final-export action.
- Historical owned approved artifacts can be retrieved accurately.
- Failed or skipped AI review never supplies human approval.

Planned write paths

- `content_machine/workflow/action_routes.py`
- `content_machine/workflow/skip_review.py`
- `content_machine/workflow/http.py`
- `content_machine/api/app.py`
- `tests/test_workflow_api_actions.py`
- `content_machine/workflow/routes.py`

Focused test `tests/test_workflow_api_actions.py`

Review focus Unguarded file routes, filename collisions and state inferred from navigation

### C11 — Create a platform registry and recognizable icons

Dependencies C10

Work

- Map retained identifiers from constants.js and the approved capability inventory.
- Add Instagram caption and Reel-script identity/format definitions. Consume editing/generation readiness from the server capability response.
- Use reviewed licensed brand SVG assets with visible labels and consistent dimensions.
- Retain neutral script/newsletter choices where a specific provider is absent.

Acceptance checks

- Every retained format has one explicit destination/format mapping.
- An unavailable generation adapter is identified by the server capability response until its packet passes.
- Icons cannot imply an authenticated account or published content.

Planned write paths

- `ui/src/lib/platforms.js`
- `ui/src/components/ui/PlatformIcon.jsx`
- `ui/src/lib/platforms.test.js`
- `ui/src/components/ui/BOOTSTRAP-ICONS-LICENSE.txt`

Focused test `ui/src/lib/platforms.test.js`

Review focus Dropped legacy identifiers and generic scripts presented as platform-ready assets

### C12 — Add workflow domain API clients

Dependencies C11

Work

- Write request/response and error tests around fetchJson.
- Implement the approved item, history, skip, approve, export and adaptation calls.
- Pass revision and idempotency data explicitly.
- Preserve server conflict details for recovery UI.
- Load the authoritative capability response alongside item state.
- Add an authenticated binary download call that returns the server's exact response bytes and safe filename. Test errors, text content type and `Content-Disposition`, alongside the JSON segment export used for copy.

Acceptance checks

- Networking remains inside ui/src/api.
- Request fields match the frozen contract.
- An error response cannot be interpreted as an empty successful result.

Planned write paths

- `ui/src/api/workflow.js`
- `ui/src/api/workflow.test.js`

Focused test `ui/src/api/workflow.test.js`

Review focus Raw fetch in components and silently swallowed failures

### C13 — Manage acknowledged workflow state and saves

Dependencies C12

Work

- Write delayed-request tests for load, edit, debounce save, item switch and retry.
- Track local edits separately from acknowledged server revision.
- Apply returned state only to its owner/item/request generation.
- Expose Saving/Saved/Not saved, conflict and recovery without clearing typed content.

Acceptance checks

- A delayed save/load for A cannot replace B or newer A edits.
- Repeated retries use stable idempotency keys.
- Approval and final export wait for the current artifact's required acknowledgement.

Planned write paths

- `ui/src/components/workflow/useWorkflow.js`
- `ui/src/components/workflow/useWorkflow.test.jsx`
- `ui/src/components/workflow/workflowUtils.js`

Focused test `ui/src/components/workflow/useWorkflow.test.jsx`

Review focus False Saved labels, race conditions and errors that erase input

### C14 — Build the real saved-content landing

Dependencies C13

Work

- Write cases for loading, actual empty results, loaded items, no search matches and load failure.
- Show New content and a prominent Resume action naming its saved item.
- Use actual server status and updated time.
- Keep previously loaded items visible with an appropriate stale/error indication on refresh failure.

Acceptance checks

- Two same-title items remain distinguishable and independently resumable.
- A load failure never becomes No saved content.
- Scanned articles are absent until deliberately saved or used.

Planned write paths

- `ui/src/components/workflow/ContentList.jsx`
- `ui/src/components/workflow/ContentList.test.jsx`

Focused test `ui/src/components/workflow/ContentList.test.jsx`

Review focus Synthetic empty-state data and conflating discovery history with drafts

### C15 — Capture own material in the Idea stage

Dependencies C14

Work

- Write tests for platform/format selection, notes and an existing draft.
- Provide equally prominent Your idea and Discover ideas choices.
- Capture one optional intended point and source/context attachments through shared item state.
- Preserve a pasted draft exactly until an author edit or accepted suggestion.

Acceptance checks

- No profile or source setup is required for the own-material path.
- Changing stage preserves input and the selected destination.
- Choosing discovery can expose a truthful unavailable/loading state until discovery integration lands.

Planned write paths

- `ui/src/components/workflow/IdeaStage.jsx`
- `ui/src/components/workflow/IdeaStage.test.jsx`

Focused test `ui/src/components/workflow/IdeaStage.test.jsx`

Review focus Forced interviews and duplicate note forms

### C16 — Provide one manual draft editor and explicit AI skip

Dependencies C15

Work

- Write tests for manual edits, supplied drafts and explicit Skip AI review and continue.
- Use one controlled editor and the same expandable context record from Idea.
- Save the working artifact and record the explicit skip before approval.
- Expose existing AI controls only when their matching integration is ready.

Acceptance checks

- Manual drafting reaches approval without a score or an interview.
- A failed AI request remains distinguishable from an explicit skip.
- Changing content invalidates the working approval.

Planned write paths

- `ui/src/components/workflow/DraftStage.jsx`
- `ui/src/components/workflow/DraftStage.test.jsx`

Focused test `ui/src/components/workflow/DraftStage.test.jsx`

Review focus Review-result prerequisites and duplicate editors

### C17 — Present the actual approval decision

Dependencies C16

Work

- Write tests displaying the full current artifact, destination, format and honest review state.
- Use one explicit Approve this version action with clear consent wording.
- Submit the acknowledged revision and show conflicts without losing text.
- Advance only after the server returns the matching approval.

Acceptance checks

- Pending/failed approval cannot advance to final export.
- Explicit AI skip still requires human approval.
- A stale approval response cannot approve newer edits.

Planned write paths

- `ui/src/components/workflow/ApproveStage.jsx`
- `ui/src/components/workflow/ApproveStage.test.jsx`

Focused test `ui/src/components/workflow/ApproveStage.test.jsx`

Review focus Extra consent rituals and approval of an earlier artifact

### C18 — Copy and download the approved payload

Dependencies C17

Work

- Write tests for exact approved content, clipboard denial and download initiation failure.
- Show Copy, Download and selectable content from the approved snapshot.
- Present per-segment controls for threads and an appropriate whole-artifact download.
- Offer linked adaptation using the approved version as its source.
- Use the server's binary export response for Download, including its safe filename. Preserve the exact approved segments for copy, and show copy/download failures without advancing any workflow state.

Acceptance checks

- Entering or using Export invokes zero model calls.
- Failed copy cannot report Copied.
- Download feedback describes initiation and never claims publication.

Planned write paths

- `ui/src/components/workflow/ExportStage.jsx`
- `ui/src/components/workflow/ExportStage.test.jsx`
- `ui/src/hooks/useCopyToClipboard.js`

Focused test `ui/src/components/workflow/ExportStage.test.jsx`

Review focus Hidden rewriting and generated files mistaken for browser downloads

### C19 — Replace tool navigation with the integrated Workflow

Dependencies C18

Work

- Write entry-point tests for Workflow, Lessons and Settings with four stages inside an item.
- Open the saved-content landing first and resume at the actual saved stage.
- Integrate the working Idea/Draft/Approve/Export components using the existing `useWorkflow` hook.
- Keep registration in tabs.js and App within its documented size target.

Acceptance checks

- The primary journey completes from App without copying between tool pages.
- Resume avoids repeating new-item platform selection.
- Workflow navigation preserves current item and pending input.

Planned write paths

- `ui/src/components/workflow/WorkflowTab.jsx`
- `ui/src/components/workflow/WorkflowTab.test.jsx`
- `ui/src/app/tabs.js`
- `ui/src/app/tabs.test.js`
- `ui/src/App.jsx`
- `ui/src/App.test.jsx`

Focused test `ui/src/App.test.jsx`

Review focus A cosmetic stepper over disconnected old tabs

### C20 — Validate the complete internal manual slice

Dependencies C19

Work

- Add an integrated existing LinkedIn draft journey using real workflow clients with mocked transport boundaries.
- Cover durable save acknowledgement, list/Resume, explicit AI skip, one approval and exact copy/download.
- Run a browser journey against isolated local storage and record actual interactions. Prasad or the reviewer completes checks that require an unavailable browser or assistive technology.
- Capture actual visual/keyboard evidence and repair the previous packet responsible for any failure.

Acceptance checks

- All four states operate through the normal root entry point.
- Refreshing recovers acknowledged input and actual approval associations.
- The report records the verified local journey and any remaining hosted release checks.

Planned write paths

- `ui/src/components/workflow/WorkflowJourney.test.jsx`

Focused test `ui/src/components/workflow/WorkflowJourney.test.jsx`

Review focus Unit-only success and seeded screenshots

### C21 — Persist real author facts and source configuration

Dependencies C20

Work

- Write owner-isolation and failed-save tests for factual profile and source records.
- Implement explicit save/read operations using the approved owned storage.
- Initialize empty author fields and labeled neutral product defaults.
- Support add/edit/enable/disable sources while preserving attached historical evidence.
- Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

Acceptance checks

- Blank accounts contain no invented identity or employment history.
- Updating one source preserves other sources.
- Saved records survive reload and seed refresh.

Planned write paths

- `content_machine/workflow/settings.py`
- `content_machine/workflow/settings_routes.py`
- `tests/test_workflow_settings.py`
- `content_machine/workflow/routes.py`

Focused test `tests/test_workflow_settings.py`

Review focus Global Markdown state leaking between creators

### C22 — Edit profile and sources through Settings

Dependencies C21

Work

- Write tests for optional factual fields, sources, unsaved edits, validation and server failure.
- Use ordinary fields and Save per section.
- Preserve unsaved inputs when refreshing or visiting Workflow.
- Link writing preferences to Lessons.

Acceptance checks

- Profile completion is optional.
- A failed save preserves exact input.
- Returning to Workflow restores the active item.

Planned write paths

- `ui/src/components/profile/SettingsPage.jsx`
- `ui/src/api/settings.js`
- `ui/src/components/profile/SettingsPage.test.jsx`

Focused test `ui/src/components/profile/SettingsPage.test.jsx`

Review focus Hardcoded persona and duplicate rule editors

### C23 — Scope governed writing preferences to their creator

Dependencies C22

Work

- Use failing tests to exercise manual add/edit/stop-using and actual conflict/cap outcomes.
- Reuse governed conflict/cap logic through the contract-approved storage seam.
- Preserve origin and change history and keep AI proposals pending.
- Keep old local/CLI records recoverable under the explicit migration mapping.
- Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

Acceptance checks

- Creator A's preferences do not affect B.
- A conflicting or blocked save cannot report activation.
- Stopping a preference persists and does not rewrite approved artifacts.

Planned write paths

- `content_machine/workflow/preferences.py`
- `content_machine/workflow/preference_routes.py`
- `tests/test_workflow_preferences.py`
- `content_machine/workflow/routes.py`

Focused test `tests/test_workflow_preferences.py`

Review focus Bypassing lessons governance and ambiguous legacy ownership

### C24 — Simplify Lessons to the single preference editor

Dependencies C23

Work

- Write cases for empty/loading/failed/active/pending preferences and blocked activation.
- Show Add/Edit/Stop using with explicit human Save and use.
- Use actual returned activation status and plain conflict text.
- Keep optional existing proposals manageable through the same collection.

Acceptance checks

- A creator can finish publishing preparation without visiting Lessons.
- AI suggestions activate only after an explicit author decision.
- A factual correction stays item-specific unless deliberately generalized.

Planned write paths

- `ui/src/components/lessons/LessonsTab.jsx`
- `ui/src/api/lessons.js`
- `ui/src/components/lessons/LessonsTab.test.jsx`

Focused test `ui/src/components/lessons/LessonsTab.test.jsx`

Review focus False success and a fifth required stage

### C25 — Attach real discovery sources to the working item

Dependencies C24

Work

- Reuse connector/Oracle seams with trusted creator-specific source configuration.
- Preserve item URL, title, available excerpt and retrieval context.
- Distinguish partial failure, no new results and unavailable history.
- Create an owned working item only after Save/Use.
- Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

Acceptance checks

- Title-only source material is identified accurately.
- A failed connector leaves other successful items usable.
- Real source metadata cannot become a fabricated personal experience.

Planned write paths

- `content_machine/workflow/discovery.py`
- `content_machine/workflow/discovery_routes.py`
- `tests/test_workflow_discovery.py`
- `content_machine/workflow/routes.py`

Focused test `tests/test_workflow_discovery.py`

Review focus Dropped excerpts, global connector settings and invented fallback summaries

### C26 — Unify discovery presentation inside Idea

Dependencies C25

Work

- Show one discovery list with search, optional filters and Use this idea.
- Keep refresh/status/Manage sources contextual.
- Use the same source selection behavior for new and previously found items.
- Preserve personal notes when the creator switches entry routes.
- Extend the workflow domain client with the actual discovery endpoints and preserve errors.

Acceptance checks

- Your idea and Discover remain equally prominent.
- Filters can be cleared and failures expose a useful next action.
- Source configuration changes return to the same draft.

Planned write paths

- `ui/src/components/workflow/DiscoveryPane.jsx`
- `ui/src/components/workflow/IdeaStage.jsx`
- `ui/src/components/workflow/DiscoveryPane.test.jsx`
- `ui/src/api/workflow.js`

Focused test `ui/src/components/workflow/DiscoveryPane.test.jsx`

Review focus Taxonomy noise and inconsistent archive actions

### C27 — Make voice results target a stable field context

Dependencies C26

Work

- Write delayed-transcription tests with item/revision/field targets.
- Expose recording and transcribing status independently of the active recording flag.
- Release microphone resources when the target stage becomes inactive.
- Return a recoverable transcript when intervening edits prevent safe insertion.

Acceptance checks

- Permission denial leaves typing usable.
- A delayed transcript cannot enter another item or account.
- Stopping shows processing accurately until a result or error.

Planned write paths

- `ui/src/hooks/useVoiceRecording.js`
- `ui/src/hooks/useVoiceRecording.test.js`

Focused test `ui/src/hooks/useVoiceRecording.test.js`

Review focus Late insertion, silent text replacement and hidden active microphones

### C28 — Place labeled dictation beside intake and editing

Dependencies C27

Work

- Add Dictate/Stop to the intended fields using the shared hook.
- Show local recording/processing/error status and an editable transcript.
- Bind insertion to the originating field and preserve typed text.
- Document the actual browser/backend processing path in contextual help.

Acceptance checks

- The full workflow requires no separate Audio destination.
- Keyboard start/stop and cancellation preserve input.
- An unavailable microphone offers continued typing.

Planned write paths

- `ui/src/components/workflow/DictationControl.jsx`
- `ui/src/components/workflow/IdeaStage.jsx`
- `ui/src/components/workflow/DraftStage.jsx`
- `ui/src/components/workflow/DictationControl.test.jsx`

Focused test `ui/src/components/workflow/DictationControl.test.jsx`

Review focus Decorative-only controls and field labeling

### C29 — Build an owner-specific editorial context snapshot

Dependencies C28

Work

- Write tests for source claims, author experience, interpretation and owned settings/preferences.
- Build one immutable context snapshot for the writing request.
- Pass scoped context explicitly through the provider seam while retaining supported local callers.
- Keep credentials outside stored draft/evidence payloads.

Acceptance checks

- A and B receive only their own author/preferences context.
- Changing settings affects later requests and leaves existing approved snapshots intact.
- Source-only commentary requires no invented personal story.

Planned write paths

- `content_machine/workflow/context.py`
- `content_machine/knowledge/provider.py`
- `tests/test_workflow_context.py`

Focused test `tests/test_workflow_context.py`

Review focus Per-request process environment mutation and globally loaded author facts

### C30 — Generate the initial selected-platform draft

Dependencies C29

Work

- Write offline tests capturing the actual model request inputs.
- Reuse the appropriate existing generation seams with the approved context snapshot and platform/format.
- Return a proposed artifact associated with its input version.
- Preserve source/notes and an honest error when generation fails.
- Register the subrouter in the workflow router and exercise it through TestClient against the normal app.
- Use the C30a, C30b and C30c children above, with a separate review after each.

Acceptance checks

- Per-item notes and excerpts actually reach the writing request.
- A supplied draft is unchanged until a creator requests/accepts a rewrite.
- Provider failure produces no template disguised as successful generation.

Planned write paths

- `content_machine/workflow/writing.py`
- `content_machine/workflow/writing_routes.py`
- `tests/test_workflow_writing.py`
- `content_machine/workflow/routes.py`
- `content_machine/workflow/format_registry.py`

Focused test `tests/test_workflow_writing.py`

Review focus Context rendered only in UI and wrong platform prompts

### C31 — Add the actual Instagram caption adapter

Dependencies C30

Work

- Write tests for supported format registration, grounded prompt inputs and failure behavior.
- Generate editable caption text from the supplied evidence and creator point.
- Apply contract-approved applicable limits before approval.
- Register the adapter under the exact destination/format ID.

Acceptance checks

- Caption requests return caption artifacts.
- Missing evidence does not trigger invented metrics or anecdotes.
- Availability becomes true only when the adapter checks pass.

Planned write paths

- `content_machine/workflow/adapters/instagram_caption.py`
- `content_machine/workflow/format_registry.py`
- `tests/test_instagram_caption.py`

Focused test `tests/test_instagram_caption.py`

Review focus Relabeling a generic video script as a caption

### C32 — Add the actual Instagram Reel-script adapter

Dependencies C31

Work

- Write tests for a script artifact with grounded spoken text and production cues.
- Implement the Reel-specific adapter using shared generation logic.
- Preserve required visual/camera/pause markers where applicable.
- Expose the format independently of Caption.

Acceptance checks

- A Reel script is labeled as text for production.
- Unsupported benchmark/numeric sections are omitted or returned as author questions.
- A caption remains separately selectable and separately approved.

Planned write paths

- `content_machine/workflow/adapters/instagram_reel.py`
- `content_machine/workflow/format_registry.py`
- `tests/test_instagram_reel.py`

Focused test `tests/test_instagram_reel.py`

Review focus Rendered-video promises and compulsory bundles

### C33 — Preserve and validate X-thread segments

Dependencies C32

Work

- Reuse the current X generator through the selected-platform adapter contract.
- Parse or request ordered post segments and validate configured per-post constraints.
- Keep the approved segmentation in the immutable artifact.
- Return actionable errors before approval when segmentation is invalid.

Acceptance checks

- Per-post copy and full download use the exact approved boundaries.
- No silent shortening occurs during export.
- An incomplete/overlong response cannot appear ready for approval.

Planned write paths

- `content_machine/workflow/adapters/x_thread.py`
- `content_machine/workflow/format_registry.py`
- `tests/test_workflow_x_thread.py`

Focused test `tests/test_workflow_x_thread.py`

Review focus Total-string length mistaken for valid thread structure

### C34 — Preserve short/long YouTube script capabilities

Dependencies C33

Work

- Map existing short/long script identifiers without removing retained history.
- Use grounded script generation with actual production cues.
- Make unsupported evidence sections optional.
- Label deliverables accurately as scripts.

Acceptance checks

- Short and long formats remain distinct.
- A source without numbers yields no forced benchmark chapter.
- Export retains the exact approved script text.

Planned write paths

- `content_machine/workflow/adapters/youtube.py`
- `content_machine/workflow/format_registry.py`
- `tests/test_workflow_youtube.py`

Focused test `tests/test_workflow_youtube.py`

Review focus Lost formats and fabricated production/performance claims

### C35 — Preserve newsletter and generic-script capabilities

Dependencies C34

Work

- Implement the contract's honest mappings for newsletter and the retained general short-script path.
- Reuse existing generators and keep their legacy identifier translation explicit.
- Validate actual artifact structure before approval.
- Keep format changes as separately approvable adaptations.

Acceptance checks

- Existing formats/history have an explicit supported mapping.
- Newsletter is a draft and generic script names its actual capability.
- Destination/format changes cannot inherit approval.

Planned write paths

- `content_machine/workflow/adapters/retained_formats.py`
- `content_machine/workflow/format_registry.py`
- `tests/test_workflow_retained_formats.py`

Focused test `tests/test_workflow_retained_formats.py`

Review focus Silent capability removal and inflated platform claims

### C36 — Associate AI review with its exact owned snapshot

Dependencies C35

Work

- Write tests capturing reviewed bytes/context and subsequent sanitizer/revision changes.
- Invoke Council using the owned immutable input context.
- Record actual reviewed snapshot, score basis, actions and proposed revisions separately.
- Preserve fail/skip/earlier/current states and the ability to approve without a score.
- Use a single review pass for workflow advice and present sanitizer or writer changes as proposals. Preserve existing Council iteration callers.
- Expose the owned review operation through writing_routes.py and test its normal HTTP entry with scoped principals.

Acceptance checks

- Returned changed wording never inherits a review of different content.
- Raw and normalized scores have explicit distinct scales.
- Reviewing A cannot incorporate B's profile/preferences or overwrite B.

Planned write paths

- `content_machine/workflow/reviews.py`
- `content_machine/council/loop.py`
- `tests/test_workflow_reviews.py`
- `content_machine/workflow/writing_routes.py`

Focused test `tests/test_workflow_reviews.py`

Review focus Review/source mismatch and global author context

### C37 — Connect drafting, AI feedback and revision comparison

Dependencies C36

Work

- Connect Create draft, optional Review draft and one wording suggestion to versioned APIs.
- Lead with actionable feedback and a readable current/proposed comparison.
- Accept a proposal as a new working version and retain the prior snapshot.
- Keep pending/failure/earlier-version output attached to its origin.
- Extend the domain client with actual owned generation/review operations used by this UI.

Acceptance checks

- Cancel changes nothing and acceptance invalidates old working approval.
- An explicit skip remains available after a failed review.
- Late results cannot force navigation or replace newer text.

Planned write paths

- `ui/src/components/workflow/DraftStage.jsx`
- `ui/src/components/workflow/ReviewPanel.jsx`
- `ui/src/components/workflow/ReviewPanel.test.jsx`
- `ui/src/api/workflow.js`

Focused test `ui/src/components/workflow/ReviewPanel.test.jsx`

Review focus Multiple polish entry points and stale revisions accepted into another item

### C38 — Separate provable demo records from creator work

Dependencies C37

Work

- Write migration tests with proven synthetic, actual legacy and ambiguous records.
- Require an explicit owner mapping for imported user work.
- Keep recoverable backups and quarantine proven synthetic records outside normal creator work.
- Make repeated import safe and preserve historical Comments/exports.

Acceptance checks

- Private workspaces retain actual creator provenance. Guest examples stay labelled and scoped to their own guest workspace.
- Unknown lineage/approval stays unknown.
- Import twice preserves edits, record counts and recoverability.

Planned write paths

- `content_machine/workflow/legacy_import.py`
- `tests/test_workflow_legacy_import.py`

Focused test `tests/test_workflow_legacy_import.py`

Review focus Mass deletion and guessed ownership

### C39 — Remove automatic public-demo seeding from the real entry

Dependencies C38

Work

- Write bootstrap tests for real empty private workspace initialization.
- Remove automatic sample seeding from private cold starts. Preserve the explicit guest-seeding integration point for the hosted packets.
- Use the selected deployment storage configuration.
- Initialize actual accounts without invented persona or active learned rules.

Acceptance checks

- Private cold starts leave new creator workspaces empty and retain existing saved records.
- Restart/deploy cannot replace saved creator settings.
- Temporary storage is identified until the durable hosted gate passes.

Planned write paths

- `api/index.py`
- `content_machine/bootstrap.py`
- `tests/test_workflow_bootstrap.py`

Focused test `tests/test_workflow_bootstrap.py`

Review focus A new UI backed by the old demo cold start

### C40 — Return actual Council and distribution failures

Dependencies C39

Work

- Write failed-provider cases for the existing API seams.
- Remove unrelated seeded review/bundle substitution in the real workflow.
- Return actionable structured failures with the original request identity.
- Retain preserved inputs and usable earlier-version data.

Acceptance checks

- A quota/provider failure cannot return sample success.
- Failed review cannot set review-complete or human-approved state.
- Existing clients receive explicit errors through their domain adapters.

Planned write paths

- `content_machine/api/app.py`
- `tests/test_workflow_failure_routes.py`

Focused test `tests/test_workflow_failure_routes.py`

Review focus A labeled replay still being used as actual work

### C41 — Return actual briefing and synthesis failures

Dependencies C40

Work

- Write cases for unavailable source context, invalid model output and exhausted routes.
- Return explicit failure/partial status instead of invented tension or template success.
- Keep optional generic prompts labeled as generic help.
- Preserve author notes for manual continuation.

Acceptance checks

- Title-only input cannot produce a confident sourced briefing by fallback.
- Typed notes survive a failed synthesis.
- Manual drafting and explicit AI skip remain possible.

Planned write paths

- `content_machine/interview/engine.py`
- `tests/test_workflow_interview_failures.py`

Focused test `tests/test_workflow_interview_failures.py`

Review focus Invented narrative used to conceal failure

### C42 — Report wording-assistance fallback outcomes honestly

Dependencies C41

Work

- Write cases distinguishing model rewrite, deterministic cleanup and complete failure.
- Expose the actual operation/result provenance.
- Show cleanup as a proposal associated with its original version.
- Keep exact saved/approved artifacts immutable.

Acceptance checks

- Local cleanup cannot claim a successful model rewrite or authenticity verification.
- Changed text has a new review/approval status.
- Failure retains input and a useful retry/manual route.

Planned write paths

- `content_machine/humanize/transformer.py`
- `content_machine/schemas.py`
- `tests/test_workflow_wording_failures.py`

Focused test `tests/test_workflow_wording_failures.py`

Review focus Silent sanitizer success and misleading humanized badges

### C43 — Retire Audio/demo navigation and UI emoji throughout entry points

Dependencies C42

Work

- Update root navigation tests to the reviewed destinations and integrated workflow.
- Retire obsolete guide/sample components and Audio registration within the creator workflow. Preserve the guest entry and mode status in the hosted design.
- Use professional topic/action presentation through the shared registry.
- Keep original content text intact while changing interface labels.
- Use C43a through C43c above for navigation, input integration and interface labels. Adjust tests for the intended removal and verify rendered labels across every remaining destination.

Acceptance checks

- Normal entry points expose the agreed Workflow/Lessons/Settings structure.
- Mic input remains available at real fields.
- Private workflows have no guide toggle or sample launcher competing with content creation. The explicit hosted guest mode remains supported.

Planned write paths

- `ui/src/App.jsx`
- `ui/src/app/tabs.js`
- `ui/src/lib/topics.js`
- `ui/src/App.test.jsx`
- `ui/src/components/audio/AudioTab.jsx`
- `ui/src/components/audio/AudioTab.test.jsx`
- `ui/src/components/DemoBanner.jsx`
- `ui/src/components/DemoBanner.test.jsx`
- `ui/src/components/SampleStory.jsx`
- `ui/src/components/SampleStory.test.jsx`
- `ui/src/lib/constants.js`
- `ui/src/lib/topics.test.js`

Focused test `ui/src/App.test.jsx`

Review focus Dormant old navigation and accidental modification of authored text

### C44 — Add safe item history and stable browser navigation

Dependencies C43

Work

- Implement private item/stage URLs through the selected existing routing seam.
- Open old snapshots read-only with Compare and Restore as new version.
- Restore focus and active item/stage after settings/history detours.
- Keep the current unsaved draft while historical data loads or fails.

Acceptance checks

- Back/Forward does not rerun AI or clear text.
- Viewing history cannot grant approval.
- Direct Export navigation handles missing prerequisites visibly.

Planned write paths

- `ui/src/app/workflowNavigation.js`
- `ui/src/components/workflow/VersionHistory.jsx`
- `ui/src/components/workflow/VersionHistory.test.jsx`
- `ui/src/components/workflow/WorkflowTab.jsx`

Focused test `ui/src/components/workflow/VersionHistory.test.jsx`

Review focus Navigation inferred as workflow completion and destructive restoration

### C45 — Validate the hosted authentication/storage adapter

Dependencies C44

Work

- Use the confirmed Supabase Auth and Postgres design with Google sign-in and anonymous guests. Verify the actual project, account and deployment prerequisites.
- Record trusted principal verification, durable store guarantees, CORS/origin configuration and credential provisioning.
- Confirm the H01 through H07 scopes above and resolve their shared storage/authentication design before implementation.
- Record missing live configuration while completing the offline provider implementation and tests. Review migrations before any real-data use.

Acceptance checks

- Account/cost/credential prerequisites are explicit.
- Ephemeral Vercel /tmp cannot satisfy acknowledged durable saves.
- The hosted storage/authentication design is reviewed before service refactors. Live checks remain pending until the actual project is configured.

Planned write paths

- `docs/implementation/hosted-workspace-decision.md`

Review focus A placeholder provider treated as a private production system

### C46 — Implement the selected hosted adapter in reviewed subpackets

Dependencies C45

Work

- Use H01 through H06, including the separate H03 service reviews, as the concrete implementation children after C45's design review.
- Freebuff implements one child at a time with failing identity/storage tests.
- Exercise actual authenticated access and durable recovery in the selected environment.
- Return credentials/setup blockers as typed status for one-time user action.

Acceptance checks

- Every assigned child names its current files, exact commands and required inputs before work begins.
- Unauthenticated and forged-principal requests fail.
- Acknowledged content survives the chosen deployment restart boundary.

Planned write paths

- The H01 through H06 initial scopes listed above, narrowed to the currently assigned child.

Review focus Dispatching an unresolved architecture task to the implementer

### C47 — Audit every legacy route and file for creator isolation

Dependencies C46

Work

- Enumerate all existing read/write/static-file routes and identify private data flows.
- Apply the selected hosted access boundary to legacy routes as well as /api/workflow.
- Scope or explicitly disable unsupported global-data routes in hosted mode while preserving supported local callers.
- Test direct IDs, paths, history, sources, profile, preferences and late results across two creators.

Acceptance checks

- Authenticated B cannot access A through an older endpoint or file path.
- Global Markdown/SQLite/process environment cannot select another creator's author data.
- Static SPA fallback and unknown /api behavior remain correct.

Planned write paths

- `content_machine/workflow/route_access.py`
- `content_machine/api/app.py`
- `tests/test_workflow_route_access.py`

Focused test `tests/test_workflow_route_access.py`

Review focus Securing only the new endpoints

### C48 — Rehearse migration and durable recovery

Dependencies C47

Work

- Use backed-up isolated legacy data with explicit owner assignments.
- Exercise interrupted save/import, repeated migration and restart/redeploy recovery.
- Verify unchanged historical artifacts and source/approval associations.
- Exercise export of an unapproved recovery backup separately from final approval.

Acceptance checks

- Failed/partial operations preserve recoverable data.
- Seed updates and repeat migrations cannot overwrite creator edits.
- Known synthetic and uncertain records are handled according to their actual provenance.

Planned write paths

- `tests/test_workflow_recovery.py`

Focused test `tests/test_workflow_recovery.py`

Review focus A successful fresh install mistaken for safe migration

### C49 — Complete keyboard, screen-reader and responsive journeys

Dependencies C48

Work

- Exercise own notes, discovery, existing draft, explicit AI skip and manual export. Prasad or the reviewer completes any unavailable assistive-technology checks.
- Check focus/labels/errors/linear comparison using keyboard and a screen reader.
- Check 320 CSS-pixel reflow, 200% text resize, long content and phone keyboard.
- Record actual evidence, failures and unperformed checks. Repair the owning code packet for each observed failure.

Acceptance checks

- All text and primary actions stay reachable and readable.
- Icons have visible labels or accessible names and statuses have textual meaning.
- A screenshot or worker claim alone cannot mark a manual scenario passed.

Planned write paths

- `ui/src/components/workflow/WorkflowJourney.test.jsx`
- `docs/implementation/workflow-ui-verification.md`

Focused test `ui/src/components/workflow/WorkflowJourney.test.jsx`

Review focus Invented browser/accessibility evidence

### C50 — Run full release verification and final diff review

Dependencies C49

Work

- Run collected focused tests, the guarded full pytest suite, mandated guarded unittest discovery, frontend suite and production build. The reviewer verifies these results against the final diff.
- Verify the complete retained-platform matrix including both Instagram deliverables.
- Review staged, unstaged, untracked and generated output against the accepted checkpoint baseline.
- Record exact command exit codes, revision/diff digest, manual evidence, remaining limitations and release disposition.

Acceptance checks

- Every required test/check was actually run against the reviewed revision.
- Tracked ui/dist matches the accepted source build.
- All mandatory product gates pass before release is marked ready.

Planned write paths

- `docs/implementation/workflow-release-evidence.md`

Review focus Rubber-stamped completion, stale build artifacts and unreviewed final edits

## First handoff prompt

Prasad can paste this prompt into Freebuff after opening the implementation checkout. It assigns a bounded audit and leaves the first coding assignment for the next message.

```text
Please work in C:\Users\mamat\Github\Content-Machine\.orchestration\worker.
Read AGENTS.md, then the current handoff state, working protocol and recovery
task R00 in docs/implementation/freebuff-task-plan.md. Start with R00 only.

Inspect the complete current Git status, including untracked files. Preserve
the existing partial work. The workflow page import is currently unresolved.
Review the partial C10 action API, platform registry, API client, workflow page,
application shell and emoji changes. Identify concrete defects and propose
checkpoint scopes for the existing files. Use the guarded launcher for every
Python test. Run the focused checks and frontend build. Keep credentials and
real user storage out of the work.

Keep R00 read-only. Report the current changed files, observed failures,
commands, exit codes, test counts, missing test coverage and the proposed C10
scope. Stop after the audit so I can review it before assigning implementation.
```

After reviewing R00, Prasad can use the following first coding prompt. Read and incorporate any concrete review findings alongside it.

```text
Please implement C10 from docs/implementation/freebuff-task-plan.md in the
same implementation checkout. Read its working protocol, C10 section and the
relevant workflow contract sections. Reuse the existing partial action API.

Complete the history, explicit review skip, approval, restore, adaptation and
exact export endpoints. Preserve ownership checks and stable idempotent
retries. Every mutating HTTP action must commit its enclosing request-owned
transaction before success is returned. Add meaningful regression tests for
any uncovered behavior before implementing the fix. Report capability
readiness according to the actual connected workflow adapters.

Run the guarded action/item API tests and required backend regression.
Review the complete C10 diff, including its untracked files. Return the report
format below and stop at C10 for review.
```

For later tasks, Prasad assigns the next accepted-dependency checkpoint by ID. Freebuff reads the common protocol, that task and relevant source. The full document remains a reference rather than a requirement to implement every task in one session.

## Checkpoint report format

```text
Checkpoint and status
Base commit
Files changed or added
Behavior completed
Tests added and the actual failing result before implementation
Checks run with commands, working directory, exit code and test counts
Acceptance criteria verified
Known baseline failures and newly introduced failures
Remaining issues, unavailable checks and external prerequisites
Ready for review or blocked, with the precise reason
```

## Review and repair handoff

Prasad can give the checkpoint report and diff to an independent reviewer. Compare the exact candidate with its baseline, including staged, unstaged and untracked files. Review each acceptance check and applicable repository instruction. Inspect actual error paths, ownership, transaction boundaries, input preservation and normal application entry points. Re-run checks where needed to establish confidence in the current candidate.

For each actionable issue, give Freebuff the affected file and function, a concrete failing scenario, the expected result, the allowed repair files and a focused test command. Ask it to reproduce the failure first, repair it, rerun the relevant checks and stop for another review. Keep the initial and repaired results separate. Accept only the reviewed candidate, then assign the next checkpoint.

The release review covers the full backend and frontend suites, a production build, the browser journeys, the retained platform matrix, accessibility checks and hosted isolation/recovery. Record each actual result and leave unperformed checks open.

Use a repair instruction with the concrete review finding filled in.

```text
Please repair the reported issue within the current checkpoint. Reproduce
the supplied failing scenario with a regression test, implement the smallest
complete fix in the affected files, rerun the focused checks and inspect the
diff. Preserve the existing passing cases. Return the updated checkpoint
report and stop for review before starting the next task.
```
