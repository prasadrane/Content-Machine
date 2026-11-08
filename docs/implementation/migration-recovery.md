# Local migration and recovery rehearsal

The `workflow.recovery` module provides explicit offline SQLite backup and restore rehearsal. It accepts a caller-supplied source database and a new destination file. `backup_database` uses SQLite's backup API, verifies database integrity and foreign keys, and returns table counts and a content fingerprint. `rehearse_restore` makes a second new copy and compares its content against the verified backup. Existing files are never overwritten. The module does not assign legacy records to an owner or invoke a migration.

Use a private, access-controlled destination and verify enough disk space before a real backup. The SQLite backup is a database snapshot, not a backup of attachment files, provider configuration, OAuth credentials, environment settings, or external services. The utility has no public HTTP route or automatic startup action.

The offline tests use temporary databases and rehearse opening the restored snapshot without migration. They check preserved legacy comments and history, immutable approved content, operation input snapshots, and creator isolation. A production migration requires a separate approved mapping for legacy ownership and a rehearsal against representative, authorized data.

Hosted Supabase/Postgres backup, point-in-time recovery, access controls, retention and restore testing are separate gates. SQLite verification does not validate hosted backups or a deployed workspace.

## Combined local database and attachments

`workflow.workspace_recovery` composes the existing database and attachment utilities into one verified recovery bundle. Stop application and attachment writers first, then explicitly confirm `quiescent=True`. A SQLite write reservation excludes database writers throughout capture. File inventories before/after capture detect incidental attachment changes; this is not an online filesystem snapshot or protection against malicious change-and-revert races.

```python
from content_machine.workflow.workspace_recovery import (
    backup_workspace, inspect_workspace_bundle, rehearse_workspace_restore,
)

report = backup_workspace(
    database_path, attachment_directory, new_backup_directory, quiescent=True,
)
assert inspect_workspace_bundle(new_backup_directory) == report
assert rehearse_workspace_restore(new_backup_directory, new_restore_directory) == report
```

All arguments are explicit paths, not automatic storage discovery. The database must permit a write reservation; failure to acquire one aborts capture. The database and attachment directory must be separate, and neither output may overlap inputs or an existing entry. Select private destinations with sufficient space. Credentials, environment files, other filesystem trees and external services are not included automatically.

The backup contains `manifest.json`, a self-contained `workflow.sqlite`, and a verified `attachments/` recovery bundle. Restoring creates one new directory containing `workflow.sqlite` and exact attachment files under `attachments/`. The whole staged directory is published only after both parts verify; failures do not publish a database-only or attachments-only target. Existing/concurrently created destinations are preserved. Handled failures remove private staging; hard process termination may leave staging for explicit inspection. Publication does not promise power-loss durability or hosted PITR.

New SQLite backup files are converted to DELETE journal mode before verification so they do not require WAL/SHM sidecars. The source database's journal mode remains unchanged. Stored historical approvals, operations, legacy comments and owner associations are preserved byte-for-byte/semantically by the database snapshot. The recovery container itself is labelled `editorial_approval=False`; creating a backup does not approve a draft or assign legacy ownership. Restoring is a rehearsal and does not activate or replace a live workspace.

The combined recovery test suite also includes a restored-workspace regression for three seed refresh/reopen cycles and repeated real additive `migrate_workflow` calls. Its disposable fixture includes newer unapproved creator edits, profile/source configuration and captured source evidence, an earlier exact approved export, edited guest examples with stored provenance, unassigned legacy comments and attachment bytes. It compares the complete database fingerprint after each cycle and checks that guest bootstrap does not replace edits or duplicate examples. This new regression is pending execution because automatic approval review could not complete after its usage limit was reached; it is not passing migration evidence yet. It does not test legacy owner assignment or hosted migrations.
