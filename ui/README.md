# Content Machine UI

Minimalist React + Vite + Tailwind CSS single-page application for the Content Machine editorial engine.

## Core Philosophy & Rationale
> **SOLID Modularization**: Decomposed from a monolithic 5,125-line component into single-responsibility feature slices, typed API gateways, domain hooks, and an Open-Closed tab registry with a declarative 65-line root shell.

---

## Directory Structure

```
ui/
├── src/
│   ├── App.jsx                     # Declarative root orchestrator shell (≤70 lines)
│   ├── main.jsx                    # Vite entrypoint
│   ├── index.css                   # Global styles & Tailwind directives
│   ├── app/                        # App-level registry & orchestration
│   │   ├── tabs.js                 # OCP tab registry (id, label, Component, getProps)
│   │   ├── useServerHealth.js      # Server health polling hook
│   │   └── useSharedFlow.js        # Cross-tab workflow transitions (Oracle -> Council -> Distribute)
│   ├── api/                        # Typed API gateway clients (zero raw fetch elsewhere)
│   │   ├── client.js               # fetchJson & HTTP error utilities
│   │   ├── sse.js                  # streamSSE server-sent event reader
│   │   ├── health.js               # /api/health endpoint
│   │   ├── oracle.js               # /api/oracle/scan and /api/oracle/history
│   │   ├── council.js              # /api/council and /api/council/history
│   │   ├── interview.js            # /api/interview/brief and synthesize
│   │   ├── linkedin.js             # /api/linkedin/status and sync
│   │   ├── profile.js              # /api/profile endpoint
│   │   ├── comments.js             # /api/comments endpoint
│   │   ├── audio.js                # /api/transcribe and /api/mic/status
│   │   ├── lessons.js              # /api/lessons endpoint
│   │   └── distribute.js           # /api/distribute endpoint
│   ├── hooks/                      # Shared reusable UI hooks
│   │   ├── useCopyToClipboard.js   # Clipboard copy with status state
│   │   └── useVoiceRecording.js    # Web Speech API dictation with ASR fallback
│   ├── lib/                        # Domain constants & pure utility functions
│   │   ├── constants.js            # Voice invariants, tones, dimension labels
│   │   └── topics.js               # Topic taxonomy badges & formatting
│   └── components/                 # Feature components (<300 lines each)
│       ├── ui/                     # Shared presentational primitives (TabBtn)
│       ├── oracle/                 # Subsystem 1: Oracle feature
│       │   ├── OracleTab.jsx       # Orchestrator
│       │   ├── SourceCockpit.jsx   # Tabbed source configuration form
│       │   ├── RssPane.jsx         # RSS feeds and presets
│       │   ├── GithubPane.jsx      # GitHub repository feeds
│       │   ├── LinkedinPane.jsx    # LinkedIn engine configuration
│       │   ├── CandidateStream.jsx # Active scored stream & triage
│       │   ├── CandidateCard.jsx   # Candidate card with micro-scores
│       │   ├── ScanProgressHUD.jsx # 3-phase stepper and live metrics
│       │   ├── TriageToolbar.jsx   # Active batch search, sort, topic chips
│       │   ├── ArchiveView.jsx     # Historical feed archive and explorer
│       │   ├── InterviewModal.jsx  # Topic briefing modal
│       │   ├── BriefingSections.jsx# Interview modal sections
│       │   └── presets.js          # Default feed & profile presets
│       ├── council/                # Subsystem 4: Writer's Council
│       │   ├── CouncilTab.jsx      # Orchestrator
│       │   ├── DraftingStudio.jsx  # Draft editor and controls
│       │   ├── VerdictPanel.jsx    # Scorecards, radar, revision review
│       │   ├── HistoryTimeline.jsx # Historical draft reviews
│       │   └── HumanizedDraftCard.jsx # Formatted draft view
│       ├── distribute/             # Subsystem 6: Derivative Formats
│       │   ├── DistributeTab.jsx   # Orchestrator
│       │   ├── AnchorForm.jsx      # Post input and platform toggles
│       │   ├── OutputPreviews.jsx  # Generated outputs for X, Video, etc.
│       │   └── PlatformConfigModal.jsx # Per-platform customization
│       ├── commenting/             # Comment Generation
│       │   ├── CommentingTab.jsx   # Orchestrator
│       │   ├── InputPanel.jsx      # Post text and tone selection
│       │   ├── PolishCard.jsx      # Polish card with alternatives
│       │   └── CommentsHistory.jsx # Past generated comments
│       ├── lessons/                # Subsystem 5: Governed Lessons Store
│       │   ├── LessonsTab.jsx      # Orchestrator
│       │   ├── RulesLists.jsx      # Active codified rules
│       │   ├── ProposalsQueue.jsx  # Pending rule proposals
│       │   ├── DiffExtractor.jsx   # Diff analysis input
│       │   └── CustomRuleCard.jsx  # Rule card presentational
│       ├── audio/                  # Subsystem 2: Voice & ASR
│       │   └── AudioTab.jsx        # Int8 faster-whisper transcription
│       └── profile/                # Profile & Voice Persona
│           └── ProfileTab.jsx      # Author voice persona and invariants
├── package.json
└── vite.config.js
```

---

## Architectural Rules

1. **Strict Dependency Inversion**: Zero raw `fetch()` calls outside `ui/src/api/`. All components consume typed domain API functions.
2. **Open-Closed Tab Registry**: New tabs are added to `ui/src/app/tabs.js` with their corresponding props selector without modifying `App.jsx`.
3. **File Size Budget**: Target ≤300 lines/file; hard cap 350 lines (orchestrators only). Root `App.jsx` ≤120 lines.
4. **Offline Testability**: All unit test suites run 100% offline with zero external network access.

---

## Development Commands

```powershell
# Install dependencies
npm install

# Start Vite development server (proxies /api to http://127.0.0.1:8080)
npm run dev

# Run full Vitest suite (19 test suites, 57+ tests)
npm test

# Run tests in watch mode
npm run test:watch

# Compile production bundle to ui/dist
npm run build
```
