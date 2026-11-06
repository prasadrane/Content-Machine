# Navigation, returning work, and recovery review

Date: 2026-11-05. Planning only; specialist interaction-design critique, not user research.
Scope: shell, entry, history, saved-work model, stage navigation, failure states and access.
Confirmed: private workspace; equally prominent personal ideas and discovery; optional AI review; mandatory human approval; manual publishing.
Evidence: Tier 2 graph orientation plus live source. Additional-path coverage generation 2026-11-05T15:44:57Z returned metadata_changed; all seven paths were read directly, including the drawer's partial parse at line 57. No pagination remained for the targeted symbol search or coverage batch.
The four-stage direction is sound if stages describe this content item's state and remain revisitable. A mandatory linear wizard would obstruct existing-draft and returning-work journeys.
All proposed copy and defaults below are design hypotheses. Durability, privacy guarantees and accessible behavior require implementation and validation.

## Findings

### N1 — Simplify: one production destination for the creator's work
Why: six subsystem choices require users to infer the handoff before they can write.
Current evidence: `ui/src/app/tabs.js:8-47` exposes Oracle, Council, Distribute, Lessons, Audio and Profile; `ui/src/App.jsx:28-33,51-59` also mounts the demo navigation entry.
Proposed interaction: keep Workflow prominent; make Lessons and Settings supporting destinations. Remove standalone Audio and place dictation beside text. Do not introduce a dashboard, workspace switcher or extra top-level History destination.
How to validate: from each entry route, a new creator can find personal idea intake, discovery and an existing draft without knowing subsystem names; Settings and Lessons return to the same item.

### N2 — Simplify: stage navigation represents prerequisites, not a compulsory tour
Why: Council is optional, while approval is a real requirement; viewing a tab is not completion.
Current evidence: `ui/src/components/DemoBanner.jsx:5-18` treats tab location as the current step and includes Lessons as a fifth step; approval and review both resolve to Council.
Proposed interaction: use four contextual stages, provisionally Choose / Draft & review / Approve / Export. Stage 2 offers Run AI review and Skip AI review. Keep previous stages available; block only actions missing their prerequisites and explain the missing input beside that action.
How to validate: an existing draft can explicitly skip AI review, reach human approval and export; choosing a stage alone cannot create reviewed, approved or exported status.

### N3 — Add: a deliberate return destination, conditional on the user's choice
Why: returning creators need orientation and a reliable way to find older work.
Current evidence: `ui/src/App.jsx:11-19` starts at Oracle on every mount and keeps navigation in component state; `ui/src/components/WorkspaceEntry.jsx:9-14` has no saved-item return path.
Proposed interaction: if saved-list-first is chosen, open Your content with New content plus a prominent Continue latest row. If automatic resume is chosen, reopen the last acknowledged saved item/stage and keep All content visible. A missing/deleted/inaccessible last item returns to the list with an explanation.
How to validate: after reopening, users can locate two different saved items; an unavailable latest item never strands them, silently creates a blank replacement or opens somebody else's content.

### N4 — Add: one private workspace containing multiple content items
Why: one active editor must not become one replaceable draft for the entire product.
Current evidence: `ui/src/app/useSharedFlow.js:6-11` owns one Council value, one distribution anchor and session approval; `ui/src/components/distribute/useDistributionSession.js:42-48` replaces the active anchor when history is selected.
Proposed interaction: define the workspace as the private container; each content item has its own title, platform, sources, notes, versions, review/approval state and updated time. Opening another item preserves the first. Adaptations belong under their parent item as separately approved versions or branches.
How to validate: switch between A and B with identical titles and different source notes; each reopens its own text and status, and an adaptation cannot inherit its parent's approval.

### N5 — Add: a save contract before promising recovery
Why: staying mounted during navigation is useful continuity but is not a durable save.
Current evidence: `ui/src/App.jsx:74-78` retains three visited panels; `ui/src/app/useSharedFlow.js:10-11` calls approval session-only; `docs/ui-workspace.md:15-19` explicitly excludes refresh/restart recovery.
Proposed interaction: persist item edits independently of AI actions. Show Saving, Saved with time, or Not saved / Retry only from actual acknowledgement; for local mode say Saved on this device. Before durable storage exists, keep a concise session-only notice and a working text-download escape hatch; never label it Saved.
How to validate: type without running AI, refresh/restart and recover acknowledged text; failed writes retain editor contents and expose Retry/download. Hosted ownership and storage isolation must exist before promising private durable drafts.

### N6 — Simplify: distinguish the content list from an item's version history
Why: finding a story and comparing its revisions are different jobs; neither should overwrite work accidentally.
Current evidence: `ui/src/components/council/HistoryTimeline.jsx:14-43` is an iteration list with Load; `ui/src/components/council/useCouncilSession.js:104-105` assigns loaded text directly; `ui/src/components/distribute/DistributeHistoryDrawer.jsx:51-60,98-119` mixes past drafts and bundles.
Proposed interaction: All content opens items; Version history stays inside the current item. Open older versions read-only with Compare and Restore as new version. Preserve current work; do not silently replace it or recover approval from matching text alone. Retain legacy records without inventing missing provenance.
How to validate: open an old version while current edits exist, compare and cancel without data loss; restoring creates an unapproved working version while the original remains inspectable.

### N7 — Add: reversible back, forward and stage-jump navigation
Why: a clear workflow still needs predictable exits, especially after detours into settings or history.
Current evidence: `ui/src/App.jsx:15-19` updates only React state; `ui/src/App.jsx:71-78` swaps the active surface without a URL-backed item/stage in this shell.
Proposed interaction: give saved items and stages stable private routes; use browser Back/Forward for navigation, plus visible All content and previous-stage links. Normal stage jumps preserve inputs. Warn only when an action would actually discard unsaved edits; editing approved content creates a revision and requires approval again.
How to validate: Back after Settings restores item, stage and editor position; Forward repeats navigation without rerunning AI; a direct Export route explains missing approval and offers the route to approve.

### N8 — Simplify: the empty Workflow starts with two equal choices
Why: creators should not have to browse sources to discover that they can bring their own ideas.
Current evidence: `ui/src/App.jsx:73` places WorkspaceEntry above Oracle; `ui/src/components/WorkspaceEntry.jsx:6-12` offers Review a draft, Adapt an anchor and a sample, rather than equal idea/discovery entries.
Proposed interaction: New content offers equally weighted Your idea and Discover signals. Your idea accepts notes, dictation or a pasted draft; Discover shows configured-source items and their provenance. A draft may advance with minimal intake; source configuration is optional until discovery needs it.
How to validate: with no profile, sources or saved items, a person can paste a draft and continue; an unconfigured discovery state offers Configure sources and Your idea without fabricated results.

### N9 — Remove: guide/banner noise; retain concrete operating notices
Why: explanatory chrome competes with the actual task, while real storage and service failures need attention.
Current evidence: `ui/src/components/DemoBanner.jsx:53-61,65-87` adds public-demo copy, sample launch, limits and a guide; `ui/src/App.jsx:63-65` displays generic Online/Offline from a health check (`ui/src/app/useServerHealth.js:9-13`).
Proposed interaction: remove the demo guide, sample launch and decorative status from the private production workflow. Replace them with contextual notices such as Draft not saved or AI unavailable; keep typing available where possible. Server health alone must not imply AI availability or data safety. Retain a truthful temporary-data notice wherever storage really is temporary.
How to validate: a healthy API with failed AI shows the failed AI action, not a reassuring global Online; loss of persistence identifies affected work and offers retry/export without burying the editor.

### N10 — Keep: async results belong to the item/version that requested them
Why: navigating away should neither lose work nor let a delayed response rewrite another item.
Current evidence: `ui/src/components/council/useCouncilSession.js:33-42,60-71` captures request identity and guards history; `ui/src/components/distribute/useDistributionSession.js:59-67,74` captures the generating anchor and detects earlier output.
Proposed interaction: preserve this ownership when replacing mounted panels with stages. Pending work shows an item-specific status; users can navigate to other items. Returning reveals completion or failure for the original version. If reload survival is unsupported, state that limitation instead of promising a background job.
How to validate: start review on A, edit A or open B, then resolve the request; B is unchanged and A's result is labeled with the actual reviewed version. A rejected request retains input and supports a deliberate retry.

### N11 — Add: distinct empty, loading, unavailable and no-match states
Why: an unavailable library must never look like a creator has lost every saved draft.
Current evidence: `ui/src/components/distribute/useDistributionSession.js:34-38` and `ui/src/components/council/useCouncilSession.js:35-48` swallow history errors; `ui/src/components/distribute/DistributeHistoryDrawer.jsx:126-138` has loading/no-match presentation but no supplied error state.
Proposed interaction: show loading while fetching, No saved content only after a successful empty response, No matches with Clear search after filtering, and Could not load content with Retry on failure. Retain a visible previously loaded list as stale when refresh fails; keep New content available without implying its saves work.
How to validate: offline first load does not show No saved content; zero-result filtering preserves all records; retry restores the list without clearing search or the active draft.

### N12 — Keep: semantic navigation and focus, then complete accessible journeys
Why: reducing destinations helps only if keyboard and screen-reader users can identify location and recover context.
Current evidence: `ui/src/components/ui/TabBtn.jsx:3-9` has native buttons and aria-current; `ui/src/App.jsx:22-24,51,71` provides named navigation/main and focuses main after switches; the history drawer declares a labeled dialog at `ui/src/components/distribute/DistributeHistoryDrawer.jsx:51`.
Proposed interaction: keep these foundations; use route links for destinations and an ordered stage list with aria-current=step. Add Skip to content, a visible current-stage heading and text status. Restore focus to the opener when closing history and to the same item row after returning; announce save/failure changes without reading the whole draft on each edit.
How to validate: complete idea -> skip AI -> approve -> copy using keyboard and a screen reader; unavailable actions explain why, dialog focus/Escape/return work, focus stays visible, and stage/status never depend on color or icon alone.

### N13 — Simplify: one mobile path with the same information hierarchy
Why: a compact strip should not become clipped chips, repeated headers or an editor hidden beneath navigation.
Current evidence: `ui/src/App.jsx:35-36,51` makes the header sticky and wraps navigation; `ui/src/components/DemoBanner.jsx:54,67-68` adds another wrapping navigation region. `docs/ui-workspace.md:84-87` leaves full keyboard, text-resize and narrow reflow checks outstanding.
Proposed interaction: on narrow screens retain title, platform, save state and the active stage; expose every stage through one compact wrapped strip or labeled stage chooser. Keep one primary action near the editor; dialogs use the available viewport and preserve a visible close action. Avoid a separate mobile workflow or a second sticky action stack.
How to validate: test 320 CSS-pixel width, 200% text resize and phone keyboard; no horizontal page scroll, clipped labels, hidden focus or unreachable controls; long titles and failure messages remain readable.

### N14 — Simplify: completion reports the action that actually happened
Why: manual publishing ends the product's authority at the handoff, not at a fictitious distribution state.
Current evidence: `ui/src/components/distribute/DistributeHistoryDrawer.jsx:23-29,59-60,109-112` calls records with bundles Distributed; bundle existence is the filter criterion.
Proposed interaction: Export offers copy/download of the approved deliverable and optional Create adaptation; never silently generate fresh wording. Record Approved, Copied or Downloaded only when supported by actual events; do not claim Published. Offer optional Lessons after handoff and Start another, while keeping the completed item available.
How to validate: a failed clipboard action reports failure and offers selection/download; a successful download cannot mark a post published; optional adaptation produces a separately approvable branch and does not modify the approved original.

## Priorities and decisions

Must have before the redesigned private workflow is relied on: N1-N2 coherent navigation and optional AI; N4-N5 durable item/ownership/save contract; N6-N7 safe restoration and travel; N8 equal entries; N9-N11 truthful states; N12-N14 accessible manual handoff.
N3 must remain conditional until the startup choice is answered; either option needs the same saved-item catalogue and safe route recovery.
Do the persistence and lineage foundation before advertising automatic resume; carry forward current in-session continuity until an equivalent replacement is verified.
Defer workspace switching, teams, public showcase, elaborate dashboard statistics, tutorial mode, task-center navigation, offline synchronization and advanced saved-list filters.
Do not reopen confirmed private-workspace, equal-entry, optional-AI or manual-publishing decisions.
Material open decisions: saved-list-first versus automatic resume; supported Instagram deliverables; engineering-focused versus broader creator audience. The last two affect platform controls and wording, not the navigation/recovery contract.
Verification boundary: source inspection and design acceptance scenarios only; no code changes, new browser audit, representative user study or runtime accessibility pass performed for this report.
