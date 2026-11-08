# Hosted schema reconciliation

November 7, 2026. `supabase/migrations/202611060001_workflow_foundation.sql` remains a **review artifact**. It has not been applied to the user's Supabase project. This packet does not mount a database repository or enable hosted saves.

## Runtime parity reviewed

The schema is compared with the actual SQLite workflow migration plus the explicit legacy-import archive initializer. The review artifact now includes all normal workflow tables: items, immutable versions/approvals, operations and immutable operation inputs, reviews, idempotency, profiles, sources, preferences and immutable preference events, guest-example provenance and discovery conditional-header cache. It also includes the separate operator archive for explicit legacy import, including unknown/quarantined records with no guessed owner and historical approval fixed to `unknown`.

Guest-example rows use same-owner item references; cache rows use same-owner source references, source revision and bounded ETag/Last-Modified values. Both receive the same owner-only authenticated read policy as other workspace tables. Browser roles cannot mutate workflow tables. The legacy archive receives RLS with no authenticated or anon grants/policies: an unassigned quarantined record must not become browser-readable. Privileged server paths still require explicit ownership filtering because privileged database roles may bypass RLS.

Operation input ownership keys and immutable history triggers follow the existing runtime schema. Version purposes remain exactly `review`, `skip_review`, `approval`, `restore`, `adaptation`; generation does not invent a new persisted enum value. This schema does not add guest transfer, provider budget tables, or historical discovery content storage: those features need their own reviewed data contracts.

## Exact JSON and scalar text

Every `*_json` payload column uses PostgreSQL `TEXT`, not `jsonb`. The accepted local input domain can include escaped NUL or unpaired surrogate values inside JSON strings. PostgreSQL JSONB cannot represent that whole domain. Server writers must encode payloads with canonical ASCII-escaped JSON (`ensure_ascii=True`, strict finite JSON), remove `::jsonb` casts, and decode with the same application validators on reads. No payload is normalized into an alternate Unicode form. JSON payload schema validity remains an application validation responsibility; the table type alone is not proof of a valid editorial object.

PostgreSQL scalar TEXT fields still cannot contain NUL or invalid Unicode scalar values. The adapter must return a typed, value-redacted unsupported-input error **before mutation** for affected scalar fields. A scalar title/profile/preference must not be truncated, replaced or silently normalized to fit the database. The SQL artifact alone cannot implement this application gate. UUID owner IDs are a separate explicit hosted identity boundary; arbitrary local legacy owner strings require an explicit verified mapping before hosted import.

## Migration application and replay

The foundation is a one-shot transactional migration, intended to be recorded once by a migration ledger. It deliberately does not use `CREATE TABLE IF NOT EXISTS` to conceal preexisting drift. A second direct application must fail atomically and preserve the already-created data/schema. Changing an already-applied production foundation would require a new versioned additive migration and preflight checks; no live applied version has been established here.

Before real application, verify actual provider Postgres version, required `anon`/`authenticated` roles and `auth.uid()`, backup and rollback procedure, role grants, indexes, ownership isolation, concurrent CAS/idempotency and server transaction acknowledgement. No destructive reset is part of this packet.

## Verification boundaries and commands

`tests/test_workflow_postgres_schema.py` has offline structural checks that compare every actual SQLite runtime/archive column with this artifact and check JSON storage and privilege declarations. These can find omissions and contract drift but do not parse or execute PostgreSQL SQL and do not prove RLS, transaction, concurrency or hosted behavior.

The same file contains actual PostgreSQL tests, skipped unless both `CM_POSTGRES_SCHEMA_TEST_DISPOSABLE=1` and `CM_POSTGRES_SCHEMA_TEST_DSN` are explicitly configured. The DSN must point to a dedicated disposable database with Supabase auth roles/function already installed, using an appropriately privileged test role. The harness creates a unique `cm_schema_check_<uuid>` schema, rewrites only the artifact's `public.` qualification into it, applies there and drops only that generated schema at cleanup. It does not create shared cluster roles or modify the actual Supabase auth schema. Fixture owner IDs and JSON content are synthetic.

Actual PostgreSQL cases exercise escaped NUL/surrogate JSON roundtrip, quarantine archive privilege denial, owner A/B RLS, browser write denial, cross-owner foreign-key denial, immutable version UPDATE/DELETE rejection, and atomic one-shot repeat-application failure. Without an explicit disposable database, skipped tests remain **unverified** and cannot count as hosted acceptance.

No database credentials are included in this document. Offline verification must use the existing guarded serialized runner. Test logs are controller evidence; runtime skip/pass counts must be reported separately.

Current guarded result: **3 offline checks passed, 4 actual PostgreSQL checks skipped**. Controller log is `hosted-schema-red.txt`; the filename is historical, not evidence of a failing pre-change run. Tests were authored first, but SQL edits landed while the serialized run waited on the shared mutex; no observed red run is claimed. Whitespace checks passed. Real PostgreSQL behavior remains unverified until the opt-in class actually runs.
