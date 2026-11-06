# Freebuff integration evidence

Date 2026-11-05

## Current execution gate

On November 6, 2026 UTC, Freebuff rejected the C10 handoff under its **Driven by another agent** usage policy. Its completed response contained a `userError` stating that the message was withheld from the model, Freebuff cannot act as a worker for other agents, and the attempt counted as strike 1 that day.

The controller stopped automated submissions. The earlier round trips and accepted implementation checkpoints demonstrate historical execution. The current provider refusal prevents further automated Freebuff handoffs. The user has been asked to choose an automation-supported CLI, direct Codex implementation, or manual Freebuff handoffs.

C00 through C09 are accepted. C10 is pending implementer selection. The exact rejected message and response identity are retained in the ignored controller runtime.

## Verified connection

The user selected Freebuff Desktop and then accepted the official free CLI for automated implementation.
The installed Desktop version is 0.0.200.
The pinned npm CLI is freebuff@0.2.36.
Its package integrity is recorded in workflow-tasks.json.
The initial probe displayed MiMo v2.6 Flash Fast. The implementation session displays Freebuff high and an opaque model identifier; its underlying model is unverified. The CLI shows a data-use notice.

The official CLI help command was run successfully.
The command supports --cwd and --continue and starts an interactive terminal.
The CLI was launched through the available pseudo-terminal using a disposable three-file directory.
Sign-in completed and an active model session was observed.

## Observed round trips

| Probe | Actual result |
| --- | --- |
| Text nonce and arithmetic | CM_BUFF_PROBE_1105_A6 15 |
| File-tool read | CM_BUFF_PROBE_1105_B7 with alpha.txt containing alpha and beta.txt containing beta |
| Cancellation | A terminal-wait response was interrupted by Escape |
| Post-cancellation recovery | CM_BUFF_PROBE_1105_C8 RECOVERED |

The fixture files were independently listed and their expected contents were known to the controller.
The persisted chat recorded both ordinary replies with isComplete=true.
The interrupted reply also had isComplete=true and contained the interruption marker.
The controller therefore records cancellation independently and treats completed replies as ready for review.

The first model-session start timed out. A normal retry established the session.
Freebuff doctor completed its nine checks and reported no problems. Its informational PATH/long-path notes were retained as diagnostics.
The login-page browser automation attempt timed out. The subsequent CLI session became authenticated.

## Terminal driver procedure

1. Start the pinned official CLI with an explicit resolved --cwd.
2. Capture the selected project/chat identity.
3. Type or paste the prompt as one terminal input.
4. Send Enter as a separate terminal input after the text is present.
5. Associate the persisted user message with the request nonce and follow its actual AI record.
6. Wait for that response to complete. Honor the controller cancellation ledger.
7. Read its tool outcomes/report and independently inspect the requested artifact and changes.
8. Accept the checkpoint or send a focused repair prompt.
9. Use Escape for a requested cancellation and verify the resulting interrupted record.
10. Resume only after checking pending work and associating the next request with its own identity.

Current testing used a project-scoped chat-messages.json under the CLI's standard project history.
Its location was derived only from the disposable fixture project.
The integration used project-scoped transcripts and the pinned CLI's normal sign-in flow.

## Runtime locations from this probe

- CLI launcher at C:/Users/mamat/AppData/Local/Temp/content-machine-freebuff-0.2.36/node_modules/.bin/freebuff.cmd
- Fixture project at C:/Users/mamat/AppData/Local/Temp/content-machine-freebuff-smoke
- Project transcript root at C:/Users/mamat/.config/manicode/projects/content-machine-freebuff-smoke/chats

Sandbox and elevated processes may resolve different temporary directories on this computer.
Use resolved absolute paths from the dispatch record when crossing those boundaries.
The terminal tool's transient session identifier belongs to the current active session and requires rediscovery after a restart.

## Repository-context authorization

Automatic approval review rejected a file/environment-inspection probe and later rejected a repository-contract drafting handoff.
The stated reason was insufficient explicit authorization to send repository-derived context to an external model service.
The user was presented a specific choice covering source code, plans and test fixtures, together with the CLI's training-use notice.
The user explicitly answered Yes, authorize this code transfer to Freebuff on 2026-11-05. This authorizes repository source, plans and test fixtures from the isolated copy to be processed by Freebuff's model service under the displayed data-use notice.
The three successful text/file probes used synthetic controller-created fixtures.
The controller prepared local contract snapshots. Automatic review rejected the prompt that would ask Freebuff to read them.

## Continuity and implementation status

The connection prototype has verified prompt submission, real file-tool operation, completion inspection, cancellation and recovery.
A durable unattended controller with its own reviewer runtime remains implementation work.
The repository handoff is authorized. C01's contract was drafted, repaired and accepted.
Freebuff implemented C02's domain schemas and platform registry in the isolated worktree on branch codex/workflow-implementation.
Independent review found a multi-segment final-post validation defect and mutable input aliasing in snapshots. Freebuff repaired both following a controller prompt.
The accepted revision passed 34 focused tests and 279 offline unittest cases independently. Actual failing and passing regression output is retained in the controller runtime.
The accepted implementation checkpoint is d778d00159793bf03cb1029eda7ba59096d603b9.
C03's additive storage migration is accepted at 19e55c31156588a68da2463f59a8096c22820352. Same-owner cross-item approval/review references were found during review and repaired while retaining valid adaptation ancestry.
The accepted storage revision independently passed 47 focused schema/migration/storage cases and 288 unittest cases through the guarded launcher.
C04's trusted-principal boundary is accepted at 1b7fd7d97c43c8e514b009c1735198cf46e282af after 59 focused checks and 300 unittest cases passed independently.
C05's owned working-item persistence is accepted at 7bc49b088029673645a5b2827dc5732d4f82d7e2. Independent review found a failed-commit rollback defect; Freebuff repaired it and retained a real two-connection regression test. The final candidate passed 73 focused checks (including the controller counterexample) and 313 unittest cases independently.
C06's immutable versions are accepted at db926228352eb36841d0e7e90ae80e58e601a6b5 after 81 focused checks and 322 unittest cases passed independently.
C07's approval and exact export are accepted at e91eb43. Independent review found incomplete script cues passing final validation. Freebuff repaired the check and retained the regression. The final candidate passed 101 focused checks, including controller counterexamples, and 339 unittest cases independently.
C08's restoration and linked adaptations are accepted at f8cd862c7fd7354f39fda41dbe0a9c2d8d76ecd5. Independent review corrected a misleading review-purpose label on preserved pre-restore work. The repaired candidate passed 14 focused checks including three independent probes and 350 unittest cases.
C09's saved-item API is accepted at bbd086c68eed0b28a69a1aa05f1b31b0453bf3b6. Independent probes found false success when a request-owned outer transaction was left uncommitted. Freebuff repaired the HTTP boundary and retained real deferred-commit-failure coverage. The final candidate passed 48 focused checks and 363 unittest cases independently.
The requested Cloudflare setup instructions and refined checkpoint scopes are committed at 04ff1419223cae03de7fa5c14db85a5b55e59f27. Later action API, UI and hosted-release checkpoints are pending.

The user confirmed Supabase Auth and Postgres, Google sign-in, and a seeded guest mode with live AI. Guest work persists across return visits, with an offered transfer after Google sign-in. The updated product plan and hosted decision record govern the later guest and hosted packets.
The active implementation session uses the isolated worktree. Session/request identities and acceptance records are stored under the ignored .orchestration/controller directory. A completed worker reply submits a candidate for review and cannot advance the queue itself.

## Test isolation incident and recovery

An intermediate C03 fixture restored an old environment value after another test module selected its temporary home. A subsequent legacy storage test reached the default local data directory, creating ten known fixture rows and six empty unreleased tables and refreshing three runtime knowledge files.
The controller audited exact fixture identities and timestamps read-only, created a full local database backup outside the implementation worktree, removed the exact fixture rows/empty tables and restored the knowledge files from the preserved preimages. Empty test-created project directories were removed without recursive deletion.
Independent verification found exactly ten removed fixture rows, zero other added/changed legacy rows relative to the recovery backup, no foreign-key violations, and matching knowledge preimage hashes. The backup integrity check passed.
The fixture now scopes its import environment immediately and restores per-test temporary homes. Every subsequent Python check must use the controller-owned guarded-test-runner.py, which supplies disposable storage and denies production-directory file/SQLite access. Both guard probes and the accepted checks passed. Production content and the recovery backup are excluded from Freebuff handoffs.

The controller subsequently extended the offline guard to block actual repository credential files and controller-owned Cloudflare credentials. It disables dotenv's upward discovery, which could otherwise reach the original checkout from the nested worktree. Path-only regression tests confirmed the boundary without opening credential contents. The stronger guard passed the C09 verification and full 363-case regression.

## Baseline verification

The source reference is 34405a5530a6340aee17a9b1f0f5f61dfc1bd091.
Backend pytest passed 375 cases and mandatory unittest discovery passed 245 cases.
Frontend verification passed 132 tests across 34 files using temporary Node 22.23.4, matching the CI major version.
The production build and repository diff check passed.
The full frontend run took 241.90 seconds, with environment startup accounting for most of that time.
Earlier Node 24 runs were interrupted. These observations establish a working Node 22 command and leave the earlier runtime diagnosis unresolved.
The planning manifest/runbook validation passed for all 51 checkpoints, their dependency chain, task kinds, allowlists, mirrored steps and local links.

## Sources

- [Freebuff CLI](https://freebuff.com/cli)
- [Freebuff headless orchestration request](https://github.com/CodebuffAI/freebuff/issues/947)
- [Codebuff SDK](https://github.com/CodebuffAI/freebuff/blob/main/sdk/README.md)
- [Codex App Server](https://developers.openai.com/codex/app-server/)
