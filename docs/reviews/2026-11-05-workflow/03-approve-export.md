# Approval and export review

Date: 2026-11-05. Scope: current approval/Distribution and proposed Workflow stages 3/4.
This is an AI expert critique of live source, not a rendered-browser audit or user study.
Confirmed requirements: private creator workspace; one platform first; optional adaptations; copy/download for manual publishing; AI Council may be skipped, human approval may not.
Recommendation: retain two compact stages because deciding what may leave the app and taking it out are distinct jobs. Stage 4 must become an export surface; all writing ends before stage 3.
Evidence method: codebase-memory Tier 2 discovery, architecture and exact-path coverage; generation 2026-11-05T15:39:23Z. All checked paths were `metadata_changed`; PlatformConfigModal:100 and DistributeHistoryDrawer:57 also had partial parses. Material claims below use direct live-source fallback.

## Findings

### E1 — Simplify: make Approve and Distribute one clear handoff
Why: creators need to inspect a finished platform deliverable, then obtain it; another writing workbench after sign-off defeats the meaning of approval.
Current evidence: ApprovalGate approves an anchor (`ui/src/components/approval/ApprovalGate.jsx:15-44`); Distribute edits it, selects formats and generates another bundle (`ui/src/components/distribute/DistributeTab.jsx:120-155`).
Proposed interaction: stage 3 shows the exact selected-platform content and “Approve this version”; stage 4 shows that same immutable version with copy/download. Approval advances directly; no second approval of the unchanged artifact.
How to validate: entering stage 4 produces no model request and preserves every character approved at stage 3. Moving back and forward preserves the approved snapshot.

### E2 — Move: finish platform writing and polish before approval
Why: formatting can alter claims, voice and meaning; it belongs to development, even when called polish or adaptation.
Current evidence: Humanize defaults on (`ui/src/components/distribute/DistributeTab.jsx:24-26`); LinkedIn generation rewrites the anchor and can then humanize it (`content_machine/distribution/engine.py:149-166`). Output Copy has no deliverable approval check (`ui/src/components/distribute/OutputPreviews.jsx:49-85`).
Proposed interaction: prepare the chosen platform/format in stage 2; show proposed edits and accept them explicitly. Remove Humanize, tone chips and Generate Bundle from stage 4. Any later content change creates an unapproved version and returns to stage 3 after editing.
How to validate: an approved LinkedIn post exports unchanged; requesting a rewrite cannot replace its approved snapshot. Editing back to identical words does not silently restore approval.

### E3 — Keep: exact-version sign-off, with an honest review status
Why: human judgment is the final authority; an editorial score is neither fact verification nor a required permission to approve.
Current evidence: approval checks item, version, text and slug (`ui/src/components/distribute/useDistributionSession.js:18-26`); the dialog allows a non-pass override (`ui/src/components/approval/ApprovalGate.jsx:20-31`). Council already says scores do not verify facts (`ui/src/components/council/CouncilTab.jsx:30-32`).
Proposed interaction: one acknowledgment beside the full preview; show platform, format, revision, source links and “AI review skipped” or the actual version-linked review result. A failed review is not a skip. Allow explicit continuation to human approval without a passing score.
How to validate: skip reaches stage 3 with no fabricated score; below-threshold approval remains possible; an earlier-version review never appears as the current version's review. An edit resets acknowledgment and approval.

### E4 — Simplify: separate destination from content format
Why: “Video” is a medium; Instagram and YouTube are destinations with different deliverables. A script is not an uploaded or rendered video.
Current evidence: the picker labels five mixed formats as platforms, including generic short video and YouTube long video (`ui/src/lib/constants.js:17-56`; `ui/src/components/distribute/PlatformConfigModal.jsx:25-28`). Short-video generation uses one shared Reels/TikTok/Shorts prompt (`content_machine/distribution/engine.py:74-82`).
Proposed interaction: choose one destination first, then only its supported format. Label “YouTube — video script” or “Instagram — Reel script” precisely; provide a separate caption only when that adapter exists. Keep a general script option honestly labeled if platform-specific support is deferred.
How to validate: a generic script never receives an Instagram-ready badge. Unsupported caption/image/video generation cannot be selected or advertised as available; changing destination requires preparing and approving a new deliverable.

### E5 — Add: recognizable platform identity without capability inflation
Why: a brand icon speeds recognition only when the associated text accurately describes what the creator receives.
Current evidence: output chips have text and a colored dot for LinkedIn (`ui/src/components/distribute/OutputPreviews.jsx:53-66`); current descriptions promise “high-performing” and “viral” output (`ui/src/lib/constants.js:23-31`), without performance evidence in this review.
Proposed interaction: use recognizable LinkedIn, X, YouTube and, when supported, Instagram icons plus text; use a neutral mail icon for Newsletter. Use outline icons for Copy, Download, Edit and History. Remove decorative emoji and performance promises; keep warm editorial tokens.
How to validate: every icon has visible text or an accessible name, focus is visible, and monochrome/forced-color operation preserves meaning. No icon suggests account connection, automated publishing or completed video production.

### E6 — Add: a real manual-publishing finish
Why: generation is not the user's outcome; an approved, portable deliverable is. Copy and download can fail independently.
Current evidence: current preview offers Copy and a text pane, with only aggregate X thread length (`ui/src/components/distribute/OutputPreviews.jsx:72-85`). Clipboard failure returns false without surfaced feedback (`ui/src/hooks/useCopyToClipboard.js:6-14`); backend writes Markdown on the server (`content_machine/distribution/engine.py:315-333`), which is not a browser download.
Proposed interaction: primary “Copy [deliverable]”, secondary “Download .txt” (Markdown also useful for newsletters/scripts); retain selectable text as recovery. For X show numbered post boundaries, individual lengths and per-post copy alongside whole-thread download. Say “Publish manually in [platform].”
How to validate: clipboard denial shows an actionable error without claiming Copied; Copy identifies the actual artifact; downloaded text matches the approved content after documented encoding only. Announce “Download started,” never “Published.”

### E7 — Remove: misleading completion and unrelated replay
Why: a stored bundle proves only that files exist; an unrelated sample is not progress on the creator's private work.
Current evidence: demo failures return a seeded bundle (`content_machine/api/app.py:834-843`), currently labeled as replay (`ui/src/components/distribute/DistributeTab.jsx:113-116`). History calls `has_bundle` items “Distributed” (`ui/src/components/distribute/DistributeHistoryDrawer.jsx:28-29,109-112`), while the architecture states nothing publishes externally (`ARCHITECTURE.md:689-695`).
Proposed interaction: remove seeded/replay success paths from real work. On failure retain input and show Retry or Continue editing. Use lifecycle labels “Draft,” “Needs approval,” “Approved,” and factual copy/download events; never infer publication. Preserve historical records without presenting them as current authored work.
How to validate: exhausted quota never produces sample derivatives, a score or a completion tick; creating a file does not mark Published/Distributed. Legacy sample records remain identifiable and cannot inherit live approval.

### E8 — Add: optional adaptation as a separately approved branch
Why: the first deliverable should finish cleanly; another destination is additional work, not an obligation or an automatic rewrite.
Current evidence: four formats are enabled by default (`ui/src/components/distribute/DistributeTab.jsx:26`), and the form leads to “Generate Platform Bundle” (`ui/src/components/distribute/AnchorForm.jsx:157-163`).
Proposed interaction: after export, show a quiet “Adapt for another platform” action. Select one destination, copy the approved source into a new linked draft, and enter stage 2. Give that branch independent revision/review/approval/export state; leave the original usable.
How to validate: completing LinkedIn does not request X, video or newsletter generation; an adaptation adds no new anecdotes/metrics; its failure or cancellation preserves the original approval and export access.

### E9 — Add: trustworthy version history and explicit recovery
Why: people return to work, compare it and recover mistakes; a slug and a highest score do not establish the source of an exported artifact.
Current evidence: approval is session-only (`ui/src/app/useSharedFlow.js:10-11`); history loading resets approval (`ui/src/components/distribute/useDistributionSession.js:42-48`). Files overwrite per slug/channel (`content_machine/distribution/engine.py:326-333`); history prefers a peak Council draft before reading saved anchor text (`content_machine/api/app.py:876-914`), so its displayed anchor can differ from the bundle's source.
Proposed interaction: persist immutable deliverable versions, platform/format, actual source lineage and approval records within the creator's private workspace before promising durable resume. History opens a read-only version; “Continue editing as new version” preserves current input or requests an explicit replacement choice. Existing unmatched records say “Approval/source association unavailable.”
How to validate: reload restores the exact saved artifact only when a matching durable record exists; missing records require new approval. Two creators cannot load each other's exports; same-title work and repeated adaptations remain separate. Never delete historical data to clean the UI.

### E10 — Add: honest error states and accessible stage transitions
Why: empty history, inaccessible history, absent content and an older async result are different conditions requiring different recovery actions.
Current evidence: history fetch errors are swallowed (`ui/src/components/distribute/useDistributionSession.js:34-38`); the drawer then presents an empty result (`ui/src/components/distribute/DistributeHistoryDrawer.jsx:133-139`). Async results retain the submitted anchor snapshot (`ui/src/components/distribute/useDistributionSession.js:59-67,74`), a useful behavior to preserve.
Proposed interaction: show “Could not load history” with Retry while keeping the active draft; show a true empty state only after success. A late result belongs to its version and offers Compare/Open, never auto-approval. Use a full stage region for approval; focus its heading on entry and announce success/failure without a color-only cue.
How to validate: keyboard-only users can inspect all text, approve, go back and export; focus returns predictably. History failure cannot clear working text, a stale result cannot advance the current workflow, and narrow/zoomed layouts keep actions readable.

### E11 — Simplify: make completeness depend on grounded content
Why: output length and a rigid template must not pressure the engine to invent evidence just to appear finished.
Current evidence: the long-video prompt demands a Benchmark & Memory/Performance Math chapter (`content_machine/distribution/engine.py:85-104`) even though it also prohibits invented claims. The X prompt requests concrete numbers in the hook (`content_machine/distribution/engine.py:66-71`).
Proposed interaction: use only sections supported by the supplied material; show missing context as an editable question before approval. Separate third-party findings from the creator's experience. Never inject a metric, anecdote, customer or employment claim to fill a script/chapter.
How to validate: a source without benchmark numbers produces no fabricated benchmark, first-person incident or padded “proof”; the creator can approve a shorter, faithful deliverable and inspect its source context.

## Proposed compact layout and capability contract

Shared header: title, visible destination/format, current revision and History; one active stage beneath the progress strip.
Stage 3: full readable deliverable, modest platform-specific preview, character/post structure, expandable sources and changes, honest AI-review status, acknowledgment, “Back to edit” and “Approve this version.”
Stage 4: approved version label, readable unchanged content, Copy and Download, manual-publishing instruction; quiet Edit as new version and Adapt actions. Do not add another configuration modal or approval checkbox here.

| Destination / choice | Current text capability observed | Honest release wording / gap |
| --- | --- | --- |
| LinkedIn | Generated plain-text post | LinkedIn post; selected-platform version must be prepared before approval. |
| X | Single text string with thread instructions | X thread; post segmentation/validation is additional work, not established by total length. |
| YouTube | Short generic script or long YouTube script | YouTube script; no rendered footage, thumbnail, upload or guaranteed runtime. |
| Instagram | Shared generic short-video prompt mentions Reels | Platform-specific Reel script/caption requires explicit support; do not claim an Instagram asset package today. |
| Newsletter | Markdown briefing | Newsletter draft; no provider connection, subscriber delivery or email-layout rendering. |

The capability boundary above comes from `content_machine/distribution/engine.py:35-41,74-118,256-269`; it does not establish output quality or platform compliance.

## Acceptance scenarios for the combined journey

1. Own notes or a sourced idea reaches a selected-platform draft; skipping Council is explicit and stage 3 reads “AI review skipped,” then human approval enables export.
2. Approval of version 4 exports version 4 unchanged; editing one space creates a new unapproved version while the historical approved version remains available.
3. An X thread opens with clear per-post boundaries; overlong posts are identified before approval, never silently shortened at export.
4. Requesting an Instagram caption cannot silently return a generic video script; unavailable capabilities are explained before work begins.
5. A generation timeout, clipboard denial or download initiation failure preserves the content and shows the correct retry/recovery action, without unrelated sample success.
6. Adapting an approved LinkedIn post to YouTube creates another draft; cancelling it leaves the LinkedIn deliverable approved and exportable.
7. Reopening legacy history exposes unknown lineage/approval; neither a peak score nor the presence of files upgrades it to approved or published.
8. Private-workspace tests prevent cross-creator artifact/history/export access; reload/resume claims are accepted only after persisted version/approval recovery is verified.

## Delivery priorities and open decision

Must have: E1-E3 exact deliverable approval/export boundary; E4-E6 truthful supported formats and real copy/download; E7 removal of fake completion/replay; E9 identity/private persistence before durable-resume promises; E10 failure/accessibility handling; E11 grounded formats. E8 must preserve branch isolation whenever adaptations ship.
Defer: automated publishing, account connections, bulk bundle generation, image/video production, publication analytics, rich platform replicas, and multi-platform simultaneous approval. They do not help this manual publishing finish.
Material unanswered decisions: on return, open the latest saved work or a saved-work list? Either option must show saved status and cannot infer approval when persistence is unavailable.
For Instagram's first release, does the creator need a Reel script, a caption, or both? These are different deliverables; the current shared short-video script cannot establish caption support. If both are needed, preview and approve each explicitly as one clearly named package or separate artifacts.
Validation status: source-based planning only; no implementation, live model, browser, publication or representative-user validation was performed for this report.
