# Whole-product review: customer value and scope reduction

Date: 2026-11-05. Planning only; independent product-owner critique, not user research.
Inputs: the complete brief/protocol, all five specialist reports, and `docs/ui-workflow-plan.md`.
Evidence: reuse the specialists' inspected source and finding IDs; no additional code/browser audit or measured product results.
Verdict: keep the coherent four-stage direction, but release a reliable path to one approved portable artifact before expanding editorial machinery.
The creator's outcome is confidence in what they can publish; scores, generated bundles, and completed steps are not outcomes by themselves.
All six user answers are settled. Recommendations below are design hypotheses, including labels and the proposed narrower platform boundary.

## P1 — Simplify: one workspace, with progress subordinate to the work

Why: returning to a real draft should take less effort than learning how the engine is organized.
Current evidence: N1–N3/N8 identify competing subsystem navigation, no saved-work landing, and state-based startup; the brief now resolves N3's conditional choice.
Proposed interaction: open the saved ideas/drafts list with prominent Resume and New content; empty state offers New content without fabricated records.
Inside an item, keep one active region and four revisitable stages; show title, destination/format, actual save state, and History once.
Keep Lessons and Settings reachable as support; reject an extra dashboard, top-level History, guide toggle, or compulsory stage tour. Three equal top-level buttons are not necessary.
How to validate: resume either of two same-title items, detour to Settings, and return to the same item/stage without rerunning AI or replacing text.

## P2 — Simplify: stage 1 earns its place by establishing intent and material

Why: a creator needs a destination and something worth saying, not a persona interview or a scored idea before writing.
Current evidence: I1–I6/I8 identify discovery-led intake, inconsistent source actions, presumed personal metrics, and source/context loss; D1 describes placeholder handoff.
Proposed interaction: after New content, choose platform/format, then equally prominent own-notes and discovery starts; existing draft is immediate within the own-material route.
Use one editable point/notes field, optional dictation, and a compact source attachment. “Use this idea” must work identically for fresh and previous discoveries.
Move source maintenance to Settings with a contextual link; keep refresh/search in discovery. Do not label every ingested result a saved creator idea.
Reject mandatory profile completion, interviewer selection, taxonomy setup, experience claims, and metric prompts. A reasoned, attributed reaction is sufficient material.
How to validate: no sources/profile still permits notes or a pasted draft; source-only commentary remains commentary, and supplied draft bytes survive entry unchanged.

## P3 — Simplify: stage 2 earns its place through controllable improvement

Why: the creator needs an editable selected-platform artifact and useful advice, with authority to decline both drafting and reviewing assistance.
Current evidence: D1–D6 show split drafting/review, omitted context, hardcoded platform/persona, and duplicate polishing; D7/D8 already provide comparison/async foundations.
Proposed interaction: one editor; Create draft when starting from notes, Review draft when advice is wanted, and explicit Skip AI review when it is not.
Carry sources, creator interpretation/experience, platform/format and saved preferences into actual requests; expose optional evidence details without adding three mandatory forms.
Keep one wording-suggestion action and full comparison before acceptance; remove score prestige, judge-operation controls, burstiness badges, and “humanity” claims.
Failed review offers Retry or explicit Skip; it never becomes skipped automatically. Editing after review labels that review as earlier-version advice.
How to validate: a pasted draft is never regenerated on entry; declined suggestions preserve it, accepted changes create recoverable versions, and late AI results cannot replace newer work.

## P4 — Keep: stage 3 earns its place through one meaningful human decision

Why: AI advice cannot decide whether the creator stands behind the actual deliverable that will leave the workspace.
Current evidence: D10/E1–E3 show approval tied to Council results and a later Distribution rewrite; E9 identifies session-only approval and uncertain historical lineage.
Proposed interaction: show the entire actual deliverable, format boundaries, honest review status, expandable evidence, and one explicit “Approve this version” action.
Recommend that the labeled approval action itself records acknowledgment; add a separate checkbox only if later testing shows creators misunderstand the decision.
Approval binds item/version/content/platform/format. Editing creates an unapproved revision; history retains the prior approved snapshot, and restoring matching words does not revive consent.
Keep review optional and approval mandatory; reject passing-score gates, override language for skipped review, and a second unchanged-text confirmation in export.
How to validate: skipped, failed, earlier-version and completed reviews are distinguishable; exact human approval is possible without a score and impossible to borrow from another artifact.

## P5 — Simplify: stage 4 earns its place by making the approved work portable

Why: the creator came to leave with usable content; generation or a server-side file does not complete that job.
Current evidence: E2/E6–E8/N14 identify post-approval rewriting, weak copy feedback, non-browser downloads, default bundles, and misleading completion labels.
Proposed interaction: approval advances directly to unchanged selectable text, Copy, Download, and a short manual-publishing instruction; export makes no model call.
Reject tone controls, Humanize, Generate bundle, account connections, and publication status here. Say what happened: copied or download started, never published.
Afterward offer a quiet optional adaptation: create a linked unapproved draft for one other destination/format, reuse the same workflow, and preserve the original.
A linked new item is sufficient initially; defer a branch-tree interface, bulk adaptation, and simultaneous multi-artifact approval.
How to validate: clipboard/download failure leaves approved text usable; export bytes match approval, and cancelled/failed adaptation cannot alter the original artifact or sign-off.

## P6 — Add: private durable work is part of the minimum product

Why: saved-list/Resume and a private workspace are promises about the creator's work, not optional infrastructure polish.
Current evidence: I9–I11/D8/E7/E9/N4–N11/S8–S9 identify disposable intake, session state, swallowed errors, seeds/replays, and incomplete durable associations.
Proposed interaction: persist typed work independently of AI; acknowledge Saving/Saved/Not saved truthfully, protect server access by creator, and retain exact item/version/context lineage.
Keep previously loaded material on refresh failure; distinguish empty, no matches, unavailable and partial success. Remove invented profiles, scores, reviews and unrelated fallback successes.
Bind dictation and AI results to their originating item/version/field; denied microphone permission or AI failure must leave manual editing usable.
Do not delete ambiguous legacy or Comments data; retain it with unknown provenance/approval rather than upgrading it or exposing it as another creator's content.
How to validate: reload acknowledged notes without ever running AI; simulate save/load failures and cross-creator requests. Hosted release waits for verified ownership and durable storage.

## P7 — Move / Defer: supporting views must repay their interruption cost

Why: preferences help only when they reduce later corrections; configuring the engine is not a prerequisite to expressing an idea.
Current evidence: S1–S7/S9 expose optional Lessons value, duplicated manual diff entry, misleading activation, limited editing, raw profile context, and invented identity.
Proposed interaction: Settings owns optional factual profile and discovery sources; Lessons owns the single editable writing-preference collection, linked from Settings without duplicate editors.
Ship straightforward Add/Edit/Stop using with explicit Save and use and actual errors; AI suggestions, if present historically, remain pending until individually approved.
Defer new inferred-learning/diff-extraction flows, semantic dashboards, raw prompt editing, model tuning, and extensive voice onboarding. Do not add a post-export learning task by default.
Keep universal grounding/approval constraints separate from author preferences; preference changes affect future requests, never rewrite approved content.
How to validate: finish both own-note and discovery paths without opening Lessons/Profile; change a preference later without touching a repository file or losing the active draft.

## P8 — Simplify: resolve cross-view conflicts once

Why: individually reasonable screens become a burden when they ask the same decision twice or imply incompatible guarantees.
- I11/D10/N3/E9 open return questions are superseded: saved-list first plus Resume; platform choice applies to New content, not reopening an already configured item.
- E4's conditional Instagram support is superseded by the brief: caption and Reel script both ship explicitly. Recommend separate format choices/artifacts; neither silently substitutes for the other or forces a package.
- E1's “one handoff” keeps four compact stages, while N2 permits revisits; it does not justify another approval modal, export rewrite, or compulsory AI review.
- D2/I6 evidence fields are one shared context record, not duplicated intake/interview/editor forms; S5's writing preferences link to P7's single collection.
- N4/E8 branches preserve lineage without a tree editor; I8 source history remains distinct from P1 creator-saved work. Unknown legacy lineage never becomes approval.
How to validate: one end-to-end walkthrough finds each platform, source, preference and approval decision in one authoritative place.

## P9 — Keep / Defer: smallest complete release and evidence of success

Why: fewer truthful capabilities beat a broad menu whose outputs need another tool to become the promised artifact.
Recommend proving the smallest complete internal slice with LinkedIn posts plus Instagram captions and Reel scripts for technical creators. A public launch limited to that slice is an unaccepted scope tradeoff, not authorization to remove current formats.
Reel scripts contain grounded production cues and editable spoken text; captions are actual caption artifacts. Preserve X/YouTube/newsletter access and history pending explicit scope disposition; any retained launch format must meet the same approval/export contract before release.
Must have: P1–P6, contextual safe dictation, basic P7 preferences/settings, both equal starts, direct draft entry, and one optional linked adaptation; no fabricated material or mandatory personal anecdote.
Acceptance: exercise own notes, source-only reaction and existing draft through explicit AI skip or current review, human approval and byte-matching export; verify both Instagram formats separately.
Acceptance: edit after approval, restore an old version, switch items during transcription/review, reopen after restart, deny clipboard access and fail storage/provider requests; no loss, borrowed consent or sample success.
Acceptance: complete these journeys by keyboard/screen reader at 200% text resize and 320px width; labels, focus and recovery remain usable without color-only status.
Success checks: observe creators finding Resume, explaining what they approved, and obtaining the expected artifact without manual handoff copying between stages; record failures before choosing numeric usability targets.
No material unanswered user question remains. The coordinator must disposition the proposed platform tradeoff; validate labels and approval acknowledgment in creator trials without reopening the six confirmed answers.
