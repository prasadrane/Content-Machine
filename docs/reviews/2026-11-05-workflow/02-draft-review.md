# Draft development and useful review

Date: 2026-11-05. Planning only; AI expert critique, not a browser audit or user study.
Scope: stage 2 and its intake, approval, and export handoffs. Labels below are proposed copy.
Confirmed: private creator workspaces, equal own-idea/source entry, one platform first,
explicitly skippable AI review, mandatory human approval, and manual publishing.
Evidence: Tier 2 graph discovery plus live source; coverage generation 2026-11-05T15:39:23Z.
All 19 checked paths were `metadata_changed`; live source was read, including the `InterviewModal.jsx:154` parse gap; no pagination remains.
The findings below describe observed code; proposed behavior and acceptance scenarios are unmeasured.

## D1 — Add: a real draft-development step before review

- Why: someone bringing an idea needs help forming a post before judging its prose.
- Current evidence: `ui/src/components/council/DraftingStudio.jsx:82-89` expects a draft;
  `ui/src/app/useSharedFlow.js:66-70` sends source text plus “Draft content goes here...”.
  Generation exists in `ui/src/components/oracle/InterviewModal.jsx:106-127`, outside this editor.
- Proposed interaction: stage 2 has one working draft, with “Create draft” for notes/source
  intake and direct editing for an existing draft. Carry both stage-1 entry routes here equally.
  Ask for the author's intended point only when missing; keep optional interview prompts inline.
- How to validate: all three intake routes reach an editable draft without another destination, manual field copying, or placeholder review.

## D2 — Add: item-specific source and author context in every writing request

- Why: notes are useful only if they constrain the draft; a third-party event is not the author's experience.
- Current evidence: `DraftingStudio.jsx:17-19,91-100` stores three local note fields and explicitly
  excludes them from requests; `useCouncilSession.js:65` sends only draft, slug, and iteration count.
  General style, voice, and governed rules DO reach revisions (`content_machine/council/loop.py:355-364`),
  and interview synthesis uses answers/notes (`content_machine/interview/engine.py:177-188`).
- Proposed interaction: keep a compact editable evidence panel with source URL/excerpts, direct
  experience, and interpretation. Send these typed fields and their revisions to generation/revision;
  show what context will be used. Permit attributed commentary when there is no personal experience.
- How to validate: inspect mocked requests for all three fields; a source-only scenario cannot
  silently become a first-person anecdote. Missing evidence produces a question or an explicit gap.

## D3 — Add: the chosen platform as part of the draft contract

- Why: publishable LinkedIn copy, an X thread, and a video script are different deliverables.
- Current evidence: `content_machine/api/app.py:155-158` has no platform in Council input;
  `useCouncilSession.js:91` hardcodes `linkedin_post` and `pragmatic_architect` for polishing.
  Initial synthesis requests generic “LinkedIn/X style” (`content_machine/interview/engine.py:59-73`).
- Proposed interaction: keep platform/title visible above the editor; apply that platform's structure,
  limits, and preview during development. Use configured author preferences rather than a fixed persona.
  A platform change creates an explicitly unapproved adaptation; later export preserves this artifact.
- How to validate: each supported platform reaches approval with its actual format and constraints;
  switching platform never inherits another platform's review or approval, even when text matches.

## D4 — Simplify: feedback should name the next useful edit

- Why: creators need to decide what to change, not operate a council simulation.
- Current evidence: `VerdictPanel.jsx:13-25` already leads with actions and hides scores, worth keeping;
  `content_machine/council/loop.py:157-165` prefixes actions with internal judge slots.
  `DraftingStudio.jsx:59-79,116` exposes “Single Pass”, “Full Loop”, and estimated execution time.
- Proposed interaction: default to “Review draft”; put processing options in secondary settings.
  Group overlapping feedback by the actual issue and show an excerpt plus a concrete suggestion.
  Keep judge attribution/details and differing opinions available; flag facts needing checking. Authors can edit, request revision, or decline advice.
- How to validate: feedback has a clear target and next action without decoding judge names;
  no request is described as a rewrite when it only reviews (`loop.py:347-364`).

## D5 — Move: score competition and technical story identity into details/history

- Why: the author's chosen version matters more than winning a numerical leaderboard.
- Current evidence: `CouncilTab.jsx:37-104` puts a trophy, three-decimal peak, and three actions first;
  `DraftingStudio.jsx:28-53` exposes the slug and recent peak scores; `HistoryTimeline.jsx:24-35`
  emphasizes scores/PEAK. Current API may return normalized score (`content_machine/api/app.py:601-602`),
  while history returns raw score (`app.py:654-655`); `VerdictPanel.jsx:24-25` presents them together as /10.
- Proposed interaction: show an editable human title; manage IDs internally. Put versions in one
  history entry point labeled by date, origin, and review state. Scores are optional diagnostics with
  their basis and scale; remove PASS/PEAK prestige treatment and incomparable score comparisons.
- How to validate: a new author can edit/review/continue without seeing a slug or score;
  raw and normalized results are never compared or rendered as the same /10 measurement.

## D6 — Simplify: one optional wording revision, without claims of “humanity”

- Why: repeated polishing controls create competing drafts and encourage metric chasing.
- Current evidence: peak polishing (`CouncilTab.jsx:77-90`) duplicates current wording polish
  (`VerdictPanel.jsx:30`). `HumanizedDraftCard.jsx:19-26,60-74` displays burstiness, a fixed persona,
  decorative emoji, and “Purged AI Clichés”. Rewrite failure silently falls back to sanitizing
  (`content_machine/humanize/transformer.py:87-102`), without a result field describing that failure.
- Proposed interaction: retain a single “Suggest wording changes” beside the active draft, followed
  by comparison. Remove burstiness/persona badges and magic language. Report rewrite failure or
  local cleanup honestly; do not treat cadence or banned-word removal as authenticity verification.
- How to validate: one wording action exists per active draft; model failure preserves input and
  reports the actual outcome. Proposed text cannot carry forward the original version's approval.

## D7 — Keep: deliberate revision comparison, with exact provenance

- Why: the author must see what a rewrite changes before accepting claims or losing their wording.
- Current evidence: `RevisionComparison.jsx:6-18` gives linear current/proposed text and explicit choices;
  `CouncilTab.jsx:128-135` guards acceptance against changed text/slug. Council sanitizes after scoring
  (`content_machine/council/loop.py:332-350,366-376`), so returned text can differ from scored text.
- Proposed interaction: retain full-text reading order; add accessible text diff emphasis and identify
  source, base version, and proposed version. Include sanitizer changes. Accepting creates a new version;
  keep the previous wording recoverable. Comparison is an editing aid, never a fact-verification badge.
- How to validate: cancel changes nothing; acceptance preserves the old version; a newly added number,
  employer, attribution, or negation is visible; changed text never inherits a review of different bytes.

## D8 — Keep: asynchronous ownership; simplify progress and failure recovery

- Why: a long request must not take ownership away from an author who continues editing.
- Current evidence: `useCouncilSession.js:33-42,57-74,84-96` snapshots requests, guards history,
  retains previous results, and labels older results; `CouncilTab.jsx:189-200` explains this.
  Demo request failures can return unrelated seeded reviews (`content_machine/api/app.py:574-593`).
- Proposed interaction: keep editing available; show the submitted version/platform and a truthful
  “Reviewing…” status without an unverified time promise. Late results offer comparison with their
  original version. On failure retain text/context and offer retry or explicit skip; remove replay fallback.
- How to validate: edit, change item/platform, or leave during a delayed request; the response cannot
  overwrite current work, mark it reviewed, or approve it. Failed requests never show sample success.

## D9 — Move: dictation beside notes and draft editing

- Why: speaking is an input method, and the transcript needs the same editorial control as typing.
- Current evidence: `InterviewModal.jsx:38-53` appends transcripts into notes/answers;
  `ui/src/hooks/useVoiceRecording.js:185-203` also delivers asynchronous backend transcripts.
- Proposed interaction: add labeled dictation controls beside the intended field, with start/stop,
  recording/transcribing status, and editable transcript before insertion. Snapshot item, version,
  field, and insertion point; a late transcript offers insertion into its original context, not new work.
- How to validate: keyboard-only start/stop, denied permission, empty audio, edits during transcription,
  and item changes preserve all typed text; inactive stages stop recording and release the microphone.

## D10 — Move: approval to its dedicated stage; make AI-review skip explicit

- Why: optional machine advice and mandatory author sign-off are different decisions.
- Current evidence: `VerdictPanel.jsx:7,33` exposes approval only after a result; peak approval is another
  route (`CouncilTab.jsx:92-100`). `ApprovalGate.jsx:18-31` already shows exact text and requires consent,
  but calls any non-pass an override. `ui/src/app/useSharedFlow.js:16-36,74-78` invalidates edits.
- Proposed interaction: use “Continue to approval” and explicit “Skip AI review” from the active draft.
  Record skipped/failed/earlier review honestly, with no fabricated score/pass or “overriding judges” claim.
  Stage 3 approves exact content, item, version, and platform; any later edit/adaptation requires approval.
- How to validate: an authored draft can skip every AI review and still requires human confirmation;
  editing then restoring the same text cannot revive approval. Export equals the approved artifact.

## Required changes, deferrals, and remaining decision

- Must have: D1-D3 grounding/platform contract; D7-D8 ownership; D10 skip plus exact approval;
  remove duplicate polish/score prestige/sample fallback; provide field-level voice input and honest errors.
- Empty state: explain the next action from real intake; no generated experience, sample verdict, or peak.
  Session notes are local React state (`DraftingStudio.jsx:17-19`); history is not complete draft recovery.
- Defer advanced change merging, automatic fact checking, expanded tone taxonomies, and judge dashboards.
- Durable private recovery needs persisted drafts, context, versions, and review/approval records before
  promising refresh/restart recovery. Return landing (resume latest versus saved-work list) remains undecided.
