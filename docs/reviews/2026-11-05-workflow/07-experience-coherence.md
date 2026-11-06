# Whole-product review: experience coherence

Date: 2026-11-05. Lens: veteran UX architect and whole-product owner. Planning only.
**Verdict:** Keep the four-stage direction, but organize it around one persistent deliverable rather than four tool visits. Resolve duplicated preferences and post-approval writing before implementation.
Evidence: read the updated brief, all five specialist reports, and `docs/ui-workflow-plan.md`; reuse their inspected live-source evidence below. No new structural audit, browser inspection, user study, or product validation was performed.
The updated brief supersedes stale specialist questions: private workspace, saved-work-first with prominent Resume, equal own/discovery starts, optional AI review, Instagram captions AND Reel scripts, and engineering creators are settled.

## Product decisions

### A1 — Keep / Simplify: four stages are useful states, not four mandatory visits
Why: choosing material, developing wording, authorizing exact content, and taking it away are different decisions. Four stages make their boundaries visible without adding another top-level tool.
Evidence: N1/N2, D1/D10, E1/E2; N2 cites `DemoBanner.jsx:5-18` confusing location with completion, while E1 cites `DistributeTab.jsx:120-155` writing after anchor approval.
Interaction: keep the confirmed four stages and one active region. “Start with an idea”, “Draft and review”, and “Copy and export” are proposed labels, not accepted copy. Existing drafts and resumed items enter their relevant state; viewing a stage never completes it.
Check: a pasted draft can traverse stage 2 without generating or running AI, approve once, and immediately export. Do not merge or add stages in this plan; any later count change conflicts with confirmed direction and needs product disposition.

### A2 — Change / Simplify: put the saved-work landing outside the active item's stage strip
Why: finding work is a different job from choosing a new source. A landing with four empty stages would contradict saved-work-first and imply every return restarts intake.
Evidence: I1/I8/I11, N3/N6/N8; I8 distinguishes scan history from saved ideas, and N3's formerly conditional return choice is now answered by the brief.
Interaction: Workflow opens the real saved ideas/drafts list, prominent Resume, and New content. Resume identifies the item and opens its acknowledged state; New content first chooses a platform, then gives equally prominent Your idea and Discover choices. Your idea accepts notes or an existing draft without another required mode selector.
Check: an unselected scanned article is absent from saved work; deliberately saving/using it creates a real item. A creator with two drafts can resume either without replacing the other. Never show a third top-level Archive or History destination.

### A3 — Change / Simplify: choose destination, then a precise deliverable
Why: platform and format answer different questions; mixed “platform” choices make the creator discover output limitations too late.
Evidence: I2, D3, E4/E5; E4 cites `constants.js:17-56` mixing platforms/formats and `distribution/engine.py:74-82` using a generic short-video prompt.
Interaction: choose one destination before new-item intake, then expose only its genuine formats. Instagram offers Caption and Reel script in the first release; each starts one deliverable, rather than requiring both every time. Keep destination/format visible; a subsequent format or platform adaptation creates separately approvable work.
Check: Caption never returns a video script; Reel script is never presented as produced video. Both Instagram capabilities are release work, not gaps that can silently be deferred. Opening saved content preserves its destination rather than presenting the picker again.

### A4 — Change / Move: use one editor and one context record across intake and development
Why: asking for notes in stage 1 and different notes in stage 2 creates duplicate effort and uncertainty about which text actually informs the draft.
Evidence: I4-I6/I11, D1-D3/D6; D2 cites `DraftingStudio.jsx:17-19,91-100` keeping notes outside requests, while I6 finds source context lost at synthesis handoff.
Interaction: stage 1 captures material; stage 2 develops the same item. Keep optional author notes, source attachments, and interpretation in one expandable context panel, editable from either stage. One draft editor accepts typed/dictated text and one optional wording-suggestion action; a pasted draft is not regenerated automatically.
Check: a source-only technical opinion can finish without a personal incident or metric. Source excerpts and author contributions survive every handoff and actually reach writing requests; accepting proposed edits preserves the prior wording and exposes changed claims.

### A5 — Keep / Simplify: optional AI is a decision, not an incomplete progress warning
Why: Council is advice; a human-authored draft without AI review must remain a normal route through this product.
Evidence: D4/D7/D8/D10, E3, N2; D10 cites approval currently coupled to results in `VerdictPanel.jsx:7,33` and separate peak approval in `CouncilTab.jsx:92-100`.
Interaction: offer Review draft as optional. For an unreviewed current version, the forward action explicitly says “Skip AI review and continue”; after a failure, offer deliberate continuation without review while retaining the failure status. Show current, earlier-version, failed, and skipped outcomes accurately, without score-driven permission or repeated skip prompts on navigation.
Check: a creator can type every word, skip all AI actions, and reach mandatory human approval. A failed request does not become a pass or a skip automatically; changing wording cannot borrow an earlier review.

### A6 — Keep / Simplify: one authorization, then a frictionless manual handoff
Why: authorizing a version and obtaining it are distinct jobs, but repeating consent or rewriting between them destroys the benefit of both.
Evidence: E1-E3/E6/E8, N14; E2 cites default-on humanization in `DistributeTab.jsx:24-26` and rewriting after anchor approval in `distribution/engine.py:149-166`.
Interaction: stage 3 previews the complete deliverable and uses one explicit “Approve this version” action with a clear consent statement; do not stack checkbox, modal, and second confirmation. Approval covers item/version/destination/format/exact content. Stage 4 immediately offers Copy and Download of that snapshot; no settings, generation, or second sign-off intervenes.
Check: export makes zero model requests and matches approved text. An edit or adaptation creates unapproved work while the historical approved artifact remains exportable. Clipboard denial retains selectable content and offers download; successful handoff never implies Published.

### A7 — Change / Move: give reusable writing preferences one editable home
Why: Lessons' active preferences and Settings' Writing defaults otherwise become competing sources of author voice, making a future draft's behavior impossible to explain.
Evidence: S1/S3-S5 and the candidate plan both place writing guidance in two destinations; S4 requires editing/stop-using, while S5 introduces Writing preferences in Settings.
Interaction: Lessons owns the single reusable preference list and its approvals/history. Settings contains About you and Discovery sources plus a direct link to that same preference editor; remove the second Writing defaults editor. Neutral product defaults are identified as defaults, not learned author rules. Contextual Remember this preference opens the same editor and returns to the item.
Check: changing a preference through either entry updates one record; it affects subsequent requests, never saved approved text. A factual correction stays on its item unless the creator deliberately saves a general preference. Manual Save and use is approval; AI suggestions remain pending until approved.

### A8 — Reject / Remove: hidden machinery and setup disguised as creative progress
Why: moving all complexity behind a disclosure is insufficient if creators still need it to understand the primary action or recover a failure.
Evidence: I3/I5/I8-I10, D4-D6, E5/E7, S5-S7; I9 finds service errors described as threshold outcomes and S6 identifies invented identity/verification claims.
Interaction: remove guide toggles, demo launch/replays, invented persona, compulsory interviews, score prestige, duplicate polish, raw slugs, and unsupported performance promises. Keep source health and Manage sources beside discovery; optional author setup stays contextual. Use labeled platform icons, outline actions, and the shared editorial theme.
Check: a first-time creator with empty profile/sources can finish their own draft. Failed discovery names the failure and offers retry or own notes; it never looks like an editorial rejection. Blank author fields never acquire someone else's history.

### A9 — Keep / Add: preservation is the shared contract, not another recovery destination
Why: reliable return paths matter more than elaborate history controls; stage navigation must not be a destructive operation.
Evidence: I7/I11, D8/D9, E9/E10, N4-N7/N10-N13, S8/S9; N5 cites session-only approval in `useSharedFlow.js:10-11`, so durable recovery is not established current behavior.
Interaction: persist private items, context, versions, and approvals before promising Resume/Saved across restart. Keep All content distinct from item Version history; restore old wording as a new version. Settings/Lessons return to the same item/stage. Bind AI/transcripts to their originating item/version/field; warn only before actual unsaved loss.
Check: item A's delayed result cannot rewrite B; permission denial leaves typing usable; failed saves retain exact text and retry/download. Loading errors never masquerade as an empty library. Server ownership protects history/files/exports; URL, keyboard, and screen-reader navigation preserve context.

### A10 — Defer / Simplify: release the complete writing loop before secondary sophistication
Why: fewer controls should reduce conceptual work, not shift essential safety into a later phase.
Evidence: I12, E8/E11, N12-N14, S1-S4/S8; specialist deferrals are acceptable only when they preserve confirmed capabilities and the complete manual-publishing route.
Interaction: defer automated learning from comparisons, judge/ranking dashboards, advanced merging/taxonomy, rich platform replicas, bulk adaptations, publishing connections, and team/public-workspace concepts. If Lessons ships, real add/edit/stop-using and truthful activation remain required. Three top-level buttons are a workable hypothesis, not a newly asserted user requirement.
Check: release includes technical-creator wording, actual Instagram caption/Reel adapters, contextual dictation, empty/error states, and accessible operation. Do not ship an attractive four-stage shell that still requires the former subsystem pages to finish.

## Smallest complete journey and counterexamples

1. Open saved work; Resume a named item or New content. For new work choose destination/format, then equally prominent own input or discovery; retain the chosen source separately from author perspective.
2. Develop one deliverable in the same editor, manually or with optional draft/review/wording help. Compare proposed edits; keep original input and context. Explicitly skip AI when proceeding without a current review.
3. Inspect the full platform-specific version and approve it once. Obtain the unchanged artifact by copy/download. Optional adaptation starts another linked, unapproved deliverable; Lessons is a later detour, never a fifth stage.
Counterexamples: pasting a complete post must not trigger an interview; returning to an approved caption must not reopen platform selection; an article about an outage must not become the creator's outage; an edited-back-to-identical draft must not revive historical approval.
Release boundary: a real private, recoverable authoring-to-export loop, both required Instagram formats, real editable preferences/settings, and safe adaptations whenever offered. Hosted release requires authentication/ownership and durable storage; a session-only build must state its limits and cannot claim this boundary complete.

## End-to-end acceptance and remaining disposition

- Empty account: keyboard-only paste -> explicit AI skip -> full preview -> one approval -> matching copy/download; no profile, source setup, sample content, or Lessons visit required.
- Discovery: a third-party engineering article plus author interpretation survives generation/revision/approval/export with inspectable source context and no invented personal anecdote; partial source failures preserve usable results.
- Return/revision: save A and B, restart, resume each exact acknowledged state; compare/restore an older A version without losing current work or its historical approved export. Unsaved and load-failure states remain truthful.
- Asynchrony: dictate/review A, switch to B and edit, then finish/fail A's request; no cross-item insertion, replacement, approval, or forced navigation occurs.
- Platform/handoff: independently finish an Instagram caption and Reel script; adapt either after export, cancel, and retain the original. No copy, download, generic script, or saved bundle claims publication or completed video.
- Preferences/access: alter one reusable preference via Settings' link, verify the same Lessons record and future-request effect; exercise failed activation, keyboard focus/return, screen reader status, 200% text resize, and 320px reflow across the whole journey.
Must-have disposition: A2/A3/A4/A7 remove contradictions; A5/A6/A9 preserve trust; A8/A10 reduce scope. A1 retains all four stages. These are proposals and acceptance checks, not measured improvements or implemented behavior.
Unresolved creator questions: none required to settle this coherent journey. Proposed labels, the single-control consent design, and the shared preference-home decision need coordinator disposition; they do not reopen the six answered user questions or authorize implementation.
