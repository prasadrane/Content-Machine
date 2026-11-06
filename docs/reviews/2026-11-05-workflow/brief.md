# Workflow product review brief

Date: 2026-11-05. Status: design review only; do not implement product changes.

## User and job

A creator wants to get ideas, develop them using their own perspective, and leave
with content they can publish. Evaluate the app as one product, not a collection
of internal subsystems. For every view ask: why does it exist, what user problem
does it solve, how does the current UI solve it, and what simpler approach would
help the creator? Challenge unnecessary views and controls.

## Confirmed requirements

- One primary Workflow destination incorporating four stages: Pick a signal,
  Council review, Approve, Distribute. Renaming is a proposal, not accepted copy.
- Supporting destinations: Lessons and Profile/Settings. Three top-level buttons
  is the current interpretation, not an explicit user decision about the count.
- Choose one platform first; optional adaptations afterward (user confirmed).
- Finish with copy/download for manual publishing (user confirmed).
- Remove the standalone Audio view. Put dictation beside actual text intake.
- Remove workflow-guide show/hide controls, competing tool navigation, demo noise.
- No decorative emoji in UI. Use professional outline icons for actions/topics,
  recognizable brand icons plus text for supported platforms.
- Actual, editable, configurable records; remove synthetic seed scores, reviews,
  persona, invented anecdotes, and unrelated sample replay fallbacks. Empty and
  failed states must be truthful. Real third-party sources are not author experience.
- Keep the shared warm editorial cm-* theme, human approval, source grounding,
  async ownership, revision comparisons, and exact-version approval integrity.
- Comments stays retired. Do not delete historical user data.
- User answers received during review: each creator has a PRIVATE workspace;
  own ideas and discovery are EQUALLY prominent; AI review can be explicitly
  SKIPPED while human approval remains required. These override earlier open
  questions. Do not plan a public showcase or team collaboration as the default.
- Further CONFIRMED user answers: Workflow opens to saved ideas and drafts with
  a prominent Resume action; Instagram first release needs captions AND Reel
  scripts; first-release audience is technical/engineering creators.

## Candidate design to critique

Workflow / Lessons / Settings. A compact progress strip and a single active stage,
not all former pages stacked vertically. Platform/title/current work remain visible.
Stage 1 accepts sourced idea, own notes/voice, or existing draft. Stage 2 develops
and reviews the target platform content. Stage 3 previews and approves the exact
deliverable. Stage 4 copies/downloads that content without silently rewriting it.
An adaptation creates a new version/branch needing its own review/approval.
History is available inside Workflow. Lessons is optional, also reachable after
completion. Profile/preferences/source configuration belong in Settings.
Durable recovery is proposed, not implemented; do not promise it without storage.

## User answers

1. CONFIRMED: each creator has a private workspace. Authentication, ownership,
   and durable storage are prerequisites for a hosted release with real drafts.
2. CONFIRMED: own idea/notes and configured-source discovery equally prominent.
3. CONFIRMED: allow explicit skip of AI Council review, retain human approval.
4. CONFIRMED: saved ideas/drafts first, with a prominent Resume action.
5. CONFIRMED: Instagram captions AND Reel scripts in the first release. These
   are planned capabilities, not currently implemented generic-script support.
6. CONFIRMED: technical/engineering creators first.

All six questions above are answered. Distinguish
observed source facts, user requirements, design hypotheses, and measured results.

## Evidence packet and graph handoff

Repo: C:/Users/mamat/Github/Content-Machine. Main was clean at start.
Read applicable AGENTS.md. Codebase-memory skill already applied by coordinator.
Tier: 2 verification. Project: C-Users-mamat-Github-Content-Machine.
Graph generation: 2026-11-05T14:43:29Z. list_projects found it; get_architecture
scoped ui/src found the React entry point and domain clients. Search for exact
names App, OracleTab, CouncilTab, DistributeTab, LessonsTab, ProfileTab,
useSharedFlow, useVoiceRecording, ApprovalGate returned 11 rows, has_more=false.
Qualified names use <project>.ui.src.components.<folder>.<file>.<function>.
App is <project>.ui.src.App.App; useSharedFlow is
<project>.ui.src.app.useSharedFlow.useSharedFlow.
App outbound trace depth 1: useSharedFlow, useServerHealth, tabs.getProps,
SampleStory, DemoBanner, TabBtn, WorkspaceEntry; 7 total, no continuation.
useSharedFlow snippet read in full; parent also read live App.jsx, tabs.js,
useSharedFlow.js, current docs/ui-workspace.md, docs/ui-style-system.md,
ARCHITECTURE.md, spikes/RESULTS.md and the prior Nov 4 UX plan.

Coverage checked for App.jsx, app/tabs.js, app/useSharedFlow.js,
components/{oracle/OracleTab,council/CouncilTab,distribute/DistributeTab,
approval/ApprovalGate,lessons/LessonsTab,profile/ProfileTab,DemoBanner,
audio/AudioTab}.jsx, lib/constants.js, api/index.py, content_machine/demo_seed.py.
All are metadata_changed; direct source fallback is required before using them.
AudioTab also has a parse_partial gap at line 11. No pagination remains.
For additional structural paths, follow skill graph discovery and coverage before
claiming structural facts. If tools unavailable, read exact live sources and state
that limitation. Do not claim fresh graph coverage from this handoff.

## Reviewer operating rules

- You are not alone in the codebase. Do not revert others' work.
- Own only your assigned Markdown report. No code changes, commits, external
  messages, live model calls, or further subagents. Root owns the final plan.
- Source-based review; no new browser audit or user study has been performed.
- Read relevant live source and give tight repo path/line references for material
  current-state observations. Do not treat existing plans as current behavior.
- Keep reports focused (roughly 100-140 lines). Prefer specific removals, defaults,
  decision points, and acceptance scenarios over generic principles or new tools.
- Use a finding ID per recommendation and label it Keep / Simplify / Move / Remove
  / Add. Include Why, Current evidence, Proposed interaction, and How to validate.
- Include failure/empty/resume states, grounded content, input preservation,
  accessible operation, and end-to-end handoffs in your owned scope.
- End with must-have changes, deferrals, and only material unanswered questions.
- Reports are AI expert critique, not research with representative users.

## Whole-product reviewer assignment protocol

After all five specialist reports exist, read ALL of 01-idea-intake.md,
02-draft-review.md, 03-approve-export.md, 04-navigation-recovery.md and
05-lessons-settings.md, this brief, and ../../ui-workflow-plan.md.
Review the combined experience from beginning to manual publishing, not just
the lens named in your assignment. Reviewers 06-10 work independently; do not
anchor on another whole-product report before writing your own.

Own only your assigned report. Use IDs P1..., A1..., T1..., U1..., or R1... as
assigned. Target 80-110 lines. Reference specialist finding IDs for traceability;
read exact source only to resolve material doubts, and follow graph coverage
rules if you conduct new structural exploration. Trust inspected specialist
evidence otherwise rather than repeat their audit.

Required output: (1) a product verdict, (2) keep/change/reject/defer decisions
across all five scopes, (3) the most important cross-view contradictions and a
concrete resolution, (4) the smallest complete coherent journey and release
boundary, (5) end-to-end acceptance scenarios, (6) only unresolved product
questions that matter to the creator. Do not merely concatenate findings or
approve all suggestions. Reduce complexity as well as proposing safeguards.

The coordinator will reconcile all five holistic reports into the final plan,
record disagreements and disposition, and keep implementation separately gated.
