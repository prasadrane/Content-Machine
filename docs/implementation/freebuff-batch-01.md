# Freebuff implementation batch 01

Prasad requested six concurrent Freebuff implementation workers. The current CLI session reports zero internal subagent-spawn tools. Batch attempt 2 therefore runs six normal Freebuff CLI sessions, with Codex coordinating their file ownership and integration. These are six separate worker sessions. This batch replaces sequential execution for the workstreams below while preserving the product requirements and acceptance gates in `freebuff-task-plan.md`. The implementation checkout is `C:\Users\mamat\Github\Content-Machine\.orchestration\worker`.

Read the R00 reviewer corrections at `C:\Users\mamat\Github\Content-Machine\.orchestration\controller\R00\attempt-1\review.md`. The current source has accepted C00–C09 and uncommitted partial work. Preserve the partial work and finish it under its assigned owner.

## Execution contract

1. Each normal CLI session implements one named worker scope below. Codex records its actual terminal and conversation identities. At most six implementation sessions run concurrently. Each worker returns its own actual completion state.
2. Tell every worker that it shares the checkout with others, owns only its listed files, must preserve others' changes, and must not spawn additional implementation workers. The coordinator owns cross-workstream integration after the workers finish.
3. Use meaningful tests first. Preserve actual failing and passing output. Every test command must use the serialized wrapper shown below. Backend checks still run through the production-storage guard, and frontend checks use Node/Vitest with `--maxWorkers=1`. The wrapper holds a Windows mutex so test processes queue while code edits remain parallel. This avoids the worker-startup timeouts seen in R00.
4. Keep existing API signatures and domain semantics. Reuse ownership, CAS, idempotency, atomic transaction, immutable-version, approval and exact-export services. Preserve existing data, credentials and the frozen Council rubric.
5. Use the shared editorial `cm-*` styles, semantic labelled controls and professional icons. Frontend networking belongs in `ui/src/api/`.
6. Preserve the server's exact approved text, segment boundaries and download filename. Keep saved input visible when requests fail. Treat AI review as optional and human approval as explicit.
7. The coordinator reviews worker outputs, repairs integration within its own scope and runs the combined checks. Return one batch report with each worker's actual completion state, files, test commands/counts, unresolved issues and final integration results. Stop for independent review. Keep Git commits, pushes, production data and deployment actions with the reviewer.

## Frozen shared interfaces

- `ui/src/api/workflow.js` retains its existing exports. Add `getDownload(itemId, versionId)` returning `{ blob, filename, artifactDigest }` from the authenticated same-origin binary export response. A failed request rejects with the existing `ApiError` contract.
- `ui/src/lib/platforms.js` retains `PLATFORMS`, `FORMATS`, `getPlatform(id)`, `getFormat(destination, format)` and `resolveLegacyFormat(id, destination?)`. Identity metadata stays separate from runtime server readiness.
- `PlatformIcon` is a default export taking `platform`, optional `size` and `className`, and renders a decorative icon beside a visible label.
- `useWorkflow` retains its existing returned state and handlers. Worker 4 may add `reviewIsCurrent`, which is true only when the review is tied to the acknowledged working revision and the draft is clean. Worker 5 consumes this flag before labelling a review as current. Extra fields must preserve existing callers.
- The root page is the default export `WorkflowTab` from `ui/src/components/workflow/WorkflowTab.jsx`. The existing app shell keeps it mounted while another tab is shown.
- Runtime generation remains unavailable for every workflow pair until a real generation adapter and route pass their later checkpoint. R00 verified the endpoint already reports false. Preserve that truthful behavior. A registry redesign is outside this batch.

## Worker 1 — C10 action boundary

Own only `content_machine/workflow/action_routes.py`, `skip_review.py`, `routes.py` and `tests/test_workflow_api_actions.py`.

1. Inspect the existing five action API tests and the accepted domain tests. Add missing HTTP-boundary cases that establish validation, nested item/version ownership, correct conflict envelopes and committed acknowledgement.
2. Cover required and blank idempotency keys for the mutation routes, missing approval fields, wrong digest, stale revision, same-owner wrong-item version IDs, and retries with identical versus changed requests.
3. Exercise a request-owned outer transaction and a real deferred-commit failure for the action boundaries. Verify rollback of mutation and idempotency success, then retry the same key after removing the forced failure.
4. Check exact export text/headers/filename and thread JSON, read-only history, and unapproved adaptation/restore export denial. Add the contract's skip-after-approval preservation case.
5. Keep routes thin and use `commit_workflow_mutation`. Repair only defects demonstrated by the boundary tests. The accepted services already test many domain cases.

Pass when the action/item tests and guarded backend regression pass, the API returns truthful readiness, and failed commits never report success. The existing missing-auth/no-database test is in C09. Digest parity is currently correct and is owned by Worker 4's regression tests.

## Worker 2 — C11 platform identity and icons

Own only `ui/src/lib/platforms.js`, `platforms.test.js`, `ui/src/components/ui/PlatformIcon.jsx`, and `BOOTSTRAP-ICONS-LICENSE.txt`.

1. Verify the existing canonical pairs, legacy aliases and platform/format labels against the contract.
2. Retain recognizable LinkedIn, Instagram, X and YouTube icons and neutral newsletter/video icons. Preserve asset attribution and license.
3. Verify consistent size, decorative SVG accessibility and usable visible labels at call sites through component tests. Preserve the frozen public interface above.
4. Avoid inferring connected accounts, generation readiness or publication from an icon.

Pass when all retained formats and aliases are covered, icon tests pass, and no decorative emoji is introduced. The existing 15 platform tests passed during R00 and must keep passing.

## Worker 3 — C12 workflow API client

Own only `ui/src/api/workflow.js` and `workflow.test.js`.

1. Reject missing or blank request IDs before a mutation reaches fetch. Preserve stable nonblank keys and exact request bodies.
2. Add the frozen `getDownload` interface using the server's binary export response. Return its Blob, safe `Content-Disposition` filename and artifact digest. Preserve JSON export for clipboard and per-thread-post copy.
3. Preserve authenticated same-origin transport, the `ApiError` detail/status/body contract and all existing exports.
4. Test exact endpoint encoding, key/body transmission, JSON versus binary handling, headers and error responses. A missing/invalid expected filename produces an actionable error instead of inventing one.

Pass when client tests demonstrate exact content handling and no error can become an empty success. All raw fetch calls remain in this API module or existing shared API transport.

## Worker 4 — C13 workflow state and digest regression

Own only `ui/src/components/workflow/useWorkflow.js`, new `useWorkflow.test.jsx`, `workflowUtils.js` and new `workflowUtils.test.js`.

1. Preserve the existing hook facade. Decouple item loading from capability loading so a capability failure preserves successful saved-work results and previously loaded items.
2. Track local edits separately from acknowledged revisions. Test delayed loads/saves, changing items, cleanup, failed requests and newer edits while a request is pending. A late response cannot replace the wrong item or erase newer text.
3. Keep the same key and exact original body for identical failed mutation retries. Surface conflicts without clearing the draft or pretending a save completed.
4. Add `reviewIsCurrent` based on a verified input-version/revision association and a clean local draft. A successful skip response can bind its returned review to that request's acknowledged revision. On reopen, verify the association through actual owned version history. Failed review, earlier-version review and explicit skip remain distinct.
5. Preserve the current digest algorithm and add fixed parity vectors for Unicode, CRLF, trailing whitespace, quotes and ordered thread segments. Independent current vectors are in the R00 review probes. Keep digest inputs limited to the contract fields.
6. Use the server filename through Worker 3's download response in the UI. Retire an unused client filename implementation only after confirming all callers.

Pass when state/digest tests cover the failure and ordering cases and existing hook callers remain compatible.

## Worker 5 — C14–C19 manual workflow presentation

Own new or existing presentation files under `ui/src/components/workflow/`, excluding every file owned by Worker 4. In particular own `WorkflowTab.jsx`, `WorkflowTab.test.jsx`, `ContentList`, `IdeaStage`, `DraftStage`, `ApproveStage`, `ExportStage` and their focused tests as needed. Keep modules within the repository size rules.

1. Complete the missing `WorkflowTab` default export using the frozen hook/API/platform interfaces. Reuse the existing journey tests and split presentation into readable components.
2. Show actual saved-work loading, empty, error, stale-refresh and list states. Offer New content and a prominent Resume naming the item. Same-title records remain independently resumable.
3. Let the author select one actual destination/format and supply notes or an existing draft. Show Your idea and Discover ideas with equal prominence. Discovery may show an explicit unavailable state until its actual integration is ready.
4. Present the four stages inside one item. Preserve exact pasted text and context, use explicit save feedback, and keep manual drafting available. Enable AI controls only when their real integration is ready.
5. Record explicit Skip AI review and continue against the saved revision. Show review state as current only when the hook verifies it. Navigation never grants review success or approval.
6. Display the full saved artifact, destination and format for approval. Require an explicit consent action and a successful matching server approval before advancing. Dirty, blank or pending input cannot be silently approved.
7. Export the approved server snapshot. Use JSON segments for exact copy and Worker 3's binary response for download. Handle clipboard denial and download initiation failure. Show the actual approved version and preserve thread boundaries. Offer an adaptation only from an owned approved source.
8. Test the real component with mocked transport boundaries, including failed save preserving exact text, stable retry keys, resume, explicit skip, consent, failed approval, copy errors and download metadata.

Pass when the root workflow component exists, the manual journey tests pass and the integration build resolves it. The coordinator owns the existing App/tab registration, so report any shell integration requirement to it.

## Worker 6 — C43c professional labels and topic identity

Own only `ui/src/lib/topics.js`, `topics.test.js`, `constants.js`, `ui/src/components/oracle/**`, `ui/src/components/council/**` and `ui/src/components/distribute/**`.

1. Review the partial emoji-removal work and preserve stored creator text and legacy history values.
2. Finish remaining decorative UI emoji, including `AnchorForm`'s Humanize Polish label, using labelled professional icons where useful. Keep existing action behavior.
3. Preserve backend topic identifiers as filter values. Plain labels are display formatting. R00 confirmed normal loaded history and active-batch filters use raw IDs. Fix the fallback constants or normalization only where a failing test establishes a mismatch before/after failed initial history loading.
4. Test visible plain labels, raw callback/filter identity, counts and action accessibility. Preserve existing Council controls and limits.

Pass when the affected focused suites pass and no authored text or persisted topic data is modified.

## Coordinator integration and report

The coordinator alone owns final integration in `ui/src/App.jsx`, `ui/src/App.test.jsx`, `ui/src/app/tabs.js` and `ui/src/app/tabs.test.js`. Keep Workflow, Lessons and Settings as the navigation, with no standalone Audio page or guide-toggle noise. Preserve the mounted workflow state across tab changes.

After all six workers finish, review their changes together, resolve interface defects and run the focused suites serially, the guarded full backend unittest suite, the full frontend suite and a Vite production build to the plan's ignored output directory. Record every actual result. Browser and hosted/live checks remain their own later gates. Report any missing worker capability or unfinished work explicitly.

Use the Python and Node executables and guarded-test launcher from `freebuff-task-plan.md`. Every worker report must include its task name, actual agent ID, changed paths, tests and exit codes, scope exceptions requested and remaining issues. The coordinator returns the combined report and waits for independent review before the next batch.

## Serialized test commands for workers

Use the following PowerShell forms, replacing the worker ID and focused test path with your assignment. Bash tools may invoke the same executable and arguments with their normal shell syntax. The wrapper invokes the guarded launcher for every backend test.

```powershell
$cmPython = 'C:\Users\mamat\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe'
$cmBatchChecks = 'C:\Users\mamat\Github\Content-Machine\.orchestration\controller\batch-test-runner.py'
& $cmPython $cmBatchChecks --kind backend --worker W1 -- -m pytest tests/test_workflow_api_actions.py -q
& $cmPython $cmBatchChecks --kind frontend --worker W3 -- src/api/workflow.test.js --maxWorkers=1
```

The wrapper's waiting/running messages describe queue state. Retain the actual test output and exit code. If a check times out while waiting for another worker, report the queue condition and retry the same focused check after the active runner finishes. Never bypass the storage guard to speed up a run.
