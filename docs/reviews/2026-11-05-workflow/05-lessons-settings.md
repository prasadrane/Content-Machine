# Lessons, settings, and real-content management review

Date: 2026-11-05. Planning only; expert source critique, not representative-user research or a browser audit.
Purpose: help a creator repeatedly finish publishable work in their own voice; preferences are supporting infrastructure.
Confirmed: private creator workspaces; equal own-idea/discovery entry; optional AI review; mandatory human approval; manual publishing.
Also confirmed: saved ideas/drafts first with prominent Resume; Instagram captions and Reel scripts; technical/engineering creators first.
Recommendations below are design hypotheses. Current behavior is cited separately; no product change or validation is claimed.
Evidence: graph Verify pass found the Lessons/Profile symbols; coverage generation `2026-11-05T15:44:57Z` flagged all 20 requested paths `metadata_changed`.
Direct live-source reads supplied every implementation observation below; graph search returned 10 symbols with no remaining page.

## S1 — Keep: Lessons as an optional place to reduce repeated edits

- Why: Lessons earns its place when the creator stops correcting the same recurring writing choice; it should never block publishing.
- Current evidence: `ui/src/components/lessons/LessonsTab.jsx:95-123` leads with custom rules and a two-text diff tool; `RulesLists.jsx:20-26` exposes governance machinery.
- Proposed interaction: retain optional Lessons access and a contextual “Remember this preference” after an edited deliverable is ready; never make it a fifth Workflow stage.
- Default view: a short list of the creator's active preferences, pending suggestions only when present, and one “Add preference” action.
- Empty state: “No saved writing preferences yet. You can keep writing and add these later.” Return directly to the current Workflow item.
- How to validate: a first-time creator reaches copy/download without opening Lessons; a repeat creator locates and changes a preference without using a diff tool.

## S2 — Simplify: teach from a real pair of edits, with explicit approval

- Why: asking someone to paste two versions again discards context and encourages overgeneralizing one factual correction into a permanent style rule.
- Current evidence: `DiffExtractor.jsx:19-41` assumes AI draft versus published text; `LessonsTab.jsx:66` stores generic `ui-diff` provenance; `content_machine/lessons/differ.py:23-30` infers general rules from edits.
- Proposed interaction: optional “Learn from these edits” opens a comparison of two saved versions of this item, with editable proposed wording and the changed passages beside it.
- Use “Earlier draft” and “Your final edit”; approval/copy is not evidence that someone actually published. Permit pasted versions as a secondary route with explicit origin labels.
- Ask whether the change is a reusable preference or a correction for this item; keep corrections with that item's evidence instead of author-wide instructions.
- How to validate: suggestions stay pending until individually approved; editing or dismissing one preserves both source versions; extraction failure preserves input and allows retry or return to copy/download.

## S3 — Simplify: explicit human activation, conflicts in plain language

- Why: a manually written preference can be approved by an explicit “Save and use” action; AI suggestions need their own decision, and conflicts need resolution before confident success.
- Current evidence: `LessonsTab.jsx:35-41` sends `auto_approve: true` then always reports activation; `content_machine/api/app.py:773-787` can return blocked/conflict outcomes; `ProposalsQueue.jsx:14-24` shows rule IDs/cap jargon.
- Proposed interaction: preview “Use this in future drafts” for manual additions; AI proposals offer Edit, Approve, or Dismiss. Show the actual conflicting preference and offer keep, replace, or cancel.
- Distinguish Saved, Pending review, Already present, Could not save, and Limit reached; never show activation merely because HTTP returned successfully.
- Keep duplicate checks and the cap as safeguards; explain the required action only when hit. Do not make users tune similarity thresholds or merge algorithms.
- How to validate: blocked save keeps typed text and shows no success; conflicting proposal cannot silently replace a preference; double activation does not create duplicates.

## S4 — Add: editable preferences with understandable history

- Why: a preference becomes a burden when the author cannot fix, stop using, or understand it later.
- Current evidence: `RulesLists.jsx:75-82` renders active rule text and provenance only; `content_machine/lessons/store.py:204-228` provides approval/rejection and active/pending reads.
- Proposed interaction: each preference offers Edit and Stop using, with a compact origin link: “Added by you” or “Suggested from [item title], [version pair]”; show dates in details.
- Editing creates a new preference revision; stopping use preserves history. AI-derived edits return to pending until the creator approves the replacement.
- Apply changes to subsequent generation/review requests; existing drafts and approved deliverables remain exact saved versions. Explain if a new run will use changed preferences.
- How to validate: pause one preference, reopen the workspace, and verify it remains inactive; old approved text and the settings used for its generation remain inspectable.

## S5 — Move: author profile into simple, useful Settings

- Why: a creator needs control over what the app knows and how it writes; a codified persona dashboard is too much setup before the first useful draft.
- Current evidence: `ProfileTab.jsx:60-63` edits only current focus/domains; `ProfileTab.jsx:192-252` gives the raw injected Markdown and character count half the page.
- Proposed interaction: Settings contains “About you”, “Writing preferences”, and “Discovery sources”; use clear labels, one Save action per section, and saved/unsaved status.
- About you offers optional name, short factual background, topics, and current focus; voice offers ordinary language guidance plus approved writing examples the author intentionally supplies.
- Begin with empty author fields and neutral writing defaults. Let the creator start from their own notes or draft immediately; offer setup only when it will improve a specific next action.
- How to validate: a new workspace can generate grounded content without completing a profile; a creator can edit their name and voice without finding a repository file.

## S6 — Remove: invented identity, verification badges, and universal personal rules

- Why: fabricated author context corrupts every later draft and makes approval harder; a badge must not imply that profile text was verified.
- Current evidence: `IdentityCard.jsx:35-58` hardcodes initials, a personal fallback, “Verified Persona”, and engineering descriptors; `content_machine/profile/manager.py:14-34,79-92` supplies a particular author's background and beliefs.
- Current evidence: `ProfileTab.jsx:153` reads frontend constant invariants; `ui/src/lib/constants.js:60-85` embeds personal employment/company/tone rules; `InvariantsDisplay.jsx:19-24` claims permanent strict enforcement.
- Proposed interaction: remove synthetic/person-specific fallbacks and the verification badge. Render only saved author data; blank profile shows “Add information about yourself”.
- Separate universal integrity requirements (no invented claims, exact human approval) from optional author choices (company attribution, tone, emoji use); show saved preferences rather than static frontend assertions.
- How to validate: an empty creator account contains no name, employer history, seniority, years of experience, anecdotes, or personal bans; a failed profile load never displays someone else's identity.

## S7 — Move: source configuration behind useful discovery defaults

- Why: source setup is reusable administration; getting an idea and developing it should remain the main task, equally available beside own notes.
- Current evidence: `OracleTab.jsx:16-22` initializes feed URLs and scan parameters in local view state; `OracleTab.jsx:189-198` sends those settings with each scan.
- Proposed interaction: Settings lists the creator's configured sources with name/URL, enabled status, last attempted refresh, and actionable failure; add/edit/disable without deleting saved source evidence.
- Discovery shows which saved sources will be checked and an adjacent “Manage sources” link. No sources offers “Add a source” beside the equally prominent own-idea entry.
- Keep one-time paste/source selection contextual; collapse advanced fetch limits. Saving a source is distinct from checking it; show source failure separately from “No new items”.
- How to validate: a saved source survives reload; invalid URL preserves input; one failed source leaves successful sources usable; third-party material is always attributed as source material, not author experience.

## S8 — Add: a real-data boundary that survives reload and deployment

- Why: editable records are the product; a private creator must never inherit showcase data or lose saved settings when a seed file refreshes.
- Current evidence: `api/index.py:8-27` defaults to demo mode and seeds cold starts; `content_machine/demo_seed.py:7-9,103-107,164-188` creates synthetic persona and active lessons.
- Current evidence: `content_machine/storage/paths.py:38-64` refreshes differing runtime Markdown from repo seeds; `content_machine/profile/manager.py:262-267` writes profile changes to runtime, mirroring seeds only in development mode.
- Proposed interaction: real creator workspaces initialize empty author/work records; optional neutral defaults are visibly product defaults and never claimed as learned or personal.
- Migration preserves historical user records and Comments history; identify/quarantine known demo records by provenance for review rather than mass-deleting ambiguous records. Remove replay fallbacks from real work.
- How to validate: creator A's saved profile, source, preference, draft, and approval survive reload/restart/deploy and are inaccessible to creator B; seed changes cannot overwrite them. Hosted release depends on this, without choosing a vendor.

## S9 — Simplify: truthful loading, errors, and preservation of unsaved work

- Why: “empty”, “failed”, and “saved” require different next actions; silent failure damages confidence and repeated entry wastes the creator's effort.
- Current evidence: `LessonsTab.jsx:19-24,75-88` swallows load/decision errors; `ProfileTab.jsx:37-40,225` refreshes form values from fetched data despite existing unsaved-change detection at lines 102-105.
- Proposed interaction: distinct loading, empty, loaded, and failed states; retry beside the affected section. Approve/dismiss keeps the item visible with a pending state until confirmed, then reports the result.
- Preserve unsaved inputs across Settings/Lessons/Workflow navigation; Refresh must not overwrite edits without a clear discard choice. Save failures keep exact text and retry safely.
- Proposed accessible behavior: associated labels, semantic controls, named icon buttons, announced status/error messages, keyboard-reachable row actions, visible focus, dialog focus return, and linear comparison alternative.
- How to validate: simulate offline load/save/approve, navigate away and back, and operate by keyboard at 200% zoom/320px; input remains intact and failure is never presented as zero preferences or successful activation.

## S10 — Remove: standalone Audio; keep dictation where thoughts become text

- Why: recording is an input method for the creator's actual task, not a destination the creator must visit and transfer work out of.
- Current evidence: standalone Audio retirement and contextual dictation are confirmed requirements in `docs/reviews/2026-11-05-workflow/brief.md:21`; this recommendation does not claim a fresh audio implementation audit.
- Proposed interaction: put “Dictate notes” beside own-note/draft intake; insert editable transcript into the intended input, preserving its source label and existing typed text.
- Show recording/transcribing/error state where the input lives; permission denial returns to usable typing, and cancellation never replaces existing notes with empty text.
- Keep device/model/provider settings out of ordinary author preferences; if required operationally, place diagnostics in advanced support details.
- How to validate: a creator types, dictates, corrects the transcript, develops the draft, skips AI review if desired, approves the exact deliverable, and copies it without a separate Audio step.

## Release priorities and deferrals

- Must-have: S6/S8 truth and durable private records; S9 preservation/errors; S5 usable author editing; S7 real source records; S10 contextual dictation; maintain exact-version approval throughout.
- Must-have if Lessons ships: S1 optional placement, S3 truthful activation, S4 edit/stop using/history. S2 can follow the first reliable publishing workflow without blocking it.
- Defer: raw Markdown editor, semantic-rule dashboards, model/threshold tuning, automatic learning, and mandatory multi-step onboarding; keep a read-only advanced context preview only if it helps diagnosis.
- First-release labels/examples/source suggestions can target engineering creators; expertise and career history must still come from each creator's saved facts.
- No material unanswered product question remains in this scope. Preserve the saved-work-first entry, prominent Resume, and Instagram caption/Reel choices in Workflow rather than adding a second Settings journey.
