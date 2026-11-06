# Content Machine supervised implementation runbook

Date 2026-11-05

This runbook translates the reviewed product plan into 51 supervised checkpoints.
Freebuff is the implementer. Codex supplies bounded prompts, independently verifies the work, issues repairs and controls advancement.

## Current execution gate

Freebuff rejected the C10 handoff on November 6, 2026 UTC under its **Driven by another agent** usage policy. The provider withheld the message from its model. Automatic Freebuff submissions have stopped while the user chooses a supported implementation route. C00 through C09 are accepted, and C10 is pending. The supervision protocol below remains the checkpoint/review design for the selected implementation route. [Rejection evidence and accepted checkpoints](freebuff-integration.md)

The latest user decisions select Supabase Auth and Postgres with Google sign-in and add an explicit guest demo with seeded examples and live AI. Guest work persists across return visits, and Google sign-in offers an explicit transfer. C38, C39, C43 and the hosted children must preserve this opt-in guest experience while keeping creator workspaces private and free of automatic sample seeding. The hosted packets must verify guest and authenticated ownership throughout retention and transfer.

[Product requirements](../ui-workflow-plan.md) govern user outcomes.
[Machine-readable checkpoints](workflow-tasks.json) define the packets.
[Dispatch, review and repair prompts](workflow-prompts.md) define the handoff.

## Current integration evidence

The installed Freebuff Desktop version is 0.0.200. Its packaged build identifies commit 4d28fecfed52f1ecbd85ab065cdde49c87458a2f.
The user accepted the official Freebuff CLI as the implementer.
The official npm package freebuff@0.2.36 was installed for a disposable probe and its help command was run.
The CLI exposes an interactive terminal, --cwd, --continue and --trust-agents. Its actual help output provides no print/JSON/headless run option.
The CLI launched through the available pseudo-terminal in a separate three-file temporary directory and requested a one-time sign-in.
The CLI subsequently entered an authenticated session. Two automated turns completed, including an actual file-tool read of controller-created fixtures. A cancellation produced an interrupted response.

Vendor documentation describes the interactive CLI, and an upstream request for headless orchestration remains open.
The separate Codebuff SDK documents API-key-backed execution.
Source-backed internal Desktop HTTP/MCP code exists, but this task established no supported external authentication/discovery contract for it.
The selected experiment uses the official interactive CLI with its normal account, ads and allowance behavior.

Sources were opened on 2026-11-05.
- [Freebuff CLI](https://freebuff.com/cli)
- [Upstream orchestration request](https://github.com/CodebuffAI/freebuff/issues/947)
- [SDK README](https://github.com/CodebuffAI/freebuff/blob/main/sdk/README.md)
- [Official Codex App Server documentation](https://developers.openai.com/codex/app-server/)

## How automatic operation works

~~~mermaid
flowchart LR
    P["Codex renders one checkpoint"] --> F["Freebuff implements it"]
    F --> E["Controller captures diff and runs checks"]
    E --> R["Codex reviews the exact candidate"]
    R -->|Accept| N["Record accepted checkpoint"]
    N --> P
    R -->|Repair| Q["Send a focused correction"]
    Q --> F
    R -->|Blocked| B["Preserve work and report required action"]
~~~

The initial policy uses one active implementer and three repair attempts per checkpoint.
The default task timeout is 20 minutes. Identical failures repeated twice trigger diagnosis or task splitting.
These are adjustable controller choices.

During an active session Codex can submit prompts, wait, inspect diffs, run checks and send follow-ups through a verified transport.
Continuous operation after this chat closes requires a durable local controller and a configured reviewer runtime.
Codex App Server provides documented thread/turn events for that separate runtime. Its account/model access must be verified during setup.
The current chat and the local controller require an explicit connection before unattended continuation can be claimed.

One-time sign-in, MFA, account/credential provisioning and host-required permissions can require the user.
The running controller reports those conditions immediately and continues independent ready work.

## Control protocol

1. Record the current HEAD and every staged, unstaged and untracked path. Preserve the existing planning documents.
2. Prepare a controller-owned isolated checkout under an authorized workspace using a codex/ branch. Supply the approved plan/contract explicitly when they are absent from HEAD.
3. Resolve Python and npm to actual working executables. This Windows installation's Python alias has failed in the sandbox before. Record the resolved command and actual dependency/collection check.
4. Capture the baseline and isolate CONTENT_MACHINE_HOME before importing backend storage. Keep production author data separate from tests.
5. Lock one task and render the common prompt plus only that task's contract/source context. Resolve every path/command placeholder.
6. Dispatch the exact prompt with a nonce and record the Freebuff session and task identity.
7. Require an explicit per-turn completion condition established by C00. A quiet terminal, a disconnected process or the word done cannot advance the queue.
   The CLI also marks interrupted replies complete. Check the cancellation ledger and matching response identity before treating the reply as ready for review.
8. Capture the actual tree and diff, including untracked content. Compare changed paths to the allowlist and preserve the candidate for review.
9. Independently collect/run the targeted tests and inspect source against every acceptance case. Add the relevant browser/manual checks when required.
10. Review exact changed content. Record accept, repair or blocked with its tree digest and evidence.
11. On repair send a concrete reproducer, location, expected behavior and restricted correction packet. Preserve prior accepted work.
12. On acceptance stop the worker from further edits, verify the tree is still the reviewed tree, and record the accepted local checkpoint.
13. Dispatch the next dependency-ready task. A restart resumes from the last controller acceptance record and investigates an in-flight task before resubmitting it.
14. A scope expansion, dependency change or missing design decision returns to the controller for a smaller explicit packet.
15. Final commit/push, real-data migration and deployment follow the user's applicable authorization and the completed release evidence.

The source allowlist is checked against actual edits. It is a coordination policy, with isolation providing additional protection for the original working tree.
A controller examines unexpected changes before continuing.

## Acceptance authority and evidence

Each run keeps dispatch.json, worker transcript/report, actual diff/tree digest, independent check output and reviewer decision.
The worker submits ready_for_review. The controller alone writes accepted.json and advances the manifest.
Store controller evidence outside the worker checkout and protect it with the runtime's available permissions.

Tests must collect the intended cases. The existing backend mixes unittest classes and function-style pytest tests.
Use targeted pytest for new backend packets, the repository-mandated unittest discovery at milestones, and full pytest for release.
Record collected/pass/fail/skip counts and process exit codes. A zero-collected result needs correction.
Mocks can isolate real model/network access, while assertions must exercise the actual changed behavior and normal entry points.

UI checks use existing Vitest/Testing Library tooling. Check user-visible behavior and API ownership.
Record manual keyboard, screen-reader, browser and responsive scenarios separately with actual evidence.
A screenshot covers its recorded viewport and state. A pending manual requirement remains visible in the release record.

Tests/build dependencies and the frozen Council rubric are controller-managed boundaries.
The implementer preserves tests that express accepted behavior and repairs the implementation when those tests expose a regression.

## Logical contract to freeze in C01

The following is the proposed concrete contract. Codex reviews and freezes it in workflow-contract.md before C02.

| Record | Required identity and meaning |
| --- | --- |
| Principal | Trusted stable creator ID supplied by authenticated verification or explicit trusted local mode |
| ContentItem | Opaque item ID, owner ID, editable title, destination/format, stage, working revision, context, artifact, parent-version reference and actual timestamps |
| Context | Real source identities/URLs/excerpts/retrieval context, optional author notes/experience/interpretation and an owned preference/profile snapshot |
| Artifact | Ordered text segments. A post/caption/script/newsletter has one segment. A thread has one segment per post |
| ContentVersion | Immutable owned item/revision/context/artifact snapshot created at review, approval, restore or adaptation boundaries |
| Review | Operation ID, input version, actual state, actions and explicit score basis, with proposed wording separate from scored input |
| Approval | Authenticated owner, item, immutable version, exact artifact digest, destination/format and approval time |
| Idempotency record | Owner, operation/resource, key, request digest and actual result. Reusing a key with another payload conflicts |

Use explicit expected_revision on content writes. A stale revision returns 409 with current acknowledged metadata and preserves the client's input.
Content/platform/format/context edits increment the working revision and clear its active approval.
Navigation and approval state changes preserve the artifact snapshot. They never manufacture a reviewed or approved version.
Export reads the approved snapshot and serializes its stored segments under the frozen UTF-8/newline contract.

Freeze this worked example.
1. Create item A at revision 1.
2. Save changed text with expected_revision 1 and request key K1, receiving revision 2.
3. Freeze revision 2 as V2. Record an explicit AI skip or actual review associated with V2.
4. Approve V2 after checking revision 2 is still current, recording approval A2 and moving to Export.
5. Export A2's exact artifact without a model request.
6. Save a one-space edit with expected_revision 2, receiving revision 3 and clearing working approval.
7. Restore V2 into revision 4. A2 remains historical and revision 4 requires its own human approval.
8. Retry K1 with its original payload, receiving the recorded result. A changed payload for K1 returns a conflict.

Freeze endpoint names and response/error shapes.
- GET/POST /api/workflow/items
- GET/PATCH /api/workflow/items/{item_id}
- GET /api/workflow/items/{item_id}/versions
- POST /api/workflow/items/{item_id}/restore
- POST /api/workflow/items/{item_id}/skip-review
- POST /api/workflow/items/{item_id}/approve
- GET /api/workflow/items/{item_id}/exports/{version_id}
- POST /api/workflow/items/{item_id}/adapt
- GET /api/workflow/capabilities
- Owned settings, preferences, discovery and writing/review endpoints specified before their packets

The backend registry supplies actual editing/generation readiness to the UI.
The frontend registry owns platform identity, icons and labels.
The worker receives the exact approved retained-format mapping and adapters.

Local SQLite supports the internal slice through the existing architecture.
Hosted authentication and durable deployment choices remain C45 decision work.
Provider-specific children replace C46 before dispatch. Literal placeholders are a dispatch error.
Every legacy data/file route is audited in C47, including profile, lessons, discovery and history.
Per-request global environment switching cannot provide concurrent private owner isolation.

## Practical test commands

~~~powershell
# Resolve these executables in C00 and use isolated storage before backend imports.
python -m pytest tests/test_workflow_items.py -q
python -m unittest discover -s tests
python -m pytest tests -q

# Run from ui.
npm test -- src/app/useWorkflowSession.test.jsx --maxWorkers=2
npm test -- --maxWorkers=2
npm run build
~~~

The manifest holds argv arrays and a working directory so the controller can launch commands without building shell strings.
The controller checks every newly created file as well as tracked diffs.
The tracked ui/dist build is produced after source acceptance and reviewed as generated output.

## Checkpoint index

| ID | Phase | Deliverable | Acceptance check |
| --- | --- | --- | --- |
| C00 | readiness | Prove the Freebuff transport and capture the baseline | Controller gate |
| C01 | foundation | Freeze implementation decisions and the logical contract | Controller gate |
| C02 | foundation | Define workflow domain schemas | tests/test_workflow_schemas.py |
| C03 | foundation | Add additive workflow storage migration | tests/test_workflow_migrations.py |
| C04 | foundation | Resolve trusted principals for workflow requests | tests/test_workflow_access.py |
| C05 | foundation | Store and list owned working items | tests/test_workflow_items.py |
| C06 | foundation | Persist immutable content snapshots | tests/test_workflow_versions.py |
| C07 | foundation | Approve and export an exact saved artifact | tests/test_workflow_approvals.py |
| C08 | foundation | Restore versions and create linked adaptations | tests/test_workflow_history.py |
| C09 | foundation | Expose owned item CRUD through a small API router | tests/test_workflow_api_items.py |
| C10 | foundation | Expose history, approval and export actions | tests/test_workflow_api_actions.py |
| C11 | shell | Create a platform registry and recognizable icons | ui/src/lib/platforms.test.js |
| C12 | shell | Add workflow domain API clients | ui/src/api/workflow.test.js |
| C13 | shell | Manage acknowledged workflow state and saves | ui/src/app/useWorkflowSession.test.jsx |
| C14 | shell | Build the real saved-content landing | ui/src/components/workflow/ContentList.test.jsx |
| C15 | shell | Capture own material in the Idea stage | ui/src/components/workflow/IdeaStage.test.jsx |
| C16 | shell | Provide one manual draft editor and explicit AI skip | ui/src/components/workflow/DraftStage.test.jsx |
| C17 | shell | Present the actual approval decision | ui/src/components/workflow/ApproveStage.test.jsx |
| C18 | shell | Copy and download the approved payload | ui/src/components/workflow/ExportStage.test.jsx |
| C19 | shell | Replace tool navigation with the integrated Workflow | ui/src/App.test.jsx |
| C20 | integration | Validate the complete internal manual slice | Controller gate |
| C21 | support | Persist real author facts and source configuration | tests/test_workflow_settings.py |
| C22 | support | Edit profile and sources through Settings | ui/src/components/profile/SettingsPage.test.jsx |
| C23 | support | Scope governed writing preferences to their creator | tests/test_workflow_preferences.py |
| C24 | support | Simplify Lessons to the single preference editor | ui/src/components/lessons/LessonsTab.test.jsx |
| C25 | content | Attach real discovery sources to the working item | tests/test_workflow_discovery.py |
| C26 | content | Unify discovery presentation inside Idea | ui/src/components/workflow/DiscoveryPane.test.jsx |
| C27 | content | Make voice results target a stable field context | ui/src/hooks/useVoiceRecording.test.js |
| C28 | content | Place labeled dictation beside intake and editing | ui/src/components/workflow/DictationControl.test.jsx |
| C29 | content | Build an owner-specific editorial context snapshot | tests/test_workflow_context.py |
| C30 | content | Generate the initial selected-platform draft | Controller gate |
| C31 | content | Add the actual Instagram caption adapter | tests/test_instagram_caption.py |
| C32 | content | Add the actual Instagram Reel-script adapter | tests/test_instagram_reel.py |
| C33 | content | Preserve and validate X-thread segments | tests/test_workflow_x_thread.py |
| C34 | content | Preserve short/long YouTube script capabilities | tests/test_workflow_youtube.py |
| C35 | content | Preserve newsletter and generic-script capabilities | tests/test_workflow_retained_formats.py |
| C36 | content | Associate AI review with its exact owned snapshot | tests/test_workflow_reviews.py |
| C37 | content | Connect drafting, AI feedback and revision comparison | ui/src/components/workflow/ReviewPanel.test.jsx |
| C38 | integrity | Separate provable demo records from creator work | tests/test_workflow_legacy_import.py |
| C39 | integrity | Remove automatic public-demo seeding from the real entry | tests/test_workflow_bootstrap.py |
| C40 | integrity | Return actual Council and distribution failures | tests/test_workflow_failure_routes.py |
| C41 | integrity | Return actual briefing and synthesis failures | tests/test_workflow_interview_failures.py |
| C42 | integrity | Report wording-assistance fallback outcomes honestly | tests/test_workflow_wording_failures.py |
| C43 | integration | Retire Audio/demo navigation and UI emoji throughout entry points | Controller gate |
| C44 | integration | Add safe item history and stable browser navigation | ui/src/components/workflow/VersionHistory.test.jsx |
| C45 | hosted | Validate the hosted authentication/storage adapter | Controller gate |
| C46 | hosted | Implement the selected hosted adapter in reviewed subpackets | Controller gate |
| C47 | hosted | Audit every legacy route and file for creator isolation | tests/test_workflow_route_access.py |
| C48 | hosted | Rehearse migration and durable recovery | tests/test_workflow_recovery.py |
| C49 | verification | Complete keyboard, screen-reader and responsive journeys | Controller gate |
| C50 | verification | Run full release verification and final diff review | Controller gate |

## Checkpoint packets

Proposed new paths are explicitly assigned implementation destinations. They describe future files.
Read the actual predecessor implementation and frozen contract at dispatch time.
A controller_split packet expands into small named child packets before dispatch. Its acceptance requires all children.
Controller gates capture decisions/evidence. implementation_with_gate packets receive a final controller check.
The detailed task manifest and the packets below contain the same instructions.

### C00 Prove the Freebuff transport and capture the baseline

**Allowed changes**

- Controller runtime evidence for the disposable transport probe and baseline.

**Implementation steps**

1. Controller pins the CLI version and records its actual help output and available terminal transport.
2. Send a read-only nonce task in a disposable directory containing three known files. Capture submitted input, actual answer, terminal/session identity and completion evidence.
3. Repeat with one follow-up and an interruption. Confirm the adapter can associate each result with the correct request.
4. Record repository HEAD, staged/unstaged/untracked paths, Python/npm executables, collected tests and baseline command results. Preserve the current planning changes.

**Acceptance**

- Two distinct prompts receive their matching nonces without manual prompt copy/paste.
- An interrupted or sign-in-blocked task has an explicit status and cannot advance the queue.
- Controller records actual completion evidence and baseline changes before any product task is dispatched.

**Review focus**

Transport version, exact completion detection, one-time authentication and unchanged product files.

**Controller gate**

transport_verified.

### C01 Freeze implementation decisions and the logical contract

**Allowed changes**

- docs/implementation/workflow-contract.md

**Implementation steps**

1. Read the product plan and current storage/API/client seams named in this runbook.
2. Controller records exact schema fields, endpoint shapes, ownership source, local storage choice and hosted auth/storage decision status.
3. Record canonical artifact serialization, revision/CAS rules, idempotency behavior, source/context mapping and retained platform identifiers.
4. Supply a worked create/save/review-or-skip/approve/export example and an error example. Controller reviews the contract before code packets begin.

**Acceptance**

- Every implementation packet refers to an approved contract revision and its digest.
- Hosted provider/account decisions have a named owner and explicit status.
- An owner is obtained from trusted authentication or explicit trusted local mode, with spoofed client owner fields rejected.

**Review focus**

Ambiguous identities, contradictory payload examples and invented provider choices.

**Controller gate**

contract_approved.

### C02 Define workflow domain schemas

**Allowed changes**

- content_machine/workflow/__init__.py
- content_machine/workflow/schemas.py
- tests/test_workflow_schemas.py
- content_machine/workflow/format_registry.py

**Implementation steps**

1. Write failing schema tests for item/context/artifact/snapshot/review/approval inputs from the approved contract.
2. Implement Pydantic models with bounded fields and explicit platform/format combinations.
3. Represent thread segments in order and single-text artifacts as one segment. Preserve exact string contents.
4. Keep ownership and timestamps server-assigned.
5. Create the initial backend capability registry with the approved retained IDs and explicit editing/generation readiness.

**Acceptance**

- Unknown platform/format pairs and invalid revision numbers are rejected.
- Whitespace-only final artifacts cannot be approved.
- Client-supplied ownership cannot replace the authenticated principal.

**Review focus**

Schema/API drift and accidental whitespace normalization.

**Focused test**

tests/test_workflow_schemas.py. Run the exact resolved command from the JSON manifest.

### C03 Add additive workflow storage migration

**Allowed changes**

- content_machine/workflow/migrations.py
- content_machine/storage/db.py
- tests/test_workflow_migrations.py

**Implementation steps**

1. Write isolated tests starting from a fresh DB and a legacy DB with existing content and Comments rows.
2. Create owned item, immutable version, review, approval and idempotency tables using the contract.
3. Connect the migration to the existing initialization seam and preserve row factories/foreign-key behavior.
4. Make repeated initialization safe and atomic.

**Acceptance**

- Fresh and existing databases initialize successfully.
- Running the migration twice preserves counts, IDs and legacy rows.
- A forced migration failure leaves a usable recoverable original state.

**Review focus**

Destructive SQL, constraint coverage and partial migration behavior.

**Focused test**

tests/test_workflow_migrations.py. Run the exact resolved command from the JSON manifest.

### C04 Resolve trusted principals for workflow requests

**Allowed changes**

- content_machine/workflow/access.py
- tests/test_workflow_access.py

**Implementation steps**

1. Write tests using dependency-injected authenticated principals A and B and an unauthenticated caller.
2. Implement the contract's Principal and resolve_principal boundary.
3. Implement explicitly configured local mode and hosted-mode failure behavior.
4. Use the principal for internal ownership. Keep request body, query and untrusted forwarding headers outside that decision.

**Acceptance**

- Hosted requests without configured/valid authentication fail closed.
- Spoofed owner values cannot select B's workspace.
- Local-mode tests are explicitly configured and isolated.

**Review focus**

Implicit default owners, trusting browser-provided ownership and local mode on hosted deployments.

**Focused test**

tests/test_workflow_access.py. Run the exact resolved command from the JSON manifest.

### C05 Store and list owned working items

**Allowed changes**

- content_machine/workflow/items.py
- tests/test_workflow_items.py

**Implementation steps**

1. Write tests for create/list/get/update for two owners with identical display titles.
2. Use opaque IDs, owner-filtered queries and parameterized SQL.
3. Save working content with expected_revision and an idempotency key.
4. Return acknowledged state only after transaction commit.

**Acceptance**

- A cannot load or mutate B's item by ID.
- A stale expected_revision returns a conflict and preserves newer content.
- Retrying the same idempotency key does not create another item or revision.

**Review focus**

Lost updates, title collisions and partial saves.

**Focused test**

tests/test_workflow_items.py. Run the exact resolved command from the JSON manifest.

### C06 Persist immutable content snapshots

**Allowed changes**

- content_machine/workflow/versions.py
- tests/test_workflow_versions.py

**Implementation steps**

1. Write tests that freeze an item's exact artifact/context at a review or approval boundary.
2. Create immutable snapshots associated with item, owner and working revision.
3. Expose owned list/get operations and the canonical digest operation.
4. Keep old snapshots available after further working edits.

**Acceptance**

- Changing one whitespace character changes the artifact digest.
- Repeated freezing of the same acknowledged revision is idempotent.
- Later working edits cannot mutate stored snapshots.

**Review focus**

Mutable history, Unicode/newline transformation and snapshot races.

**Focused test**

tests/test_workflow_versions.py. Run the exact resolved command from the JSON manifest.

### C07 Approve and export an exact saved artifact

**Allowed changes**

- content_machine/workflow/approvals.py
- tests/test_workflow_approvals.py

**Implementation steps**

1. Write failing tests for explicit author approval of the current acknowledged revision.
2. Bind approval to owner, item, snapshot, destination, format and canonical artifact digest.
3. Resolve export from that approved snapshot and the documented UTF-8 serialization.
4. Keep historical approved snapshots accessible to their owner.

**Acceptance**

- A one-character edit or format change requires a new approval.
- Reverting to identical text in a new revision does not revive old approval.
- Export matches the approved segments and invokes zero generation calls.

**Review focus**

Borrowed approval, stale consent and post-approval rewriting.

**Focused test**

tests/test_workflow_approvals.py. Run the exact resolved command from the JSON manifest.

### C08 Restore versions and create linked adaptations

**Allowed changes**

- content_machine/workflow/history.py
- tests/test_workflow_history.py

**Implementation steps**

1. Write tests for read-only historical inspection, restore and adaptation.
2. Restore old content into a new working revision after checking expected_revision.
3. Create another format/destination as a linked unapproved item using the original approved snapshot.
4. Retain the original artifact and approvals through adaptation failure or cancellation.

**Acceptance**

- Restoring preserves both the previous working version and historical snapshot.
- An adaptation starts without inherited approval or AI-review success.
- Cross-owner source snapshots are inaccessible.

**Review focus**

Destructive replacement and cross-item consent.

**Focused test**

tests/test_workflow_history.py. Run the exact resolved command from the JSON manifest.

### C09 Expose owned item CRUD through a small API router

**Allowed changes**

- content_machine/workflow/routes.py
- content_machine/api/app.py
- tests/test_workflow_api_items.py

**Implementation steps**

1. Write TestClient cases for create/list/get/update under /api/workflow/items.
2. Use resolve_principal and the approved request/response models.
3. Map missing, unauthorized, validation and revision-conflict results consistently.
4. Register the router through the existing FastAPI app.

**Acceptance**

- Normal API entry points exercise actual storage behavior.
- Unauthenticated and cross-owner cases return the approved errors.
- Failed writes do not return Saved or a fabricated current revision.

**Review focus**

API-only success mocks and ownership bypass.

**Focused test**

tests/test_workflow_api_items.py. Run the exact resolved command from the JSON manifest.

### C10 Expose history, approval and export actions

**Allowed changes**

- content_machine/workflow/action_routes.py
- content_machine/api/app.py
- tests/test_workflow_api_actions.py
- content_machine/workflow/routes.py

**Implementation steps**

1. Write tests for version history, restore, approve, export and adaptation endpoints.
2. Apply the same principal and revision contract to every action.
3. Return exact text downloads with safe filenames and appropriate content types.
4. Provide explicit review-skip state through the versioned workflow action contract.
5. Register the subrouter in the workflow router and exercise it through TestClient against the normal app.
6. Expose /api/workflow/capabilities from the backend registry and cover it through the normal app entry point.

**Acceptance**

- An unapproved working item cannot use the final-export action.
- Historical owned approved artifacts can be retrieved accurately.
- Failed or skipped AI review never supplies human approval.

**Review focus**

Unguarded file routes, filename collisions and state inferred from navigation.

**Focused test**

tests/test_workflow_api_actions.py. Run the exact resolved command from the JSON manifest.

### C11 Create a platform registry and recognizable icons

**Allowed changes**

- ui/src/lib/platforms.js
- ui/src/components/ui/PlatformIcon.jsx
- ui/src/lib/platforms.test.js

**Implementation steps**

1. Map retained identifiers from constants.js and the approved capability inventory.
2. Add Instagram caption and Reel-script identity/format definitions. Consume editing/generation readiness from the server capability response.
3. Use reviewed licensed brand SVG assets with visible labels and consistent dimensions.
4. Retain neutral script/newsletter choices where a specific provider is absent.

**Acceptance**

- Every retained format has one explicit destination/format mapping.
- An unavailable generation adapter is identified by the server capability response until its packet passes.
- Icons cannot imply an authenticated account or published content.

**Review focus**

Dropped legacy identifiers and generic scripts presented as platform-ready assets.

**Focused test**

ui/src/lib/platforms.test.js. Run the exact resolved command from the JSON manifest.

### C12 Add workflow domain API clients

**Allowed changes**

- ui/src/api/workflow.js
- ui/src/api/workflow.test.js

**Implementation steps**

1. Write request/response and error tests around fetchJson.
2. Implement the approved item, history, skip, approve, export and adaptation calls.
3. Pass revision and idempotency data explicitly.
4. Preserve server conflict details for recovery UI.
5. Load the authoritative capability response alongside item state.

**Acceptance**

- Networking remains inside ui/src/api.
- Request fields match the frozen contract.
- An error response cannot be interpreted as an empty successful result.

**Review focus**

Raw fetch in components and silently swallowed failures.

**Focused test**

ui/src/api/workflow.test.js. Run the exact resolved command from the JSON manifest.

### C13 Manage acknowledged workflow state and saves

**Allowed changes**

- ui/src/app/useWorkflowSession.js
- ui/src/app/useWorkflowSession.test.jsx

**Implementation steps**

1. Write delayed-request tests for load, edit, debounce save, item switch and retry.
2. Track local edits separately from acknowledged server revision.
3. Apply returned state only to its owner/item/request generation.
4. Expose Saving/Saved/Not saved, conflict and recovery without clearing typed content.

**Acceptance**

- A delayed save/load for A cannot replace B or newer A edits.
- Repeated retries use stable idempotency keys.
- Approval and final export wait for the current artifact's required acknowledgement.

**Review focus**

False Saved labels, race conditions and errors that erase input.

**Focused test**

ui/src/app/useWorkflowSession.test.jsx. Run the exact resolved command from the JSON manifest.

### C14 Build the real saved-content landing

**Allowed changes**

- ui/src/components/workflow/ContentList.jsx
- ui/src/components/workflow/ContentList.test.jsx

**Implementation steps**

1. Write cases for loading, actual empty results, loaded items, no search matches and load failure.
2. Show New content and a prominent Resume action naming its saved item.
3. Use actual server status and updated time.
4. Keep previously loaded items visible with an appropriate stale/error indication on refresh failure.

**Acceptance**

- Two same-title items remain distinguishable and independently resumable.
- A load failure never becomes No saved content.
- Scanned articles are absent until deliberately saved or used.

**Review focus**

Synthetic empty-state data and conflating discovery history with drafts.

**Focused test**

ui/src/components/workflow/ContentList.test.jsx. Run the exact resolved command from the JSON manifest.

### C15 Capture own material in the Idea stage

**Allowed changes**

- ui/src/components/workflow/IdeaStage.jsx
- ui/src/components/workflow/IdeaStage.test.jsx

**Implementation steps**

1. Write tests for platform/format selection, notes and an existing draft.
2. Provide equally prominent Your idea and Discover ideas choices.
3. Capture one optional intended point and source/context attachments through shared item state.
4. Preserve a pasted draft exactly until an author edit or accepted suggestion.

**Acceptance**

- No profile or source setup is required for the own-material path.
- Changing stage preserves input and the selected destination.
- Choosing discovery can expose a truthful unavailable/loading state until discovery integration lands.

**Review focus**

Forced interviews and duplicate note forms.

**Focused test**

ui/src/components/workflow/IdeaStage.test.jsx. Run the exact resolved command from the JSON manifest.

### C16 Provide one manual draft editor and explicit AI skip

**Allowed changes**

- ui/src/components/workflow/DraftStage.jsx
- ui/src/components/workflow/DraftStage.test.jsx

**Implementation steps**

1. Write tests for manual edits, supplied drafts and explicit Skip AI review and continue.
2. Use one controlled editor and the same expandable context record from Idea.
3. Save the working artifact and record the explicit skip before approval.
4. Expose existing AI controls only when their matching integration is ready.

**Acceptance**

- Manual drafting reaches approval without a score or an interview.
- A failed AI request remains distinguishable from an explicit skip.
- Changing content invalidates the working approval.

**Review focus**

Review-result prerequisites and duplicate editors.

**Focused test**

ui/src/components/workflow/DraftStage.test.jsx. Run the exact resolved command from the JSON manifest.

### C17 Present the actual approval decision

**Allowed changes**

- ui/src/components/workflow/ApproveStage.jsx
- ui/src/components/workflow/ApproveStage.test.jsx

**Implementation steps**

1. Write tests displaying the full current artifact, destination, format and honest review state.
2. Use one explicit Approve this version action with clear consent wording.
3. Submit the acknowledged revision and show conflicts without losing text.
4. Advance only after the server returns the matching approval.

**Acceptance**

- Pending/failed approval cannot advance to final export.
- Explicit AI skip still requires human approval.
- A stale approval response cannot approve newer edits.

**Review focus**

Extra consent rituals and approval of an earlier artifact.

**Focused test**

ui/src/components/workflow/ApproveStage.test.jsx. Run the exact resolved command from the JSON manifest.

### C18 Copy and download the approved payload

**Allowed changes**

- ui/src/components/workflow/ExportStage.jsx
- ui/src/components/workflow/ExportStage.test.jsx
- ui/src/hooks/useCopyToClipboard.js

**Implementation steps**

1. Write tests for exact approved content, clipboard denial and download initiation failure.
2. Show Copy, Download and selectable content from the approved snapshot.
3. Present per-segment controls for threads and an appropriate whole-artifact download.
4. Offer linked adaptation using the approved version as its source.

**Acceptance**

- Entering or using Export invokes zero model calls.
- Failed copy cannot report Copied.
- Download feedback describes initiation and never claims publication.

**Review focus**

Hidden rewriting and generated files mistaken for browser downloads.

**Focused test**

ui/src/components/workflow/ExportStage.test.jsx. Run the exact resolved command from the JSON manifest.

### C19 Replace tool navigation with the integrated Workflow

**Allowed changes**

- ui/src/components/workflow/WorkflowPage.jsx
- ui/src/app/tabs.js
- ui/src/App.jsx
- ui/src/App.test.jsx

**Implementation steps**

1. Write entry-point tests for Workflow, Lessons and Settings with four stages inside an item.
2. Open the saved-content landing first and resume at the actual saved stage.
3. Integrate the working Idea/Draft/Approve/Export components using useWorkflowSession.
4. Keep registration in tabs.js and App within its documented size target.

**Acceptance**

- The primary journey completes from App without copying between tool pages.
- Resume avoids repeating new-item platform selection.
- Workflow navigation preserves current item and pending input.

**Review focus**

A cosmetic stepper over disconnected old tabs.

**Focused test**

ui/src/App.test.jsx. Run the exact resolved command from the JSON manifest.

### C20 Validate the complete internal manual slice

**Allowed changes**

- ui/src/components/workflow/WorkflowJourney.test.jsx

**Implementation steps**

1. Add an integrated existing LinkedIn draft journey using real workflow clients with mocked transport boundaries.
2. Cover durable save acknowledgement, list/Resume, explicit AI skip, one approval and exact copy/download.
3. Controller runs a browser journey against isolated local storage.
4. Capture actual visual/keyboard evidence and repair the previous packet responsible for any failure.

**Acceptance**

- All four states operate through the normal root entry point.
- Refreshing recovers acknowledged input and actual approval associations.
- The controller records a verified internal slice separately from release readiness.

**Review focus**

Unit-only success and seeded screenshots.

**Controller gate**

manual_slice_reviewed.

### C21 Persist real author facts and source configuration

**Allowed changes**

- content_machine/workflow/settings.py
- content_machine/workflow/settings_routes.py
- tests/test_workflow_settings.py
- content_machine/workflow/routes.py

**Implementation steps**

1. Write owner-isolation and failed-save tests for factual profile and source records.
2. Implement explicit save/read operations using the approved owned storage.
3. Initialize empty author fields and labeled neutral product defaults.
4. Support add/edit/enable/disable sources while preserving attached historical evidence.
5. Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

**Acceptance**

- Blank accounts contain no invented identity or employment history.
- Updating one source preserves other sources.
- Saved records survive reload and seed refresh.

**Review focus**

Global Markdown state leaking between creators.

**Focused test**

tests/test_workflow_settings.py. Run the exact resolved command from the JSON manifest.

### C22 Edit profile and sources through Settings

**Allowed changes**

- ui/src/components/profile/SettingsPage.jsx
- ui/src/api/settings.js
- ui/src/components/profile/SettingsPage.test.jsx

**Implementation steps**

1. Write tests for optional factual fields, sources, unsaved edits, validation and server failure.
2. Use ordinary fields and Save per section.
3. Preserve unsaved inputs when refreshing or visiting Workflow.
4. Link writing preferences to Lessons.

**Acceptance**

- Profile completion is optional.
- A failed save preserves exact input.
- Returning to Workflow restores the active item.

**Review focus**

Hardcoded persona and duplicate rule editors.

**Focused test**

ui/src/components/profile/SettingsPage.test.jsx. Run the exact resolved command from the JSON manifest.

### C23 Scope governed writing preferences to their creator

**Allowed changes**

- content_machine/workflow/preferences.py
- content_machine/workflow/preference_routes.py
- tests/test_workflow_preferences.py
- content_machine/workflow/routes.py

**Implementation steps**

1. Use failing tests to exercise manual add/edit/stop-using and actual conflict/cap outcomes.
2. Reuse governed conflict/cap logic through the contract-approved storage seam.
3. Preserve origin and change history and keep AI proposals pending.
4. Keep old local/CLI records recoverable under the explicit migration mapping.
5. Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

**Acceptance**

- Creator A's preferences do not affect B.
- A conflicting or blocked save cannot report activation.
- Stopping a preference persists and does not rewrite approved artifacts.

**Review focus**

Bypassing lessons governance and ambiguous legacy ownership.

**Focused test**

tests/test_workflow_preferences.py. Run the exact resolved command from the JSON manifest.

### C24 Simplify Lessons to the single preference editor

**Allowed changes**

- ui/src/components/lessons/LessonsTab.jsx
- ui/src/api/lessons.js
- ui/src/components/lessons/LessonsTab.test.jsx

**Implementation steps**

1. Write cases for empty/loading/failed/active/pending preferences and blocked activation.
2. Show Add/Edit/Stop using with explicit human Save and use.
3. Use actual returned activation status and plain conflict text.
4. Keep optional existing proposals manageable through the same collection.

**Acceptance**

- A creator can finish publishing preparation without visiting Lessons.
- AI suggestions activate only after an explicit author decision.
- A factual correction stays item-specific unless deliberately generalized.

**Review focus**

False success and a fifth required stage.

**Focused test**

ui/src/components/lessons/LessonsTab.test.jsx. Run the exact resolved command from the JSON manifest.

### C25 Attach real discovery sources to the working item

**Allowed changes**

- content_machine/workflow/discovery.py
- content_machine/workflow/discovery_routes.py
- tests/test_workflow_discovery.py
- content_machine/workflow/routes.py

**Implementation steps**

1. Reuse connector/Oracle seams with trusted creator-specific source configuration.
2. Preserve item URL, title, available excerpt and retrieval context.
3. Distinguish partial failure, no new results and unavailable history.
4. Create an owned working item only after Save/Use.
5. Register the subrouter in the workflow router and exercise it through TestClient against the normal app.

**Acceptance**

- Title-only source material is identified accurately.
- A failed connector leaves other successful items usable.
- Real source metadata cannot become a fabricated personal experience.

**Review focus**

Dropped excerpts, global connector settings and invented fallback summaries.

**Focused test**

tests/test_workflow_discovery.py. Run the exact resolved command from the JSON manifest.

### C26 Unify discovery presentation inside Idea

**Allowed changes**

- ui/src/components/workflow/DiscoveryPane.jsx
- ui/src/components/workflow/IdeaStage.jsx
- ui/src/components/workflow/DiscoveryPane.test.jsx
- ui/src/api/workflow.js

**Implementation steps**

1. Show one discovery list with search, optional filters and Use this idea.
2. Keep refresh/status/Manage sources contextual.
3. Use the same source selection behavior for new and previously found items.
4. Preserve personal notes when the creator switches entry routes.
5. Extend the workflow domain client with the actual discovery endpoints and preserve errors.

**Acceptance**

- Your idea and Discover remain equally prominent.
- Filters can be cleared and failures expose a useful next action.
- Source configuration changes return to the same draft.

**Review focus**

Taxonomy noise and inconsistent archive actions.

**Focused test**

ui/src/components/workflow/DiscoveryPane.test.jsx. Run the exact resolved command from the JSON manifest.

### C27 Make voice results target a stable field context

**Allowed changes**

- ui/src/hooks/useVoiceRecording.js
- ui/src/hooks/useVoiceRecording.test.js

**Implementation steps**

1. Write delayed-transcription tests with item/revision/field targets.
2. Expose recording and transcribing status independently of the active recording flag.
3. Release microphone resources when the target stage becomes inactive.
4. Return a recoverable transcript when intervening edits prevent safe insertion.

**Acceptance**

- Permission denial leaves typing usable.
- A delayed transcript cannot enter another item or account.
- Stopping shows processing accurately until a result or error.

**Review focus**

Late insertion, silent text replacement and hidden active microphones.

**Focused test**

ui/src/hooks/useVoiceRecording.test.js. Run the exact resolved command from the JSON manifest.

### C28 Place labeled dictation beside intake and editing

**Allowed changes**

- ui/src/components/workflow/DictationControl.jsx
- ui/src/components/workflow/IdeaStage.jsx
- ui/src/components/workflow/DraftStage.jsx
- ui/src/components/workflow/DictationControl.test.jsx

**Implementation steps**

1. Add Dictate/Stop to the intended fields using the shared hook.
2. Show local recording/processing/error status and an editable transcript.
3. Bind insertion to the originating field and preserve typed text.
4. Document the actual browser/backend processing path in contextual help.

**Acceptance**

- The full workflow requires no separate Audio destination.
- Keyboard start/stop and cancellation preserve input.
- An unavailable microphone offers continued typing.

**Review focus**

Decorative-only controls and field labeling.

**Focused test**

ui/src/components/workflow/DictationControl.test.jsx. Run the exact resolved command from the JSON manifest.

### C29 Build an owner-specific editorial context snapshot

**Allowed changes**

- content_machine/workflow/context.py
- content_machine/knowledge/provider.py
- tests/test_workflow_context.py

**Implementation steps**

1. Write tests for source claims, author experience, interpretation and owned settings/preferences.
2. Build one immutable context snapshot for the writing request.
3. Pass scoped context explicitly through the provider seam while retaining supported local callers.
4. Keep credentials outside stored draft/evidence payloads.

**Acceptance**

- A and B receive only their own author/preferences context.
- Changing settings affects later requests and leaves existing approved snapshots intact.
- Source-only commentary requires no invented personal story.

**Review focus**

Per-request process environment mutation and globally loaded author facts.

**Focused test**

tests/test_workflow_context.py. Run the exact resolved command from the JSON manifest.

### C30 Generate the initial selected-platform draft

**Allowed changes**

- content_machine/workflow/writing.py
- content_machine/workflow/writing_routes.py
- tests/test_workflow_writing.py
- content_machine/workflow/routes.py
- content_machine/workflow/format_registry.py

**Implementation steps**

1. Write offline tests capturing the actual model request inputs.
2. Reuse the appropriate existing generation seams with the approved context snapshot and platform/format.
3. Return a proposed artifact associated with its input version.
4. Preserve source/notes and an honest error when generation fails.
5. Register the subrouter in the workflow router and exercise it through TestClient against the normal app.
6. Controller splits this packet into children with concrete allowlists before any implementation dispatch.

**Acceptance**

- Per-item notes and excerpts actually reach the writing request.
- A supplied draft is unchanged until a creator requests/accepts a rewrite.
- Provider failure produces no template disguised as successful generation.

**Review focus**

Context rendered only in UI and wrong platform prompts.

**Controller gate**

small_child_packets_approved.

### C31 Add the actual Instagram caption adapter

**Allowed changes**

- content_machine/workflow/adapters/instagram_caption.py
- content_machine/workflow/format_registry.py
- tests/test_instagram_caption.py

**Implementation steps**

1. Write tests for supported format registration, grounded prompt inputs and failure behavior.
2. Generate editable caption text from the supplied evidence and creator point.
3. Apply contract-approved applicable limits before approval.
4. Register the adapter under the exact destination/format ID.

**Acceptance**

- Caption requests return caption artifacts.
- Missing evidence does not trigger invented metrics or anecdotes.
- Availability becomes true only when the adapter checks pass.

**Review focus**

Relabeling a generic video script as a caption.

**Focused test**

tests/test_instagram_caption.py. Run the exact resolved command from the JSON manifest.

### C32 Add the actual Instagram Reel-script adapter

**Allowed changes**

- content_machine/workflow/adapters/instagram_reel.py
- content_machine/workflow/format_registry.py
- tests/test_instagram_reel.py

**Implementation steps**

1. Write tests for a script artifact with grounded spoken text and production cues.
2. Implement the Reel-specific adapter using shared generation logic.
3. Preserve required visual/camera/pause markers where applicable.
4. Expose the format independently of Caption.

**Acceptance**

- A Reel script is labeled as text for production.
- Unsupported benchmark/numeric sections are omitted or returned as author questions.
- A caption remains separately selectable and separately approved.

**Review focus**

Rendered-video promises and compulsory bundles.

**Focused test**

tests/test_instagram_reel.py. Run the exact resolved command from the JSON manifest.

### C33 Preserve and validate X-thread segments

**Allowed changes**

- content_machine/workflow/adapters/x_thread.py
- content_machine/workflow/format_registry.py
- tests/test_workflow_x_thread.py

**Implementation steps**

1. Reuse the current X generator through the selected-platform adapter contract.
2. Parse or request ordered post segments and validate configured per-post constraints.
3. Keep the approved segmentation in the immutable artifact.
4. Return actionable errors before approval when segmentation is invalid.

**Acceptance**

- Per-post copy and full download use the exact approved boundaries.
- No silent shortening occurs during export.
- An incomplete/overlong response cannot appear ready for approval.

**Review focus**

Total-string length mistaken for valid thread structure.

**Focused test**

tests/test_workflow_x_thread.py. Run the exact resolved command from the JSON manifest.

### C34 Preserve short/long YouTube script capabilities

**Allowed changes**

- content_machine/workflow/adapters/youtube.py
- content_machine/workflow/format_registry.py
- tests/test_workflow_youtube.py

**Implementation steps**

1. Map existing short/long script identifiers without removing retained history.
2. Use grounded script generation with actual production cues.
3. Make unsupported evidence sections optional.
4. Label deliverables accurately as scripts.

**Acceptance**

- Short and long formats remain distinct.
- A source without numbers yields no forced benchmark chapter.
- Export retains the exact approved script text.

**Review focus**

Lost formats and fabricated production/performance claims.

**Focused test**

tests/test_workflow_youtube.py. Run the exact resolved command from the JSON manifest.

### C35 Preserve newsletter and generic-script capabilities

**Allowed changes**

- content_machine/workflow/adapters/retained_formats.py
- content_machine/workflow/format_registry.py
- tests/test_workflow_retained_formats.py

**Implementation steps**

1. Implement the contract's honest mappings for newsletter and the retained general short-script path.
2. Reuse existing generators and keep their legacy identifier translation explicit.
3. Validate actual artifact structure before approval.
4. Keep format changes as separately approvable adaptations.

**Acceptance**

- Existing formats/history have an explicit supported mapping.
- Newsletter is a draft and generic script names its actual capability.
- Destination/format changes cannot inherit approval.

**Review focus**

Silent capability removal and inflated platform claims.

**Focused test**

tests/test_workflow_retained_formats.py. Run the exact resolved command from the JSON manifest.

### C36 Associate AI review with its exact owned snapshot

**Allowed changes**

- content_machine/workflow/reviews.py
- content_machine/council/loop.py
- tests/test_workflow_reviews.py
- content_machine/workflow/writing_routes.py

**Implementation steps**

1. Write tests capturing reviewed bytes/context and subsequent sanitizer/revision changes.
2. Invoke Council using the owned immutable input context.
3. Record actual reviewed snapshot, score basis, actions and proposed revisions separately.
4. Preserve fail/skip/earlier/current states and the ability to approve without a score.
5. Use a single review pass for workflow advice and present sanitizer or writer changes as proposals. Preserve existing Council iteration callers.
6. Expose the owned review operation through writing_routes.py and test its normal HTTP entry with scoped principals.

**Acceptance**

- Returned changed wording never inherits a review of different content.
- Raw and normalized scores have explicit distinct scales.
- Reviewing A cannot incorporate B's profile/preferences or overwrite B.

**Review focus**

Review/source mismatch and global author context.

**Focused test**

tests/test_workflow_reviews.py. Run the exact resolved command from the JSON manifest.

### C37 Connect drafting, AI feedback and revision comparison

**Allowed changes**

- ui/src/components/workflow/DraftStage.jsx
- ui/src/components/workflow/ReviewPanel.jsx
- ui/src/components/workflow/ReviewPanel.test.jsx
- ui/src/api/workflow.js

**Implementation steps**

1. Connect Create draft, optional Review draft and one wording suggestion to versioned APIs.
2. Lead with actionable feedback and a readable current/proposed comparison.
3. Accept a proposal as a new working version and retain the prior snapshot.
4. Keep pending/failure/earlier-version output attached to its origin.
5. Extend the domain client with actual owned generation/review operations used by this UI.

**Acceptance**

- Cancel changes nothing and acceptance invalidates old working approval.
- An explicit skip remains available after a failed review.
- Late results cannot force navigation or replace newer text.

**Review focus**

Multiple polish entry points and stale revisions accepted into another item.

**Focused test**

ui/src/components/workflow/ReviewPanel.test.jsx. Run the exact resolved command from the JSON manifest.

### C38 Separate provable demo records from creator work

**Allowed changes**

- content_machine/workflow/legacy_import.py
- tests/test_workflow_legacy_import.py

**Implementation steps**

1. Write migration tests with proven synthetic, actual legacy and ambiguous records.
2. Require an explicit owner mapping for imported user work.
3. Keep recoverable backups and quarantine proven synthetic records outside normal creator work.
4. Make repeated import safe and preserve historical Comments/exports.

**Acceptance**

- Private workspaces retain actual creator provenance. Guest examples stay labelled and scoped to their own guest workspace.
- Unknown lineage/approval stays unknown.
- Import twice preserves edits, record counts and recoverability.

**Review focus**

Mass deletion and guessed ownership.

**Focused test**

tests/test_workflow_legacy_import.py. Run the exact resolved command from the JSON manifest.

### C39 Remove automatic public-demo seeding from the real entry

**Allowed changes**

- api/index.py
- content_machine/bootstrap.py
- tests/test_workflow_bootstrap.py

**Implementation steps**

1. Write bootstrap tests for real empty private workspace initialization.
2. Remove automatic sample seeding from private cold starts. Preserve the explicit guest-seeding integration point for the hosted packets.
3. Use the selected deployment storage configuration.
4. Initialize actual accounts without invented persona or active learned rules.

**Acceptance**

- Private cold starts leave new creator workspaces empty and retain existing saved records.
- Restart/deploy cannot replace saved creator settings.
- Temporary storage is identified until the durable hosted gate passes.

**Review focus**

A new UI backed by the old demo cold start.

**Focused test**

tests/test_workflow_bootstrap.py. Run the exact resolved command from the JSON manifest.

### C40 Return actual Council and distribution failures

**Allowed changes**

- content_machine/api/app.py
- tests/test_workflow_failure_routes.py

**Implementation steps**

1. Write failed-provider cases for the existing API seams.
2. Remove unrelated seeded review/bundle substitution in the real workflow.
3. Return actionable structured failures with the original request identity.
4. Retain preserved inputs and usable earlier-version data.

**Acceptance**

- A quota/provider failure cannot return sample success.
- Failed review cannot set review-complete or human-approved state.
- Existing clients receive explicit errors through their domain adapters.

**Review focus**

A labeled replay still being used as actual work.

**Focused test**

tests/test_workflow_failure_routes.py. Run the exact resolved command from the JSON manifest.

### C41 Return actual briefing and synthesis failures

**Allowed changes**

- content_machine/interview/engine.py
- tests/test_workflow_interview_failures.py

**Implementation steps**

1. Write cases for unavailable source context, invalid model output and exhausted routes.
2. Return explicit failure/partial status instead of invented tension or template success.
3. Keep optional generic prompts labeled as generic help.
4. Preserve author notes for manual continuation.

**Acceptance**

- Title-only input cannot produce a confident sourced briefing by fallback.
- Typed notes survive a failed synthesis.
- Manual drafting and explicit AI skip remain possible.

**Review focus**

Invented narrative used to conceal failure.

**Focused test**

tests/test_workflow_interview_failures.py. Run the exact resolved command from the JSON manifest.

### C42 Report wording-assistance fallback outcomes honestly

**Allowed changes**

- content_machine/humanize/transformer.py
- content_machine/schemas.py
- tests/test_workflow_wording_failures.py

**Implementation steps**

1. Write cases distinguishing model rewrite, deterministic cleanup and complete failure.
2. Expose the actual operation/result provenance.
3. Show cleanup as a proposal associated with its original version.
4. Keep exact saved/approved artifacts immutable.

**Acceptance**

- Local cleanup cannot claim a successful model rewrite or authenticity verification.
- Changed text has a new review/approval status.
- Failure retains input and a useful retry/manual route.

**Review focus**

Silent sanitizer success and misleading humanized badges.

**Focused test**

tests/test_workflow_wording_failures.py. Run the exact resolved command from the JSON manifest.

### C43 Retire Audio/demo navigation and UI emoji throughout entry points

**Allowed changes**

- ui/src/App.jsx
- ui/src/app/tabs.js
- ui/src/lib/topics.js
- ui/src/App.test.jsx
- ui/src/components/audio/AudioTab.jsx
- ui/src/components/audio/AudioTab.test.jsx
- ui/src/components/DemoBanner.jsx
- ui/src/components/DemoBanner.test.jsx
- ui/src/components/SampleStory.jsx
- ui/src/components/SampleStory.test.jsx
- ui/src/lib/constants.js
- ui/src/lib/topics.test.js

**Implementation steps**

1. Update root navigation tests to the reviewed destinations and integrated workflow.
2. Retire obsolete guide/sample components and Audio registration within the creator workflow. Preserve the guest entry and mode status in the hosted design.
3. Use professional topic/action presentation through the shared registry.
4. Keep original content text intact while changing interface labels.
5. Split retirement into controller-issued child packets by navigation, obsolete components, and interface labels before dispatch. Adjust tests for the intended removal and verify rendered UI labels across every remaining destination.

**Acceptance**

- Normal entry points expose the agreed Workflow/Lessons/Settings structure.
- Mic input remains available at real fields.
- Private workflows have no guide toggle or sample launcher competing with content creation. The explicit hosted guest mode remains supported.

**Review focus**

Dormant old navigation and accidental modification of authored text.

**Controller gate**

retirement_children_reviewed.

### C44 Add safe item history and stable browser navigation

**Allowed changes**

- ui/src/app/workflowNavigation.js
- ui/src/components/workflow/VersionHistory.jsx
- ui/src/components/workflow/VersionHistory.test.jsx
- ui/src/components/workflow/WorkflowPage.jsx

**Implementation steps**

1. Implement private item/stage URLs through the selected existing routing seam.
2. Open old snapshots read-only with Compare and Restore as new version.
3. Restore focus and active item/stage after settings/history detours.
4. Keep the current unsaved draft while historical data loads or fails.

**Acceptance**

- Back/Forward does not rerun AI or clear text.
- Viewing history cannot grant approval.
- Direct Export navigation handles missing prerequisites visibly.

**Review focus**

Navigation inferred as workflow completion and destructive restoration.

**Focused test**

ui/src/components/workflow/VersionHistory.test.jsx. Run the exact resolved command from the JSON manifest.

### C45 Validate the hosted authentication/storage adapter

**Allowed changes**

- docs/implementation/hosted-workspace-decision.md

**Implementation steps**

1. Use the confirmed Supabase Auth and Postgres design with Google sign-in and anonymous guests. Verify the actual project, account and deployment prerequisites.
2. Record trusted principal verification, durable store guarantees, CORS/origin configuration and credential provisioning.
3. Produce provider-specific implementation subpackets with exact files and tests.
4. Review the adapter before hosted implementation or real-data migration.

**Acceptance**

- Account/cost/credential prerequisites are explicit.
- Ephemeral Vercel /tmp cannot satisfy acknowledged durable saves.
- Provider-specific work remains blocked until this decision is complete.

**Review focus**

A placeholder provider treated as a private production system.

**Controller gate**

hosted_adapter_decision.

### C46 Implement the selected hosted adapter in reviewed subpackets

**Allowed changes**

- {controller_supplied_hosted_allowlist}

**Implementation steps**

1. Controller replaces this packet with small concrete provider-specific children after the hosted decision.
2. Freebuff implements one child at a time with failing identity/storage tests.
3. Exercise actual authenticated access and durable recovery in the selected environment.
4. Return credentials/setup blockers as typed status for one-time user action.

**Acceptance**

- Every dispatched child has concrete paths and commands, with all placeholders resolved.
- Unauthenticated and forged-principal requests fail.
- Acknowledged content survives the chosen deployment restart boundary.

**Review focus**

Dispatching an unresolved architecture task to the implementer.

**Controller gate**

hosted_children_reviewed.

### C47 Audit every legacy route and file for creator isolation

**Allowed changes**

- content_machine/workflow/route_access.py
- content_machine/api/app.py
- tests/test_workflow_route_access.py

**Implementation steps**

1. Enumerate all existing read/write/static-file routes and identify private data flows.
2. Apply the selected hosted access boundary to legacy routes as well as /api/workflow.
3. Scope or explicitly disable unsupported global-data routes in hosted mode while preserving supported local callers.
4. Test direct IDs, paths, history, sources, profile, preferences and late results across two creators.

**Acceptance**

- Authenticated B cannot access A through an older endpoint or file path.
- Global Markdown/SQLite/process environment cannot select another creator's author data.
- Static SPA fallback and unknown /api behavior remain correct.

**Review focus**

Securing only the new endpoints.

**Focused test**

tests/test_workflow_route_access.py. Run the exact resolved command from the JSON manifest.

### C48 Rehearse migration and durable recovery

**Allowed changes**

- tests/test_workflow_recovery.py

**Implementation steps**

1. Use backed-up isolated legacy data with explicit owner assignments.
2. Exercise interrupted save/import, repeated migration and restart/redeploy recovery.
3. Verify unchanged historical artifacts and source/approval associations.
4. Exercise export of an unapproved recovery backup separately from final approval.

**Acceptance**

- Failed/partial operations preserve recoverable data.
- Seed updates and repeat migrations cannot overwrite creator edits.
- Known synthetic and uncertain records are handled according to their actual provenance.

**Review focus**

A successful fresh install mistaken for safe migration.

**Focused test**

tests/test_workflow_recovery.py. Run the exact resolved command from the JSON manifest.

### C49 Complete keyboard, screen-reader and responsive journeys

**Allowed changes**

- ui/src/components/workflow/WorkflowJourney.test.jsx
- docs/implementation/workflow-ui-verification.md

**Implementation steps**

1. Controller exercises own notes, discovery, existing draft, explicit AI skip and manual export.
2. Check focus/labels/errors/linear comparison using keyboard and a screen reader.
3. Check 320 CSS-pixel reflow, 200% text resize, long content and phone keyboard.
4. Record actual evidence, failures and unperformed checks. Repair the owning code packet for each observed failure.

**Acceptance**

- All text and primary actions stay reachable and readable.
- Icons have visible labels or accessible names and statuses have textual meaning.
- A screenshot or worker claim alone cannot mark a manual scenario passed.

**Review focus**

Invented browser/accessibility evidence.

**Controller gate**

ui_journeys_reviewed.

### C50 Run full release verification and final diff review

**Allowed changes**

- docs/implementation/workflow-release-evidence.md

**Implementation steps**

1. Controller reruns collected focused tests, the full pytest suite, mandated unittest discovery, frontend suite and production build.
2. Verify the complete retained-platform matrix including both Instagram deliverables.
3. Review staged, unstaged, untracked and generated output against the accepted checkpoint baseline.
4. Record exact command exit codes, revision/diff digest, manual evidence, remaining limitations and release disposition.

**Acceptance**

- Every required test/check was actually run against the reviewed revision.
- Tracked ui/dist matches the accepted source build.
- All mandatory product gates pass before release is marked ready.

**Review focus**

Rubber-stamped completion, stale build artifacts and unreviewed final edits.

**Controller gate**

release_reviewed.

## Validation and current status

The 51 checkpoints describe the supervised implementation sequence. C00 through C07 are accepted, and later checkpoints remain in progress or pending.
The transport probe ran in a disposable three-file directory.
Two automated turns completed with matching nonces and correct fixture contents.
The persisted chat contains isComplete=true on both corresponding AI records.
An Escape cancellation produced an interrupted response.
A recovery prompt and independent checks complete the remaining transport-readiness evidence.
The recovery prompt subsequently returned its expected nonce and RECOVERED marker.
The controller records cancellation before sending Escape. Interrupted responses also have isComplete=true, so that field alone cannot advance a checkpoint.
The user authorized the repository-context handoff. The terminal integration has completed implementation and repair rounds, with evidence in [the integration record](freebuff-integration.md).
Actual product-task acceptance records follow controller review of implemented work.
The baseline source passed 375 pytest cases, 245 unittest cases, 132 frontend tests across 34 files and the production build. Frontend checks used temporary Node 22.23.4, matching CI's major version.
The earlier Node 24 runs were interrupted during a long startup. The completed Node 22 result establishes the usable baseline command.
