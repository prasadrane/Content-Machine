# Editorial workspace behavior

The UI keeps the existing editorial visual identity and offers direct entry to
signal discovery, draft review, and channel adaptation. The optional read-only
sample never grants approval to the operator's working text.

## Session continuity

Oracle, Council, and Distribution mount lazily and remain mounted after their
first visit, hidden when inactive. This is the minimal navigation-continuity seam:
feature settings, interview notes, review results, and generated bundles remain
available without introducing a state-management dependency. Other tools retain
their original unmount behavior.

This does not promise recovery after refresh, browser closure, server restart, or
Vercel cold start. Editorial state is not copied into browser storage. Oracle
clears its LinkedIn cookie when inactive. Inactive interviews hide their portal,
disable recording, and retain notes. A late microphone permission response
releases its stream instead of starting recording in a hidden workspace.

## Approval and request identity

`useSharedFlow` owns production approval. A record identifies the content item,
version, slug, exact text, and operator context. Distribution consumes that record;
its local approval fallback exists only for standalone consumers that omit the
controlled approval prop.

Any actual anchor text or identifier change increments the working version and
invalidates approval, including whitespace and edits back to previous wording.
Selecting a history item creates a new session identity and does not approve it.

Council and Distribution capture request input before generation. Delayed results
retain their original context and cannot overwrite newer editor text. Results for
an older input are labeled accordingly. Council history requests are guarded
against out-of-order responses. Pending confirmation is cancelled when the active
item or version changes.

Revision replacement requires comparing current and proposed wording. Textual
comparison and editorial scores do not verify factual claims. Optional author
notes are session context and are not automatically included in model requests.

## Sample provenance

The cache-stampede seed uses synthetic sources, first-person perspective, and
reviews. Its stored distribution anchor differs from the Council sample draft.
The viewer shows these separately and does not invent a recorded human approval.
Missing sample material is labeled as unavailable.

Replayed derivatives are not generated from custom submitted text. Their input
disclosure says "Submitted input (not the source of this replay)"; the UI does not
claim to know the actual seeded anchor when the response does not include it.

## Validation and remaining release checks

Implementation verification on 2026-11-04: 143 frontend tests passed across 37
files; 266 backend unittest cases passed using Python 3.11.9; the production Vite
build and whitespace diff check passed. The tracked `ui/dist` bundle was rebuilt.
Ten subagents contributed discovery, input fixes, controls, Council integrity,
shared approval, sample entry, Oracle layout, review presentation, Distribution,
and independent integration QA, scheduled under the three-worker limit.

Behavioral coverage includes multiline inputs, native format controls, approval
invalidation, stale reviews/history, delayed generation, original anchor labels,
revision accept/cancel, inactive dialogs/interviews, and microphone cleanup.

Required automated commands:

```text
cd ui
npm test -- --maxWorkers=2
npm run build
```

Run `python -m unittest discover -s tests` from the repository root using the
configured Python environment and isolated test storage. No live model calls are
needed for these checks.

Manual browser checks performed during implementation covered the local Oracle
and Distribution views, explicit approval, whitespace invalidation, navigation
continuity, and no horizontal overflow on the checked Distribution view at the
browser's effective 400 CSS-pixel width. The backend was offline during these UI
checks. Browser automation timeouts prevented a complete manual audit.

Release readiness still requires screen-reader checks, full keyboard walkthrough,
independent 200% text-resize and 320 CSS-pixel reflow checks, measured contrast and
target sizing, and the proposed formative user study. Do not infer these checks
passed from unit tests or a desktop screenshot. No deployment is implied.
