# Hosted workspace decision

The user selected Supabase Auth and Postgres for the deployed private workspaces. Prepare the integration for the existing Vercel application.

Supabase and Google sign-in are confirmed. The guest mode has seeded demo data, live AI, saved work across return visits and an explicit transfer offer after sign-in. Project configuration, credentials and live deployment verification remain pending. C45 and C46 retain their implementation and verification gates.

Hosted requests must resolve a verified Supabase identity to a stable creator ID. Postgres must preserve creator ownership, acknowledged revisions, immutable versions, exact approvals and idempotent mutations across application restarts. SQLite continues to support local operation.

Use Supabase anonymous identities for guests, with verified tokens and creator ownership enforced by the same backend. Seed each guest's own workspace with labelled ideas and drafts through an idempotent bootstrap. Live AI produces actual operation records and feedback. Preserve guest work across return visits. After Google authentication, offer an explicit transfer that preserves content and provenance and verifies ownership of both the guest source and authenticated destination.

Prepare the hosted work in separately reviewed packets covering the Postgres schema and ownership policies, transactional persistence, authentication verification, browser session handling, and authenticated recovery checks. Finalize each packet's concrete source paths after the local workflow and legacy-route audit establish the integration seams.

Before hosted verification, establish the Supabase project URL and reference, supported connection mode, credential provisioning, Google OAuth and redirect configuration, guest behavior, migration backup and recovery procedure. Keep server credentials outside source control and Freebuff prompts. The controller supplies environment-variable names and test fixtures to the implementer and manages actual credentials locally.

Acceptance requires authenticated creators A and B to retain separate workspaces, forged or expired identities to fail, concurrent and retried writes to remain consistent, and acknowledged content to survive the selected deployment restart boundary. Record offline tests, live provider checks and deployment checks separately.
