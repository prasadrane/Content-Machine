# Proposed guest-to-creator transfer contract

Status: behavioral contract with an implemented offline SQLite service packet described below. Hosted application integration and complete H06 acceptance remain open. The older unavailable preview remains unchanged; integrating the new copy flow requires its explicit consent UI, reviewed schema and durable persistence verification. No production migration is authorized by this document.

## Implemented offline service packet

The user subsequently authorized implementation of the remaining nonbrowser work. `workflow/guest_transfer.py` and `guest_transfer_storage.py` now implement the unapproved-copy policy below for SQLite; this does not establish hosted durability or a complete native-history transfer. The original legacy `guests.preview_transfer` remains a separate unavailable preview. Integration must use the new explicitly named copy functions and accurately describe their behavior.

Integration interface:

- Install `TRANSFER_MIGRATION_STATEMENTS` from `guest_transfer_storage` through the reviewed migration seam, or call `migrate_guest_transfer(conn)` explicitly on disposable/backed-up local data.
- `preview_guest_copy(conn, guest_proof, creator_proof, verifier)` verifies both identities, refuses pending operations and returns the complete source fingerprint/item count and `requires_new_approval=True`.
- `copy_guest_workspace(conn, guest_proof, creator_proof, verifier, consent=True, request_id=..., source_fingerprint=...)` atomically creates unapproved current-work copies, immutable original-history receipt and typed item/context-source mappings. Idle-connection success follows commit; an HTTP caller owning an outer transaction must commit before returning success.
- `get_transfer_receipt(conn, verified_creator_principal, transfer_id)` returns the inert archive only to the receiving creator and verifies its source fingerprint.
- `transferred_example_labels(conn, principal)` supplies stored copy provenance for normal owned-item summaries; UI integration must preserve this label.

The service archives all 13 native owner-scoped workflow tables and the optional `workflow_legacy_imports` provenance table when installed. Future owner-scoped workflow tables fail closed until supported. Limits are 1,000 source working items and 8 MB canonical archive data. No source table, historical JSON, authorship or approval is rewritten. Target items begin at revision 1 with no approval, current review, operation or parent-version FK. Archived source profile/preferences remain inert; creator settings remain untouched. Replays of the completed generation return identical copy IDs; a subsequent changed source generation is refused rather than silently treated as delta import.

Offline regressions cover complete archive/exact artifacts, source and creator-settings preservation, proof/consent checks, source drift, pending work, retry/concurrent duplicate behavior, immutable receipt ownership, typed context IDs with unchanged literal text, staged copy/deferred commit rollback and unknown-history rejection. Final test evidence is reported in the parent integration handoff; no actual project credentials or live provider calls are used by this packet. Parent integration still owns routes, browser consent flow, central migration and real Postgres verification.

## Result presented to the creator

Transfer creates new, unapproved working copies in the authenticated creator's workspace. It leaves the guest workspace unchanged and recoverable. The UI must say **Copy guest work into your account** and explain that copied drafts require approval again. It must not claim that the guest's historical approvals or AI operations become approvals or operations performed by the receiving creator.

Every accepted copy also creates an immutable transfer receipt containing the exact source history and provenance captured at the transfer boundary. The creator can inspect that archived history separately from the new working copy's ordinary version history. Original identifiers, authorship, timestamps, approval associations, artifact bytes, model metadata and score basis remain original within the archive.

This interpretation resolves content transfer without rewriting historical consent. It does **not** make archived source versions editable or directly exportable as approved target versions. If the product requires all history to appear as native target-owned versions and approvals, the alternative model below must be selected instead before implementation.

## Preconditions and authority

- A trusted server verifies both credentials independently for signature, configured issuer, audience, expiry, authenticated role and canonical UUID subject.
- The source proof must carry the strict signed top-level `is_anonymous=true`; the destination proof must carry strict `is_anonymous=false`. Editable metadata and browser owner IDs are never authority.
- Source and destination subjects must be distinct. Same-subject Supabase identity upgrade is a separate lifecycle and must not be relabelled as dual-owner transfer.
- Explicit consent applies to the source, destination and reviewed source snapshot. A preview or sign-in alone never triggers copying.
- The source has no pending AI operations. Reject with a typed actionable conflict; require completion or an explicit reviewed abandon action before retrying. Do not abandon or restart provider calls automatically.
- Validate eligibility again within the transaction. Acquire owner/source locks and compare the reviewed snapshot fingerprint so concurrent edits, new items or pending operations invalidate stale consent.
- The target has no required overwrite operation. Existing creator items and settings remain unchanged.

Use one shared backend transaction across snapshot validation, target copies, immutable receipt and success response. A hosted implementation must use the durable Postgres transaction boundary; local SQLite tests do not establish cross-instance hosted behavior. Success is returned only after commit.

## Snapshot and copied content

The transfer boundary captures the complete owned source item graph: working items; immutable versions; approvals; reviews; operations; immutable operation inputs; example provenance; and their exact ownership/reference associations. Retain request and response records needed to explain history as inert archive data, never as target idempotency authority. Capture source profile, discovery-source records and governed preference history as provenance too.

New target working items preserve title, destination, format, exact current artifact segment order and bytes, and current context text/source evidence. Each receives a new item identifier and a normal initial target revision. It has no active approval, no current AI review, and no copied pending/terminal target operation. Its stage is `draft_review` when draft material exists, otherwise `idea`. All final-format validity and size checks remain enforced at normal later approval; no transfer invents valid or approved status.

Historical approval data remains only in the source archive. Do not change `approved_by`, `created_by`, source owner IDs, timestamps, operation results, stored request digests or old score-basis bindings. Copying a receipt is not a new claim that the target creator authored, reviewed or approved the historical content.

Context source excerpts and titles remain exact evidence. New working copies must not retain live configuration references that point into another owner's settings. Define fresh target context reference IDs and map them explicitly to archived source references. The working copy's `preference_snapshot_id` is unset unless a new target-owned preference snapshot is explicitly constructed by a separately reviewed operation. Parent-version lineage points to the transfer receipt/mapping, not to an inaccessible source-owned version FK.

## Settings and examples

Archive source profile, feeds, preferences and preference events in the immutable receipt. Do not replace or merge the creator's profile, automatically enable copied feeds, or activate guest preferences. A later explicit settings import can offer a reviewed conflict preview and preserve the existing governance cap and approval gate. Global legacy-origin uniqueness must not be bypassed by rewriting origins.

Preserve guest-example provenance on copied items as transfer lineage. They must retain a visible source-example label even after edits; title matching never infers provenance. Do not register copied items as newly seeded target guest examples or let a target guest-bootstrap call overwrite them.

## Idempotency and concurrent requests

The transfer request contains an opaque request key and the consented source snapshot fingerprint. Its canonical digest includes the operation, verified source subject, verified destination subject, requested copy policy/schema version and snapshot fingerprint. Proof tokens themselves are never stored or included in fingerprints.

Store one immutable completed receipt and response under `(source_subject, destination_subject, request_key)`. Replaying the identical request returns the same target IDs and receipt without copying again. Reusing its key with another source fingerprint or policy returns an idempotency conflict. A different request key for the same captured source generation must resolve to the same completed receipt, or be rejected as already transferred; it must not silently duplicate target work. Copying subsequent guest edits is a separate explicit delta-transfer feature, not a consequence of retry.

Lock and unique-constraint behavior must cover two simultaneous requests across application instances. A rolled-back transaction creates no receipt, mapping, target item or success marker and can be retried safely. Source changes after a completed transfer never mutate the archived receipt or existing target copies.

## Required schema and implementation packets

1. Add a versioned `workflow_guest_transfers` receipt/run table with source and destination subjects, policy/schema version, source fingerprint, request key/digest, capture/commit timestamps, exact inert source archive payload, archive hash and canonical success response. Store no credentials. Add immutable update/delete protection and appropriate owner access/retention policies. Decide archive size/retention limits before migration.
2. Add `workflow_guest_transfer_items` mappings with transfer ID, source item ID, target item ID and source current-version identity where known. Composite owner-scoped FKs must bind target items to the verified destination. Add a typed identity-mapping table or typed mapping columns for archived versions, approvals, operations, reviews, sources, preferences and context-reference IDs. Archives retain source IDs; mappings explain relationships without rewriting archived payloads.
3. Require uniqueness for the retry tuple, captured source generation and target mapping. Specify locking order, committed-state representation and immutable receipt hashing for both SQLite and Postgres. Map source/destination receipt access explicitly; source retention and creator-account deletion behavior require a deliberate policy.
4. Implement typed source-graph extraction and validation. Every supported stored JSON shape must have a named decoder and reference checks. Do not use recursive string replacement or infer references from matching text. Reject unsupported schema versions and unresolved/cross-owner references before any target write.
5. Implement one atomic copy service, then explicit preview/confirm routes and browser client/UI. Keep durable adapter injection and normal auth/storage fail-closed behavior. Do not mount a SQLite-only implementation as hosted persistence.

## Required tests before acceptance

- Valid anonymous-to-creator proofs; missing, forged, expired, wrong-issuer/audience/role, metadata-only/nonboolean anonymity, reversed identities and equal subjects rejected before storage mutation.
- Explicit consent, stable source fingerprint, source edits/new records between preview/commit, missing source rows, pending operations and late abandoned-operation results handled without inferred completion.
- Exact Unicode, whitespace, thread boundaries, scripts, excerpts, unknown historical approval/lineage and complete archived graph associations preserved. Source archive hash recomputes; malformed/unrecognized references fail closed.
- Target copies start unapproved with no current review or AI operation. Historical authorship and approval fields remain original only in the inert archive. Target final export remains unavailable until a fresh explicit target approval.
- Existing creator items/profile/feeds/preferences unchanged. Guest source graph remains unchanged. Example labels persist through copy/edit. Settings archive cannot silently activate preferences or evade caps.
- Same-key retry and changed-key/body conflict, already-copied generation, concurrent duplicates, deterministic mapping replay and committed acknowledgements. Force real deferred-commit failure and fail each copy stage; assert no partial target graph or receipt and successful retry.
- Owner A/B denial for source archive, target copies and receipt downloads; archived idempotency records cannot replay live target writes. No credentials in receipt, logs, API responses or provider inputs.
- Repeat migration on populated isolated data; rollback/interruption recovery; restore original source plus immutable receipt and exact target-copy mappings from backup. Repeat against disposable real Postgres including RLS, concurrency and restart boundaries before hosted acceptance.

## Alternative if complete native history is mandatory

Use immutable shared content/version identity with distinct ownership/access grants and explicit transfer lineage, or extend native rows with immutable origin owner/author/approval identity separate from current access owner. That requires a schema-level ownership redesign and a review of every read, write, history, operation, approval and export path. It must specify which historical approvals remain export authority after ownership changes and who may revoke them.

Do not simulate that model by copying rows and substituting the destination owner in nested JSON or authorship fields. If complete native history is a non-negotiable requirement, this proposed working-copy-plus-receipt policy is insufficient and H06 remains blocked on the alternative design decision.
