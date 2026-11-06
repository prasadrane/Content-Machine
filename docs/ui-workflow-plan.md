# Content Machine creator workflow product plan

Updated 2026-11-05
Implementation is underway through the supervised Freebuff checkpoints. Five specialist and five whole-product reviews informed the plan. The latest confirmed changes add Supabase, Google sign-in and an explicit guest demo.

This is the current proposal for future UX work. It supersedes the November 4 demo-led plan; existing implementation/validation documents remain historical evidence. AI expert critique is not a usability study with representative creators. Detailed evidence and decisions are in [the review record](reviews/2026-11-05-workflow/decision-log.md).

## 1. Product purpose and confirmed decisions

Help a technical creator turn an idea and their own perspective into content they can publish. The product succeeds when the creator can find their work, develop a faithful deliverable, knowingly approve it, and obtain it without manual transfers between tools.

The user confirmed these decisions.

- Each creator has a private workspace.
- Hosted private workspaces use Supabase Auth and Postgres with Google sign-in.
- Offer an explicit guest entry seeded with clearly labelled demo content and isolated from private creator workspaces. Guests can edit content and use live AI. Preserve guest work for return visits and offer transfer after Google sign-in.
- Workflow opens to saved ideas and drafts, with a prominent Resume action.
- Own ideas/notes and discovering configured sources receive equal prominence.
- Choose one target platform first; optional adaptations come afterward.
- AI Council review can be explicitly skipped; human approval remains required.
- Finish with copy/download; the creator publishes manually.
- Instagram captions AND Reel scripts are first-release capabilities.
- The initial audience is technical and engineering creators.
- Incorporate four stages into Workflow; remove the standalone Audio destination and place dictation at text intake.
- Remove guide toggles, demo noise and decorative UI emoji; use professional action/topic icons and recognizable platform logos.
- Private workspaces use actual editable and configurable records. Sample content belongs to the labelled guest demo. Operation results and review status reflect actual activity in each mode.
- Preserve the consistent editorial theme. Comments stays retired; historical user data stays preserved.

Proposed design decisions, not additional user facts: three top-level destinations (Workflow, Lessons, Settings); stage labels below; one explicit approval button as consent; one reusable-preferences editor. Validate their wording and discoverability with creators.

## 2. Why the product structure changes

The current navigation follows internal subsystems. A creator instead asks: What can I say? How can I develop it? Do I stand behind this wording? How do I take it to the platform?

| Surface or phase | Why it earns a place | Current limitation, from specialist evidence | Proposed simpler solution |
| --- | --- | --- | --- |
| Workflow landing | Find and resume real work | Oracle startup and in-session state do not provide a saved-item library (N3-N6) | Actual saved ideas/drafts, named Resume and New content; no statistics dashboard |
| Idea | Choose material and an intended point | Discovery-led entry, inconsistent source actions, forced-context prompts and scaffold handoff (I1/I4-I6, D1) | Equal own-material/discovery entry; optional author help and attached sources |
| Draft & review | Develop the actual publishable artifact | Draft creation, source context, polishing and Council advice are fragmented; platform is not consistently carried (D1-D6) | One editor, shared context, platform-aware drafting and optional actionable AI advice |
| Approve | Decide exactly what may be treated as final | Approval can concern an anchor rather than the later rewritten deliverable (E1-E3) | Full exact-artifact preview and one version-bound human decision |
| Export | Obtain the approved artifact | Distribution can rewrite after approval; files or Copy do not prove publishing (E2/E6-E9) | Copy/download unchanged approved content; no generation here |
| Lessons | Avoid repeating the same writing corrections | Rule governance/diff machinery and incomplete edit/failure behavior obscure the benefit (S1-S4) | Optional, small reusable-preferences editor with truthful activation |
| Settings | Control factual author context and sources | Fixed identity, raw injected context and overwrite risks (S5-S9) | Optional factual profile and configured sources; link to the same preference editor |
| Audio | Speaking is an input method | Separate destination adds a transfer without advancing the writing task | Remove the page; field-adjacent dictation and editable transcripts |
| Guest demo | Try the workflow before signing in | Automatic showcase seeding obscures real saved work | Explicit guest entry, labelled editable examples and isolated guest state |

Current-state evidence is source-based, not a new rendered audit. The source cockpit is already collapsed; the proposal is to simplify its remaining controls and relocate reusable configuration, not claim it is wholly expanded.

## 3. One coherent journey

~~~mermaid
flowchart LR
    W["Saved work"] -->|New content| I["1 Idea"]
    W -->|Resume| S["Open item at its saved stage"]
    I --> D["2 Draft & review"]
    D --> R["Optional AI review"]
    R --> D
    D --> A["3 Approve exact version"]
    A --> E["4 Export unchanged content"]
    E --> W
    E --> N["Optional linked adaptation"]
    N --> D
~~~

The landing is outside an active item's four-stage strip. A resumed item opens at its saved state, retaining its platform and format; it never restarts platform selection automatically.

Global navigation: Workflow is primary; Lessons and Settings are supporting destinations. Inside an item show one human title, destination/format, acknowledged save state, All content, and item History. Do not duplicate these in every stage.

Show one active stage, not four former pages stacked vertically. Stages are revisitable states, not a compulsory tour. Gate actual actions on their inputs/approval; visiting a stage is never completion. Use stable private item/stage routes and predictable browser Back/Forward. A Settings or Lessons detour returns to the same item.

## 4. Stage definitions

### Stage 1 — Idea

**Why:** establish what the creator wants to say and the real material available to support it.

**Entry:** New content chooses one destination and supported format in this stage. Platform choice does not become a fifth onboarding stage. Keep it visible and editable before generation.

**Default UI:** two equally prominent choices, Your idea and Discover ideas. Your idea accepts notes or an existing draft in one clear input, with Dictate beside it. Do not require a second mode selector just to paste a draft. Existing content is retained exactly until an author edit or accepted suggestion.

Discovery shows real source title, source/date, available excerpt and Use this idea. Search and optional Filters replace a wall of taxonomy/verdict chips. Merge fresh/previous discovery presentations with the same item action. Scanned material is source history; it becomes saved creator work only through deliberate Save/Use.

Keep Refresh and a compact configured-source summary here. Manage sources opens Settings and returns to this item; adding a source cannot silently replace other sources. Show opt-in feed suggestions as suggestions, not as creator-chosen subscriptions.

**Author context:** one optional point/takeaway field plus attached evidence. Help me develop this reveals optional prompts. Do not demand an interview, profile, personal incident, employer, metric, or an acknowledgment that no personal example exists. Attributed technical commentary is valid.

**Exit:** an owned item with platform/format and real notes, a source, or an existing draft. Source identity, available excerpt, creator notes/experience and interpretation remain distinguishable and survive the handoff.

**Empty/failure:** distinguish no sources, never checked, no new items, no filter matches, partial failure and unavailable service. Keep usable previous results, identify affected sources, and offer one useful next action. Never substitute a generic successful-looking briefing or seeded result.

### Stage 2 — Draft & review

**Why:** turn material into the exact selected-platform deliverable and decide which improvements to accept.

**Default UI:** one working editor. Create draft is useful for notes/source intake; a pasted draft is not regenerated on entry. A compact expandable Context panel exposes the same notes/source record captured in stage 1, not another set of competing fields.

Writing and revision requests receive actual source evidence, creator contribution, platform/format and applicable saved preferences. Title-only context is labeled as such; missing evidence becomes a specific question or omitted claim. General voice files are not a substitute for per-item context.

**Optional AI:** Review draft offers concise feedback tied to a passage and a useful next edit. Keep detailed judge opinions, score basis and processing settings secondary. Remove peak/trophy competition, raw slugs, unsupported performance claims and burstiness/authenticity badges.

One optional wording-suggestion action replaces duplicate Humanize controls. Show current/proposed wording and changes, including deterministic cleanup, before acceptance. Cancel preserves current text; accept creates a recoverable version. Comparison does not verify facts.

**Forward action:** Continue to approval for a current-reviewed deliverable; when proceeding without current AI advice, explicitly offer Skip AI review and continue. No reason field or passing score is required. A failed review offers Retry or a deliberate continue-without-review action; it never silently becomes skipped or successful.

Distinguish not run, pending, completed for this version, earlier-version, failed and explicitly skipped review. A review attaches to the exact text actually scored; later sanitizer/wording changes cannot inherit it. Do not compare raw and normalized scores as the same /10 scale.

**Exit:** complete selected-platform text/structured parts, with proposed edits accepted or declined and an actual current review or explicit decision to proceed without it. All content shaping ends before approval.

### Stage 3 — Approve

**Why:** the creator knowingly authorizes the exact deliverable that will be offered as final.

**Default UI:** the complete readable artifact, platform/format, relevant post boundaries or length checks, honest AI-review state, and expandable source/change context. Use a modest format-aware preview; do not promise an exact platform rendering.

One explicit Approve this version button, with a nearby plain-language consent statement, records the human decision. Do not stack a checkbox, modal and second confirmation for the same consent. Back to edit remains available. This single-action consent design is a recommendation to validate, not a claim of observed comprehension.

Approval binds the authenticated creator, item, immutable version, destination, format and exact artifact payload, including thread parts or script cues. A score or sample history cannot approve it. Editing deliverable content or changing destination/format creates an unapproved version; editing back to identical wording does not revive old consent.

**Exit:** a matching durable approval record and automatic advance to Export. The prior approved snapshot remains identifiable if the creator later edits or adapts it.

### Stage 4 — Export

**Why:** finish with portable content the author can publish manually.

**Default UI:** unchanged approved content, Copy [deliverable], Download, and a short manual-publication instruction. Selectable text remains available. For X, show numbered post boundaries, individual lengths and per-post copy, plus whole-thread download. Offer appropriate plain-text/Markdown downloads without exposing private server file paths.

No model calls, cleanup, shortening, tone changes or format generation occur here. Export retrieves the approved payload under a documented text/encoding contract. If a change is requested, create another unapproved version through Draft & review and Approve.

Clipboard failure must not say Copied. Download initiation must not claim verified disk completion. No file, generated bundle, copy or download event means Published. Completion returns to the saved-work list; keep the artifact accessible.

**Optional continuation:** Adapt content chooses another destination or format and creates a linked unapproved item/version with its own review and approval. Reuse the same workflow; defer branch-tree UI. Failure/cancellation preserves the original approved artifact.

## 5. Platform and icon contract

Platform identity and content format are separate. Use recognizable brand SVG icons plus visible labels, consistent sizing and the shared editorial theme. Use professional outline icons for actions; topic icons are optional when they add recognition. Remove decorative UI emoji without altering creator-authored content.

| Destination or retained capability | Deliverable and release requirement |
| --- | --- |
| LinkedIn | Plain-text post prepared and reviewed/approved before export |
| Instagram | Caption and Reel script as two explicit supported format choices; neither is compulsory when creating the other |
| X | Thread with explicit structured post boundaries and applicable configured limits; total string length alone is insufficient |
| YouTube | Short/long script choices with honest labels and grounded production cues; not rendered video, thumbnail or upload |
| Newsletter | Newsletter draft/Markdown, using a neutral mail icon unless a specific provider is supported |
| Existing generic short-video script | Preserve this capability and its history; define an honest destination/format mapping during adapter discovery rather than relabel it as validated Instagram/TikTok/Shorts support |

Both Instagram adapters are first-release work, not merely icons on the generic video prompt. Scripts retain required production markers, including [Visual Cue], [Camera Zoom] and [Pause], where appropriate. Do not demand benchmark/numeric chapters without supplied evidence.

Use actual supported capabilities, not promises of viral/high-performing output. An icon never implies an account connection or direct publishing.

Internal development may prove LinkedIn first, then Instagram and the retained capability matrix. The two reviewers' proposed narrower public platform release is NOT adopted: no current supported format is silently removed.

## 6. Supporting views

**Lessons owns one reusable-preference collection.** Default to active preferences, pending suggestions only when present, and Add preference. Manual Save and use is explicit human activation. AI-inferred proposals require individual approval; present real duplicate/conflict/limit/failed outcomes, preserving input. Offer Edit and Stop using with history.

Origin is Added by you or a real item/version association. A factual correction remains on its item unless the creator deliberately makes it reusable. Preference changes affect future requests, not saved approved artifacts. Universal grounding/approval requirements remain distinct from optional personal style choices.

**Settings owns optional factual author context and configured discovery sources.** Use ordinary editable fields, Save per section, and unsaved/saved/error feedback. Empty author fields stay empty; remove invented names, experience, employment history and Verified Persona claims. Neutral product defaults are labeled as defaults, not learned facts or personal rules.

Settings links to the same Lessons preference editor; it does not create another writing-rule bank. Simple non-rule defaults such as preferred platform can remain here with explicit labels. Profile completion is not required to write.

Source records support add/edit/enable/disable, attempted-refresh status and useful errors; disabling a source does not destroy previously attached evidence. Refreshing settings cannot overwrite unsaved edits silently.

Defer automated Learn from these edits until actual version-pair provenance and a reliable publishing loop exist. Do not add a required post-export teaching prompt or fifth stage. Existing pending suggestions remain subject to human decisions.

## 7. Shared integrity, privacy and recovery

- **Private means server-enforced ownership.** Hosted creator workspaces use verified Supabase identities and owner checks for content, settings, sources, attachments, review results, history, approvals and exports. Google sign-in is confirmed. Project configuration and live verification remain hosted release gates.
- **Saved means acknowledged durable writes.** Autosave working content independently of AI. Show Saving, Saved with time, or Not saved/Retry from real results. Preferences/settings activate through their deliberate save actions. Failed saves retain exact input.
- **Resume means recovered acknowledged state.** Persist notes, context, versions and actual review/approval associations. Opening another item preserves the first; identical titles cannot collide. Do not advertise recovery across reload/restart/deploy until verified.
- **History is not the content list.** Within an item, open older versions read-only with Compare and Restore as new version. Preserve current text and historical approvals; do not guess an output's source from a peak draft, slug or matching text.
- **Pending work belongs to its requester.** Snapshot owner/item/version/platform/format for AI requests and the originating field/insertion context for transcripts. Late results offer Open/Compare in that context; they cannot replace newer work or another item.
- **Dictation is field-level input.** Provide labeled Dictate/Stop, recording/transcribing/error state, editable transcript and permission-denial recovery. Preserve typed text; if context changed, offer insertion rather than silently appending elsewhere. Leaving releases the microphone. Explain the actual browser/backend processing path; private does not imply fully local transcription.
- **Failures stay failures.** Loading, successful empty, no matches, partial results, unavailable history, save failure and AI failure need distinct recovery. Keep previously loaded useful data when refresh fails. Do not claim AI health or save safety from a generic API Online indicator.
- **Manual recovery remains possible.** Typed text stays selectable; a clearly labeled unapproved draft backup can preserve work after a save failure. It must not acquire final approval, Ready to publish or a publication event.
- **Real records and guest examples have distinct provenance.** Private workspaces start with creator-owned records. Entering guest mode explicitly loads labelled technical examples into isolated guest state. Curated material has visible provenance, optional factual profile fields stay blank, and AI feedback reflects actual operations. Stored output reopens with its recorded lineage and status. Offline fixtures use isolated test storage.
- **Preserve before migrating.** Keep a recoverable copy, make migration repeatable, and quarantine proven synthetic records outside normal creator work. Preserve ambiguous records and retired Comments history. Establish ownership explicitly; never guess an owner or approval. Unmatched legacy artifacts say source/approval association unavailable.
- **Seeds cannot overwrite edits.** Runtime profile, preferences and source records belong to the creator. Product default/knowledge updates cannot reset them on refresh, restart or deployment.
- **Small components, shared contracts.** Keep API calls in ui/src/api, register destinations through the app registry, retain cm-* tokens, file-size constraints and existing request/microphone cleanup. No new state library, queue, event bus or background-job promise without a demonstrated need.

## 8. Accessibility and validation acceptance

These are proposed acceptance scenarios, not completed checks of the redesign.

1. Empty private creator: start from notes OR an existing technical draft without a profile/source setup; explicit AI skip -> one human approval -> matching copy/download. No fabricated identity, score or anecdote appears.
2. Discovery: retain actual URL/excerpt and author interpretation through generation, suggested-change comparison, approval and export. No personal example/metric is needed. Partial source failure leaves successful items usable.
3. Instagram: independently create a caption and a Reel script, with actual corresponding adapters and script cues; approve each exact artifact. A caption never receives a generic script response.
4. Retained formats: run the LinkedIn/X/YouTube/newsletter/generic-script matrix, checking real structure and configured constraints before approval. Export performs zero generation/rewriting requests.
5. Consent/version: edit one character after approval, restore matching wording, change format, or restore an older version; none borrows consent. Historical approved text remains inspectable/exportable by its owner.
6. Asynchrony/voice: record or review A, edit/switch to B, then resolve or fail A; no cross-item insertion, overwrite, advancement or approval. Denied microphone permission leaves typing usable.
7. Save/return: save A/B, visit Settings/Lessons, restart/redeploy, then Resume each acknowledged item. Save failures retain exact text and show recovery; history failure never looks like a successful empty library.
8. Privacy: unauthenticated and creator-B requests cannot read/write creator-A data, direct item routes, histories, review results, attachments or exports. Session changes cannot insert A's late result into B's account.
9. Settings/lessons: change factual profile/source/preference, fail or conflict a save, stop a preference, refresh/restart and migrate twice. No overwrite, fake activation, duplicate migration, source-list replacement or Comments-history loss.
10. Handoff: deny clipboard access or fail download initiation; keep selectable approved text and an alternate action. Report only actual Copy/Download-start events, never publication.
11. Navigation/accessibility: complete both entries and the manual finish by keyboard and a screen reader; preserve focus and reading order through settings/history/comparison. Verify visible focus, named controls, meaningful announcements, contrast, reduced motion, forced colors, 200% text resize and 320 CSS-pixel reflow with the phone keyboard.
12. Adaptation: create another format/destination from approved work, then cancel/fail/edit it; the original remains approved and exportable, while the adaptation needs independent approval.
13. Guest entry opens labelled, editable ideas and drafts in its own state and supports live AI requests. Review and approval records arise from actual guest actions. Each guest uses a distinct Supabase anonymous identity verified by the backend. Guest work survives a return visit, and Google sign-in offers an explicit transfer into the creator's workspace with input and provenance preserved. Cross-workspace access remains owner-checked throughout the transfer.

During implementation use meaningful failing behavioral tests first, offline frontend/backend regression suites and production build, followed by rendered browser/error/accessibility checks. Unit tests and source inspection do not prove platform quality, creator comprehension or accessibility.

Run a small formative study with representative technical creators after a prototype exists: find Resume, develop own/source material, explain what was approved, export the expected artifact and recover from a failure. Record confusion, wrong turns and task completion as a baseline; no numerical improvement or research result is claimed now.

## 9. Delivery sequence and parallel ownership

The supervised implementation packets and prompt/review/repair procedure are available in the [execution runbook](implementation/workflow-runbook.md).

| Work package | Why / concrete exit | Ownership and dependency |
| --- | --- | --- |
| 0. Contract and capability discovery | One agreed owner/item/version/context/artifact/review/approval contract; retained-format inventory; migration and hosted-access/storage choices documented | Foundation owner centralizes schemas, migrations, storage and API contracts; do before parallel feature writes |
| 1. Complete internal slice | Existing LinkedIn draft -> durable save/list/Resume -> explicit AI skip -> exact human approval -> real download; no fake records | Local-first integration checkpoint, not an advertised limited-platform release |
| 2A. Shell and intake | Saved list/routes, equal starts, real source discovery, simple source context and safe dictation | Shell/intake owner; owns app registry and shared icon/platform metadata, coordinates shared edits |
| 2B. Writing and formats | One context-aware editor, optional AI/revisions, all retained adapters plus Instagram caption/Reel | Editorial owner; owns drafting/review/format modules, consumes foundation APIs |
| 2C. Approval and export | Exact artifact preview/consent, immutable Copy/Download, linked adaptation and version history | Approval/export owner; consumes version APIs and shared platform metadata |
| 2D. Settings and Lessons | Real optional author/source editing, single preferences editor, truthful saves/conflicts | Settings owner; no separate rule bank or auto-learning prerequisite |
| 3. Whole-product integration | All acceptance scenarios, migration rehearsal, format parity, offline suites/build and rendered journey/accessibility checks | Integration owner checks complete journeys; shared/API fixes go through named owners |
| 4. Private hosted release | Authenticated ownership and durable restart/deploy recovery verified; no public exposure of creator data | Hosting/storage decision and authorization separate from this planning task; no deployment implied |

Run independent workstreams against frozen interfaces, scheduling within available worker slots. Workers are not alone and must preserve others' changes. Only named owners edit shared schema/storage/API, shell registry and style/icon metadata; feature work does not independently redefine them.

## 10. Deliberate deferrals and decision status

Defer automatic publishing/account connections, rendered image/video production, team/public workspaces, statistics dashboards, bulk bundles, branch-tree editors, advanced taxonomy/ranking controls, score competition, automatic factual verification, offline sync and inferred-lesson extraction.

Do not defer private ownership, acknowledged saves, grounded author/source context, truthful failures, exact approval/export, required Instagram formats or accessible primary journeys into cosmetic follow-up work.

All six questions asked during this review are answered. Stage wording, consent comprehension and detailed format mapping remain design hypotheses to validate; hosting vendors remain implementation discovery. No additional creator question currently blocks the proposed journey.

Ten reports were completed: five owned-view critiques, then five independent whole-product critiques reading all five specialists. The coordinator reconciled their recommendations and retained disagreements in the decision record rather than treating every suggestion as accepted.

Verification boundary: planning documents changed only. No redesigned UI, live generation, browser audit, user study, real-data migration, account access, commit/push or deployment was performed for this task. Any repository baseline checks recorded in the decision log do not validate this unimplemented design.
