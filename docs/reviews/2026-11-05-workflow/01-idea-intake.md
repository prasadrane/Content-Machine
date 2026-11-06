# Idea discovery, creator intake, and voice review

Date: 2026-11-05. Scope: proposed Workflow stage 1 and current Oracle/source/candidate/archive/interview UI.
Status: AI expert critique and design hypotheses; source review only, with no new browser audit or representative-user research.
Confirmed: private creator workspaces; equally prominent own-idea and discovery starts; one target platform first; optional AI review; mandatory human approval; manual publishing.
The first stage should help a creator choose material and express a point, with the minimum setup needed to continue.

Evidence method: codebase-memory Tier 2; project `C-Users-mamat-Github-Content-Machine`; generation `2026-11-05T15:39:23Z`.
Project, scoped architecture, exact-symbol search, Oracle outbound trace, and interview outline were inspected; returned relevant pages had no continuation.
Coverage checked 20 intake/evidence paths: all `metadata_changed`; SourceCockpit line 253 and InterviewModal line 154 also have `parse_partial` gaps.
Live source was read for those paths, including the flagged lines; recommendations below rely on live source, not graph completeness or historical screenshots.

### I1 — Simplify: give both starts equal weight
**Why:** A creator arriving with an idea needs the same clear entrance as someone seeking inspiration; discovery must not define the whole product.
**Current evidence:** [OracleTab.jsx:15](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:15) initializes scanner/RSS state; [OracleTab.jsx:216](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:216) frames the page entirely around feeds.
**Proposed interaction:** After the platform choice, present two equally prominent choices, proposed copy “Start with my notes” and “Discover an idea”; include “Use an existing draft” as an immediate entry.
**Default:** Neither choice is preselected; own notes opens one editable field with adjacent dictation; discovery opens previously found source material with a scan action.
**Scope boundary:** “Pick a signal” is misleading for a complete draft or personal observation; propose “Start with an idea” for this stage, subject to copy approval.
**Acceptance:** A first-time creator with no configured sources can paste a draft or enter notes and continue without opening source settings or an interview.

### I2 — Add: choose one destination before platform-specific work
**Why:** The creator needs to know what they are making before the system asks for format-specific input or generates text.
**Current evidence:** [OracleTab.jsx:189](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:189) sends source limits without a target platform; [engine.py:61](C:/Users/mamat/Github/Content-Machine/content_machine/interview/engine.py:61) requests a combined “LinkedIn/X style” draft.
**Proposed interaction:** Make one platform the first Workflow decision, using supported brand icons plus text; keep its selection visible across both intake routes and the editor.
**Default:** A saved preference may preselect one platform only when it is visible and editable; label LinkedIn source connections separately from LinkedIn as the output destination.
**Guardrail:** Changing platform preserves raw input and clearly identifies any later generated version as needing its own review and approval.
**Acceptance:** Selecting X and then a GitHub source produces an X-targeted draft; no multi-platform checklist or adaptation request interrupts intake.

### I3 — Move: source maintenance belongs in Settings
**Why:** Returning creators need fresh material without repeatedly inspecting connector syntax, presets, or scan budgets.
**Current evidence:** The cockpit is already collapsed through `compact` ([OracleTab.jsx:260](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:260)); age/cap, configuration badges, and scan controls remain outside that disclosure ([SourceCockpit.jsx:185](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/SourceCockpit.jsx:185)).
**Proposed interaction:** Keep a compact source-status summary, “Find new ideas,” and a contextual “Manage sources” link in discovery; move connector editors and advanced limits to Settings.
**Default:** Suggested feeds are opt-in suggestions, distinct from the creator's configured records; current defaults are component state, not evidence of creator-chosen subscriptions ([OracleTab.jsx:17](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:17)).
**Guardrail:** Remove “Viral Tech Radar” claims and its emoji; its handler replaces the entire feed list rather than adding suggestions ([SourceCockpit.jsx:47](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/SourceCockpit.jsx:47), [RssPane.jsx:33](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/RssPane.jsx:33)).
**Acceptance:** A creator can refresh their chosen sources in one action; editing or adding a source never silently replaces the rest of their configuration.

### I4 — Simplify: use the idea without requiring an interview
**Why:** Choosing useful material should move the creator into writing, with help available when needed.
**Current evidence:** Fresh cards offer direct “Review a draft,” but it inserts a title/link/scaffold ([CandidateCard.jsx:163](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/CandidateCard.jsx:163), [useSharedFlow.js:66](C:/Users/mamat/Github/Content-Machine/ui/src/app/useSharedFlow.js:66)); archive cards only open the interview ([ArchiveView.jsx:179](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/ArchiveView.jsx:179)).
**Proposed interaction:** Use one consistent “Use this idea” action for current and previous discoveries; open an inline editor with the source attached and a short author-context field.
**Default:** “Help me develop this” reveals optional prompts; an existing draft goes directly to editing without a briefing request or regeneration.
**Guardrail:** Keep optional author help separate from the confirmed ability to skip AI Council review; skipping either never implies human approval.
**Acceptance:** The same source item behaves consistently wherever found; a pasted draft remains byte-for-byte intact until the creator edits it or accepts a proposed rewrite.

### I5 — Remove: persona interviews as the default author-context model
**Why:** A creator should be able to express a point without inventing a metric, team incident, or first-person experience to satisfy the form.
**Current evidence:** [BriefingSections.jsx:70](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/BriefingSections.jsx:70) says “Interrogator Personas”; [engine.py:130](C:/Users/mamat/Github/Content-Machine/content_machine/interview/engine.py:130) supplies celebrity personas and questions presuming implementation, metrics, and team friction.
**Proposed interaction:** The shortest useful intake is one field: proposed copy “What is your point or takeaway?”; optional prompts ask what happened, what the creator learned, and what evidence they can share.
**Default:** Accept a reasoned reaction to a source; offer “I have no personal example” without penalty or demands for quantification.
**Guardrail:** Distinguish “my experience” from “my interpretation”; never treat unanswered prompts as permission to fill missing facts.
**Acceptance:** A creator can explain a tradeoff from a public article without being asked to claim they implemented it, measured it, or experienced an outage.

### I6 — Add: preserve source evidence and author contribution separately
**Why:** The creator needs attribution and a clear boundary between what a source says and what they personally know.
**Current evidence:** Cards display `body_snippet`, but the briefing request uses `item.body || item.title` ([InterviewModal.jsx:82](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/InterviewModal.jsx:82)); synthesis completion forwards only draft and slug ([OracleTab.jsx:326](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:326)).
**Proposed interaction:** Attach source identity, URL, available excerpt, retrieval context, author notes, and target platform to the working item; keep these editable as source material rather than mixing them into publishable text.
**Default:** Show a compact source attachment and the creator's own field; label title-only context explicitly when the source body is unavailable.
**Guardrail:** “Grounded draft” must not be a guarantee supplied by a button label; a score or fluent summary does not verify facts or establish personal experience.
**Acceptance:** A distinctive source excerpt survives intake and the next stage; the creator can inspect which source and which personal notes informed the draft.

### I7 — Move: dictation beside the actual field, with honest recording states
**Why:** Voice should reduce typing and preserve thought, with a clear destination and a reliable way to stop.
**Current evidence:** Interview fields already append transcripts ([InterviewModal.jsx:40](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/InterviewModal.jsx:40)); the fallback clears `recordingTarget` before transcription, while field buttons require that target to display “Transcribing” ([useVoiceRecording.js:185](C:/Users/mamat/Github/Content-Machine/ui/src/hooks/useVoiceRecording.js:185), [BriefingSections.jsx:183](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/BriefingSections.jsx:183)).
**Proposed interaction:** Reuse field-adjacent “Dictate” / “Stop” controls in notes and draft intake, with visible recording, processing, error, and editable-transcript states.
**Default:** Show the processing path accurately: current speech recognition and recorded-audio/backend paths differ ([useVoiceRecording.js:118](C:/Users/mamat/Github/Content-Machine/ui/src/hooks/useVoiceRecording.js:118)); private workspace does not establish fully local transcription.
**Guardrail:** Preserve typed text; prevent overlapping recordings and late transcripts entering another item; retain the current inactive-workspace microphone cleanup.
**Acceptance:** Permission denial leaves typing usable; stopping a recording shows processing until completion; returned text lands only in its originating field and can be corrected before generation.

### I8 — Simplify: one discovery list, with filters disclosed when useful
**Why:** Creators need to recognize a promising idea before learning a taxonomy or deciding which system list to inspect.
**Current evidence:** There are scanner/archive views with automatic archive selection on initial results ([OracleTab.jsx:84](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:84)); archive foregrounds verdict ranges and “Content Topic Taxonomy” ([ArchiveView.jsx:45](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/ArchiveView.jsx:45)).
**Proposed interaction:** Combine fresh and previous discoveries under discovery, with search, a clear refresh result, and optional Filters; keep work-in-progress history separate from ingested source history.
**Default:** Lead with title, source/date, readable excerpt, and “Use this idea”; retain collapsed score details, with editorial recommendations labeled as suggestions rather than approval or fact checks.
**Guardrail:** Do not rename every ingested row “Saved ideas”; current rows are scan history. Remove emoji decoration and missing-verdict fallback to “PASS” ([topics.js:3](C:/Users/mamat/Github/Content-Machine/ui/src/lib/topics.js:3), [CandidateCard.jsx:84](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/CandidateCard.jsx:84)).
**Acceptance:** A small set is readable without a wall of chips; filters can be cleared in one action, and source history cannot be confused with the creator's draft history.

### I9 — Add: distinct empty, partial, failed, and complete discovery states
**Why:** A creator needs to know whether to wait, retry, edit sources, clear filters, or begin with their own idea.
**Current evidence:** Archive errors only reach the console ([OracleTab.jsx:91](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:91)); any nonloading empty batch with progress gets a threshold explanation, including error progress ([CandidateStream.jsx:88](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/CandidateStream.jsx:88)).
**Proposed interaction:** Separate no configured sources, never scanned, no new items, no matches, below recommendation threshold, partial connector failure, and failed scan; provide one useful next action for each.
**Default:** Keep previous results and partial successes visible with timestamp/status; show compact “Checking sources” / “Ranking ideas” progress instead of SQLite, zero-token, gate/margin, and fabricated-looking percentage mechanics.
**Guardrail:** A new scan currently clears candidates immediately ([OracleTab.jsx:117](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:117)); retry must not erase usable material or label a service failure as an editorial rejection.
**Acceptance:** A failed source fetch says which source failed and permits retry or own-note entry; an archive load failure never appears as an empty successful result.

### I10 — Remove: successful-looking briefings and synthesis after provider failure
**Why:** The creator needs to distinguish an actual source-based result from generic help or their unchanged notes.
**Current evidence:** [engine.py:124](C:/Users/mamat/Github/Content-Machine/content_machine/interview/engine.py:124) returns a generic summary and invented tension as a normal briefing; [engine.py:208](C:/Users/mamat/Github/Content-Machine/content_machine/interview/engine.py:208) returns an input-based template when synthesis has no output.
**Proposed interaction:** Return explicit unavailable/partial status; show “Briefing unavailable” with source material and usable notes; offer generic writing prompts only as labeled optional help.
**Default:** If drafting fails, preserve the source and input, explain that generation failed, and offer retry or continue editing the notes.
**Guardrail:** Never substitute a seeded sample, unrelated replay, generic conflict, or invented anecdote for a creator's result; do not call a title-only template a completed AI draft.
**Acceptance:** With the provider unavailable, no confident source summary or tension appears; the creator retains all original text and can continue manually to mandatory approval.

### I11 — Add: preserve work through closing, switching, and continuing
**Why:** Creators must be able to pause a thought or change direction without losing it or replacing another draft silently.
**Current evidence:** Notes live in interview component state; close removes that component, and manual skip forwards only the source item ([InterviewModal.jsx:26](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/InterviewModal.jsx:26), [OracleTab.jsx:325](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:325), [OracleTab.jsx:334](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/OracleTab.jsx:334)).
**Proposed interaction:** Own intake in the working item rather than a disposable modal; continuing manually carries notes and attachments; selecting a different source offers add-to-current or new-item intent.
**Default:** Save private work with visible save status only after durable storage succeeds; until implemented, state session-only limits and provide an export or leave-with-unsaved-work warning.
**Guardrail:** Preserve current late-completion handling ([InterviewModal.jsx:219](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/InterviewModal.jsx:219)); bind asynchronous results to item/version and do not navigate a different current item on completion.
**Acceptance:** Closing optional help and reopening preserves notes; a draft completed elsewhere can be opened deliberately; refresh recovery is promised only after private ownership and storage have been verified.

### I12 — Keep: accessible controls and shared editorial styling
**Why:** Intake must be usable by keyboard, screen reader, and at narrow widths while a creator concentrates on their idea.
**Current evidence:** The interview has a dialog label, focus handling, and Escape support ([InterviewModal.jsx:56](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/InterviewModal.jsx:56)); question textareas and raw-note labels lack explicit label association ([BriefingSections.jsx:146](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/BriefingSections.jsx:146), [BriefingSections.jsx:175](C:/Users/mamat/Github/Content-Machine/ui/src/components/oracle/BriefingSections.jsx:175)).
**Proposed interaction:** Keep `cm-*` styling, semantic buttons, and focus restoration; explicitly label every field and icon-only action, expose selected states, and announce meaningful recording/result/error changes.
**Default:** Use professional outline icons for actions and topics, platform brand icons plus text, and textual statuses that do not depend on color or animation.
**Guardrail:** Optional-help Escape/close behavior must follow I11 preservation; a source error inside collapsed settings must be surfaced with a direct route to the affected field.
**Acceptance:** Complete own-note and discovery starts by keyboard; verify focus after selection/help closure, screen-reader field names/statuses, 200% zoom, and 320px reflow during implementation.

Must-have before release: I1/I2 equal starts and one platform; I4/I5 minimal optional context; I6 provenance; I7 safe dictation; I9/I10 truthful outcomes; I11 private preservation and owned handoffs.
Simplify in the same pass: source maintenance, duplicate discovery navigation, taxonomy/score noise, jargon, and emoji; do not preserve controls merely because they map to existing modules.
Defer: more connector types, celebrity interviewer selection, custom ranking dashboards, advanced taxonomy management, and adaptation choices before the first finished piece.
Remaining material question: should returning creators see a saved-work list or resume the latest item? Either choice needs an explicit new-item route and private durable work records.
Validation proposal: exercise own notes, existing draft, and discovered source through editing, optional AI-review skip, exact-text human approval, and copy/download; validate failures and preservation at every handoff.
No product code, data, browser interaction, live model calls, or publication was changed by this review; acceptance scenarios are proposed checks, not measured results.
