# Workflow review record and product decisions

Date: 2026-11-05. Status: ten-agent design review complete; implementation not started.
Canonical proposal: [creator workflow plan](../../ui-workflow-plan.md).

## Review method

Five specialists owned different views. Five new independent reviewers then read
all five specialist reports, the shared brief and the candidate plan, and judged
the complete creator journey. The coordinator reconciled their advice into the
canonical proposal. Three children ran at most concurrently, in batches. No child
spawned additional reviewers. Individual findings are recommendations, not votes
or evidence of user-observed behavior.

| Reviewer | Owned perspective | Report |
| --- | --- | --- |
| 01 | Discovery, author intake and voice | [Idea intake](01-idea-intake.md) |
| 02 | Draft development and useful AI review | [Draft/review](02-draft-review.md) |
| 03 | Approval, platform deliverables and manual export | [Approve/export](03-approve-export.md) |
| 04 | Navigation, returning work and recovery | [Navigation/recovery](04-navigation-recovery.md) |
| 05 | Lessons, author settings and real records | [Lessons/settings](05-lessons-settings.md) |
| 06 | Whole-product customer value and scope reduction | [Product value](06-product-value.md) |
| 07 | Whole-product UX architecture and coherence | [Experience coherence](07-experience-coherence.md) |
| 08 | Whole-product editorial trust and private data integrity | [Trust/integrity](08-trust-integrity.md) |
| 09 | Whole-product inclusive first-time/returning creator experience | [Inclusive creator](09-inclusive-creator.md) |
| 10 | Whole-product scope, engineering feasibility and delivery | [Delivery feasibility](10-delivery-feasibility.md) |

## User answers incorporated during review

| Decision | Confirmed answer | Consequence |
| --- | --- | --- |
| Access | Each creator has a private workspace | Hosted authentication/ownership and durable records are release requirements |
| Starting material | Own ideas and discovery equally prominent | Two equal entry choices; no source-first default |
| AI review | Allow an explicit skip | Human approval required; no score/pass gate or automatic skip on failure |
| Returning | Saved ideas/drafts with prominent Resume | List landing outside the active-item stage strip; no forced auto-resume |
| Instagram | Captions and Reel scripts | Two real selectable formats, not a generic video prompt with a logo |
| Audience | Technical/engineering creators first | Focused wording/source suggestions without inventing individual expertise/history |

Earlier user decisions also remain: one platform first, optional adaptations later,
copy/download for manual publishing, four workflow stages, no Audio destination,
professional action icons and platform logos, actual editable content and no fake
demo data. Comments remains retired.

Reports 01-04 were finished before the last three answers arrived. Their remaining
questions are historical; the updated brief and canonical plan supersede them.
Do not ask these six questions again or treat those reports as overruling answers.

## Coordinator dispositions

| Issue / source findings | Disposition | Concrete product result |
| --- | --- | --- |
| Four stages vs a compulsory wizard (N2, P1/P8, A1, U2, R1) | Keep stages; reject mandatory visits | One active region; existing/resumed drafts enter the appropriate state; actions depend on real prerequisites |
| Saved list vs platform-first (I2, N3/N8, A2/A3, R2) | Resolve | Workflow opens saved work; only New content asks destination/format |
| Repeated context intake (I4-I6, D1-D3, P2/P3, A4, T3) | Merge | One source/author context record used by actual writing requests, one working editor, optional prompts |
| Anchor approval then rewriting (D10, E1-E3, P4/P5, A6, T5/T6, R4/R6) | Replace boundary | Finish actual format before approval; export exact approved artifact with no model calls |
| Extra checkbox/modal acknowledgment (E3 vs P4/A6/T5/U5) | Simplify | One explicit version-bound approval action and clear consent statement; no repeated attestation |
| Optional AI vs failed/past reviews (D7/D8/D10, A5, T4/T5, U4, R4) | Keep distinct | Explicit skip is normal; failure stays recorded; changed text cannot borrow earlier review or approval |
| Writing rules in Lessons and Settings (S4/S5 vs P7/A7/U10/R8) | One home | Lessons owns one editable preference collection; Settings links to it and owns factual profile/sources |
| Lower public platform count (P9, T10 vs R5) | Do not adopt without user approval | Use a thin internal LinkedIn/Instagram sequence, retain current format capabilities/history and add both Instagram formats before the redesigned release |
| Caption plus Reel compulsory package (E4/E8, P8, A3, T6, U9) | Reject compulsory bundle | Either format is independently selectable; another format is optional linked unapproved work |
| Branch data vs complex branch UI (N4, E8, P5/P8) | Keep lineage; defer tree | Linked adaptation with independent versions/approval and preserved original export |
| Profile/identity defaults and learned rules (S5/S6/S8, T8/T9) | Replace | Optional saved facts, labeled neutral defaults, no invented persona/Verified badge or universal personal history |
| Real editable data vs seeds/replay/overwrite (I10, E7/E9, S8, P6, T7/T8, R7) | Release gate | Private durable owned records; non-destructive migration, synthetic quarantine, no fake-success fallback, no seed overwrite |
| Scale/score/cleanup mismatch (D5/D7, T4) | Correct; de-emphasize | Useful advice first; version-linked actual review, explicit diagnostic scale; never factual verification |
| Learn-from-edits as another phase (S1/S2 vs P7/A10/U10/R8) | Defer inference | Basic optional preference editing ships; future actual-version suggestions remain human-approved; no fifth stage |
| Accessibility and recovery (I7/I9/I11/I12, N5-N13, U6-U8, R9/R11) | Cross-cutting acceptance | Field-level dictation, safe pending results, truthful saves/errors, keyboard/screen-reader and resize/reflow checks throughout |

These dispositions retain user requirements while declining individually plausible
features that would duplicate decisions or expand scope. Proposed labels are Idea,
Draft & review, Approve, Export; Workflow / Lessons / Settings is the recommended
navigation, not an invented explicit user decision about the exact button count.

## Implementation boundary

Plan first: shared ownership/item/version/context/artifact/review/approval contracts,
retained capability inventory and migration plan. Prove one internal complete local
slice, then parallelize owned shell/intake, writing/adapters, approval/export and
supporting-view work. Centralize shared writes. All promised formats and private
hosted gates precede the redesigned public release.

No auth/storage vendor, new state library, queue/event bus, publishing integration,
media renderer, team mode, offline-sync system or analytics dashboard is implied.
The current source is not already a multi-creator private hosted product. A fresh
UI alone cannot establish that promise.

## Evidence and verification limits

- Specialists used graph discovery/coverage and direct source fallback; metadata
  freshness/parse gaps are recorded in their reports. Whole-product reviewers
  reused those findings instead of repeating broad code audits.
- This is source-based expert evaluation. No new deployed-app/browser audit,
  screen-reader session, model-quality test, representative-creator study or
  usability improvement measurement was performed.
- Only planning documents and an existing-document pointer changed. No product
  code, real user data, migration, external post, account or deployment changed.
- Formatting, report completeness, document links and final repository scope are
  checked separately by the coordinator. Product acceptance scenarios are future
  implementation checks, not green tests of an unimplemented interface.

Coordinator verification on 2026-11-05: the existing backend unittest suite passed
245 tests in isolated temporary storage. The planning-document check inspected 14
documents, found all 10 agent reports, and reported no trailing whitespace or
missing local Markdown links. These checks do not validate the proposed UI.
The final repository whitespace check passed, and scope inspection found only
planning documents plus the existing workspace-document pointer. The historical
git-ignored November 4 plan also now points to the canonical proposal.

Reviewers 07 and 10 were reused for a read-only check of the consolidated plan.
Reviewer 07 caught a diagram routing Resume through Idea despite the saved-stage
contract; the diagram now separates New content from Resume. Reviewer 10 found
no actionable delivery/capability discrepancy. No new agents or implementation
work were introduced by these final checks.
