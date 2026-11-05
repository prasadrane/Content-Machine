# Content Machine workflow contract

Repair 2 (`C01_R2_20261105`), preserving the repair-1 decisions and correcting this contract only. Normative inputs: `contract-context/runbook-contract.txt`, `product-plan.md`, `storage-db.py`, `storage-paths.py`, `shared-flow.js`. Documentation only: no application code and no fixture or snapshot changed. These decisions are authoritative for the local implementation; only the hosted items in §10 remain open.
IDs are opaque server TEXT; timestamps are ISO-8601 UTC TEXT `YYYY-MM-DDTHH:MM:SS.sssZ`; canonical JSON is UTF-8 with sorted keys and compact separators, preserving every string character.

## 1. Records

Working data is nested on the item: Context and Artifact have no independent rows or IDs.

| Record | Fields with types |
| --- | --- |
| Principal | `owner_id` TEXT; `mode` TEXT (`hosted_verified`\|`trusted_local`); `display_name` TEXT? |
| ContentItem | `item_id`,`owner_id`,`title`,`destination`,`format` TEXT; `stage` TEXT (`idea`\|`draft_review`\|`approve`\|`export`); `working_revision` INTEGER; `context` Context; `artifact` Artifact; `parent_version_id`,`active_approval_id` TEXT?; `created_at`,`updated_at` TEXT |
| Context | `notes` TEXT; `experience`,`interpretation` TEXT?; `sources` `[{source_id,url,title,excerpt,fetched_at}]`; `preference_snapshot_id` TEXT? |
| Artifact | `segments` `list[str]` in order; empty is valid while idea/editing |
| ContentVersion (immutable) | `version_id`,`item_id`,`owner_id` TEXT; `revision` positive INTEGER; `context` Context (nested); `artifact` Artifact (nested); `destination`,`format`,`artifact_digest` TEXT; `purpose` TEXT (`review`\|`skip_review`\|`approval`\|`restore`\|`adaptation`); `created_by`,`created_at` TEXT; unique(`item_id`,`revision`); no UPDATE or DELETE |
| Operation (server-created) | `operation_id`,`owner_id`,`item_id` TEXT; `kind` TEXT (`generate`\|`review`); `input_version_id` TEXT; `context_snapshot` Context (nested); `state` TEXT (`pending`\|`completed`\|`failed`); `request_id` TEXT; `result` JSON?; `error` JSON?; `started_at`,`finished_at` TEXT? |
| Review | `review_id`,`owner_id`,`item_id`,`input_version_id`,`request_id` TEXT; `state` TEXT (`pending`\|`completed`\|`failed`\|`skipped`); `actions` JSON; `score_basis` JSON?; `proposals` JSON `[{segment,current,proposed}]`; `model_config` TEXT?; `started_at`,`finished_at` TEXT? |
| Approval (immutable) | `approval_id`,`owner_id`,`item_id`,`version_id`,`artifact_digest`,`destination`,`format`,`approved_by`,`approved_at` TEXT |
| Idempotency | `owner_id`,`request_id` TEXT; `method`,`resource_path`,`request_digest` TEXT; `response_status` INTEGER; `response_body` JSON; `created_at` TEXT; unique(`owner_id`,`request_id`) |

A ContentVersion freezes the complete context, artifact, destination and format at one revision. An Operation belongs to its frozen input version, is created by the server, and is distinct from Review: operations carry the request/result envelope, while Review carries review state, score basis and wording proposals. Approval rows are immutable. An item edit clears only `ContentItem.active_approval_id`, so a historical owned version with a matching historical approval stays exportable, while a restored or new revision never borrows it.

## 2. Exact export, filename and canonical digest

- One-segment artifact: the export body is exactly that string encoded UTF-8 with no BOM. No newline, separator or terminator is appended, and a newline or trailing whitespace already stored in the last segment is preserved exactly; no newline normalization occurs.
- Thread: the exact stored segments joined by two LF characters between segments (`\n\n`), with nothing appended after the last segment, whose stored trailing whitespace is preserved.
- Download name: `<slug>-r<revision>.txt` where `<slug>` is a safe ASCII title slug of at most 80 characters, lowercased to `[a-z0-9-]`, with non-alphanumerics collapsed to `-` and leading/trailing `-` stripped. Path separators, control characters and header-invalid characters (`"`, `\`, CR, LF, `:`, `;`) are removed. A blank slug, or a Windows-reserved base name (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`), uses `content-<safe opaque item id>`, where the item id is reduced to ASCII alphanumerics and `-`; a raw or unsafe ID is never included. The suffix is always `-r<revision>.txt`.
- Response is `text/plain; charset=utf-8` with `X-Artifact-Digest` and that `Content-Disposition`. `?as=json` returns `{"version_id","destination","format","artifact_digest","segments"}` for per-post copy and whole-thread download.
- `artifact_digest` = `"sha256:"` + hex SHA-256 of the canonical UTF-8 JSON of `{destination, format, segments}`: sorted keys, compact separators, every character preserved, so equal text with different segment boundaries digests differently.

## 3. Snapshots, CAS and idempotency

- Every mutating POST and PATCH, including create, save, generate, review, skip-review, approve, restore and adapt, requires an `Idempotency-Key` header; omitting it is a schema 422.
- `POST /items/{id}/generate`, `/review`, `/skip-review` and `/approve` take `expected_revision` and `Idempotency-Key`. In one transaction the server freezes the acknowledged current revision or reuses the existing version for unique(`item_id`,`revision`); the browser never invents a `version_id`. Responses carry the actual `version_id`, operation, review or approval, so each operation record has a real input version.
- `approve` checks the acknowledged `artifact_digest` and `consent`. Missing `expected_revision`, `artifact_digest` or `consent` is schema 422; `consent: false` is an explicit 409 `approval_conflict`; a stale revision or changed digest is 409; a blank or malformed final artifact is 422. No approval is written unless every check passes.
- CAS compare-and-set: a mismatch returns 409 with the acknowledged `working_revision`, `stage`, `updated_at` and `active_approval_id`, and writes nothing; the client keeps its input.
- Content, destination, format or context edits increment `working_revision`, replace artifact/context, clear `active_approval_id`, and return the item to `draft_review` unless the caller states a stage.
- A stage-only PATCH still requires `expected_revision` and performs the CAS check, but changes no content revision, artifact, context or approval.
- Navigation metadata (list, open, clearing an approval) never bumps `working_revision` and never creates a version, review or approval.
- `restore` takes an owned `version_id` plus `expected_revision` and writes a new revision and version with `parent_version_id`; the restored revision needs its own approval.
- `adapt` takes an owned approved immutable `source_version_id` plus target `destination`/`format`; it creates a separate unapproved item whose parent is that version and whose artifact may start empty. The source item is never mutated.
- Idempotency: `Idempotency-Key` maps to `request_id`, unique per owner. `request_digest` covers the concrete HTTP method, concrete resource path and canonical body, so a changed resource or body under one key is a 409. An identical retry replays the recorded status and body.

## 4. Ownership and HTTP errors

- The Principal is resolved once per request by the deployment adapter or explicit trusted-local mode, never from a body, query or client header. Every object read and write filters `owner_id`; child reads re-check it. Missing and cross-owner objects both return 404.
- Errors match the existing `fetchJson`/`ApiError` contract: a human-readable `detail` string and a top-level `code`, plus the acknowledged item fields on conflicts.
- Statuses: 422 missing or invalid request/schema fields, including a missing `Idempotency-Key` and missing required approval fields; 401 unauthenticated; 404 missing or cross-owner; 409 stale revision, idempotency, digest, `approval_conflict` for `consent:false`, or `approval_required` on export without a matching approval; actionable 502 provider failure and 503 capability failure. Existing clients keep working.

## 5. `/api/workflow` endpoints

Every mutating POST/PATCH below requires `Idempotency-Key`; omission is 422.

```text
POST /api/workflow/items                         create          GET  /api/workflow/items                  saved list / Resume
GET|PATCH /api/workflow/items/{id}               read | save CAS  GET  /api/workflow/capabilities
POST /api/workflow/items/{id}/generate           writing         POST /api/workflow/items/{id}/review
POST /api/workflow/items/{id}/skip-review                        POST /api/workflow/items/{id}/approve
GET  /api/workflow/items/{id}/versions           history         GET  /api/workflow/items/{id}/exports/{version_id}
POST /api/workflow/items/{id}/restore                            POST /api/workflow/items/{id}/adapt
```

- `POST /items` `{"title":"Indexing tradeoffs","destination":"linkedin","format":"linkedin_post"}` -> 201 `{"item":{"item_id":"itm_01","working_revision":1,"stage":"idea","active_approval_id":null,"artifact":{"segments":[]},"context":{"notes":""}}}`. Empty items, context and segments are allowed; no source, profile, anecdote or metric is required.
- `GET /items` -> `{"items":[{"item_id":"itm_01","title":"Indexing tradeoffs","destination":"linkedin","format":"linkedin_post","stage":"draft_review","working_revision":2,"updated_at":"2026-11-05T09:12:00.000Z","active_approval_id":null}]}`, ordered by `updated_at` desc; this list is the saved-work list and its Resume target is the stored stage/destination/format.
- `GET /items/{id}` -> `{"item": ContentItem, "review": Review?, "approval": Approval?}` using the §1 field schema.
- `PATCH /items/{id}` `{"expected_revision":1,"artifact":{"segments":["Exact text."]}}` -> 200 `{"item":{"working_revision":2,"stage":"draft_review","active_approval_id":null}}`. The stage-only form takes `{"expected_revision":1,"stage":"approve"}` and leaves content data unchanged.
- `POST /items/{id}/generate` `{"expected_revision":2}` -> 200 `{"operation":{"operation_id":"op_01","owner_id":"own_01","item_id":"itm_01","kind":"generate","input_version_id":"ver_02","context_snapshot":{"notes":"Indexing cost"},"state":"completed","request_id":"req_01","result":{"segments":["Draft text."]},"error":null,"started_at":"...","finished_at":"..."}}`. Generation output is a proposal; applying it is an ordinary save, so it never gains review or approval currency.
- `POST /items/{id}/review` `{"expected_revision":2}` -> 200 `{"operation":{"operation_id":"op_02","owner_id":"own_01","item_id":"itm_01","kind":"review","input_version_id":"ver_02","context_snapshot":{"notes":"Indexing cost"},"state":"completed","request_id":"req_02","result":null,"error":null,"started_at":"...","finished_at":"..."},"review":{"review_id":"rev_01","input_version_id":"ver_02","state":"completed","score_basis":{"rubric":"council","judge_slot":"judge_1","dimensions":[{"name":"clarity","raw":7.5,"z":0.6}]},"proposals":[{"segment":0,"current":"Exact text.","proposed":"Exact text"}]}}`.
- `POST /items/{id}/skip-review` `{"expected_revision":2}` -> 200 `{"review":{"review_id":"rev_02","input_version_id":"ver_02","state":"skipped","score_basis":null},"item":{"stage":"approve","active_approval_id":null}}`.
- `POST /items/{id}/approve` `{"expected_revision":2,"artifact_digest":"sha256:...","consent":true}` -> 200 `{"approval":{"approval_id":"apr_01","owner_id":"own_01","item_id":"itm_01","version_id":"ver_02","artifact_digest":"sha256:...","destination":"linkedin","format":"linkedin_post","approved_at":"..."},"item":{"stage":"export","active_approval_id":"apr_01","working_revision":2}}`. A missing field is 422 and `consent:false` is 409 `approval_conflict`; approval requires nonblank required segments for a supported final artifact, otherwise 422.
- `GET /items/{id}/versions` -> `{"versions":[{"version_id":"ver_02","revision":2,"purpose":"review","artifact_digest":"sha256:...","destination":"linkedin","format":"linkedin_post","created_at":"..."}],"approvals":[{"approval_id":"apr_01","version_id":"ver_02","status":"historical","approved_at":"..."}]}`; `status` is `active` only for the item's `active_approval_id`.
- `GET /items/{id}/exports/{version_id}` -> the exact §2 body for any owned version with a matching historical approval, even after the working item changed; otherwise 409 `approval_required`. No model call, cleanup or rewrite.
- `POST /items/{id}/restore` `{"expected_revision":3,"version_id":"ver_02"}` -> 200 `{"item":{"working_revision":4,"stage":"draft_review","active_approval_id":null,"parent_version_id":"ver_02"},"version":{"version_id":"ver_05","revision":4,"purpose":"restore"}}`.
- `POST /items/{id}/adapt` `{"source_version_id":"ver_02","destination":"instagram","format":"instagram_caption"}` -> 201 `{"item":{"item_id":"itm_02","parent_version_id":"ver_02","working_revision":1,"stage":"draft_review","active_approval_id":null,"artifact":{"segments":[]}}}`.
- `GET /capabilities` -> `{"principal":{"owner_id":"own_01","mode":"trusted_local"},"pairs":[{"destination":"instagram","format":"instagram_caption","can_edit":true,"can_generate":false,"can_approve":true,"limits":{"max_chars":{"value":2200,"source":"configured_adapter","measurement":"unicode_code_points"}}},{"destination":"x","format":"x_thread","can_edit":true,"can_generate":true,"can_approve":true,"limits":{"max_chars_per_segment":{"value":280,"source":"configured_adapter","measurement":"unicode_code_points"}}}]}`.

## 6. Eight-step revision example

| Step | Action | Result |
| --- | --- | --- |
| 1 | Create item A | revision 1, stage `idea` |
| 2 | Save changed text, `expected_revision` 1, key K1 | revision 2, no active approval |
| 3 | Review or explicit skip at `expected_revision` 2 | server freezes V2; review bound to V2 |
| 4 | Approve at `expected_revision` 2 with V2's digest and consent | approval A2, stage `export` |
| 5 | Export V2 | exact stored segments, no model request |
| 6 | Save a one-space edit at `expected_revision` 2 | revision 3, `active_approval_id` cleared, A2 and V2 retained and still exportable |
| 7 | Restore V2 | revision 4 as a new version; A2 stays historical; revision 4 needs its own approval |
| 8 | Retry K1 with its original payload | recorded result replayed; changed payload or path for K1 is 409 |

## 7. Review semantics

- Workflow advice is one pass on the submitted saved snapshot. The Review binds `input_version_id`; it never applies to a later revision.
- Changed wording is a proposal: `proposals` keep `current` and `proposed` text per segment, are outside the scored input, and are never applied by the review. Accepting one is a save that invalidates the working item's review currency and active approval.
- Raw score scale and z-score normalization stay distinct. `score_basis` records the existing Council rubric and judge slots; normalized values are not bounded and are never labelled /10 or rescaled on read.
- States stay distinct: pending, completed for this version, failed, explicitly skipped, and earlier-version for a superseded input. A failed review never becomes skipped or successful. Approval never requires a score.

## 8. Capabilities, formats and entry parity

- `can_edit`, `can_generate` and `can_approve` are per destination/format pair. An unimplemented generation adapter reports `can_generate:false`, never a fabricated ready state. Structural approval readiness is independent of optional generation and review.
- Platform length rules come from the configured adapter with their measurement and source metadata; no account-specific limit is stated as fact.
- Canonical pairs and legacy aliases: `linkedin`+`linkedin_post` (legacy `linkedin`); `x`+`x_thread` (legacy `x_thread`); `youtube`+`youtube_short_script`/`youtube_long_script` (legacy `video_script_long` -> `youtube_long_script`); `instagram`+`instagram_caption`/`instagram_reel_script`; `newsletter`+`newsletter_draft` (legacy `newsletter`); `generic_video`+`generic_short_video_script` (legacy `video_script_short`, and `video_script` when the destination is unknown). Known destination metadata may select a more precise mapping; a mapping is never guessed. All retained capabilities and their history stay.
- Your idea and Discover ideas start equally: either own notes/draft or a discovered source with real URL/excerpt, with no profile or anecdote required. Instagram caption and Reel script are independent formats with their own artifacts and approvals; a caption request never returns a script. Script formats keep `[Visual Cue]`, `[Camera Zoom]` and `[Pause]` cues.

## 9. Module ownership and compatibility

- Backend workflow modules: `schemas.py`, `migrations.py`, `access.py`, `items.py`, `versions.py`, `approvals.py`, `history.py`, `routes.py`, `action_routes.py`, `format_registry.py`, with later scoped context, settings, writing and adapter packets. No second architecture, framework, queue or background-job promise is introduced.
- Frontend: `ui/src/api/workflow.js`, `ui/src/app/useWorkflowSession.js`, `ui/src/components/workflow/` and `ui/src/lib/platforms.js` for identity, icon and label metadata.
- Existing `useSharedFlow` callers keep their current local contracts until their explicit retirement or migration packet; its synchronous helper is not retrofitted into the new server approval API.
- Existing local/CLI data and callers stay readable, and repository seeds cannot overwrite new creator-owned settings. There is no process-global home or environment switching per request, and no legacy ownership or approval is guessed.

## 10. Hosted-only open decisions

1. Authentication provider, session transport and credentials for hosted verification (local trusted mode needs none).
2. Durable deployment and storage choice, including backup, repeatable migration and cross-instance concurrency.
3. Ownership mapping for legacy migrated records, since existing rows carry no owner and no approval may be invented.

Output path: `contracts/workflow-contract.md`
