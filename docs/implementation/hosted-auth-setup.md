# Hosted authentication preparation

This packet prepares offline verification of Supabase access tokens and a draft
Postgres schema for private creator workspaces. The running application still
fails closed when no hosted authenticator is configured. The SQLite local mode
is unchanged. Neither the Supabase migration nor the authenticator has been
connected to the deployed application.

## Server configuration

- Supply the exact Supabase project HTTPS origin through trusted server
  configuration. The expected issuer is `<project-origin>/auth/v1` and the
  JWKS URL is derived from that issuer, never from token-controlled headers.
- Install the reviewed runtime dependency `PyJWT[crypto]>=2.10,<3` together with
  a compatible maintained `cryptography` package. Lock the resolved versions
  in the deployed runtime and audit security updates.
- Enable Supabase Auth, configure Google OAuth credentials and approved callback
  URLs, and enable anonymous sign-in for guest sessions in the intended project.
  Do not record secrets in source, test fixtures, logs or browser responses.
- Verify that the selected project issues asymmetric ES256 or RS256 access
  tokens with `kid`, issuer `<project-origin>/auth/v1`, audience and role
  `authenticated`, and UUID subject. Both Google and anonymous Supabase
  identities must pass those same signed-token checks. Legacy HS256 projects
  require an explicit, independently reviewed migration to asymmetric signing.
- The backend accepts a single `Authorization: Bearer <access-token>` header.
  `SupabaseAuthenticator` verifies signature, permitted algorithm, issuer,
  audience, expiry, issued-at, authenticated role and canonical UUID subject.
  It maps only the verified subject to `Principal(mode="hosted_verified")`.
  It never accepts a creator ID or signing-key URL from browser input.

## Postgres review gate

`supabase/migrations/202611060001_workflow_foundation.sql` is an unexecuted
review artifact. It expresses owner-keyed tables, same-owner foreign keys,
read-only RLS policies and immutable historical versions, approvals and
preference events and captured operation inputs. Browser roles receive no direct mutation privilege.
Anonymous guests use their own Supabase authenticated subject and RLS scope.

Before application, test the migration on a disposable Supabase project with
the exact production Postgres extensions and roles. Verify A/B/anonymous
isolation, cross-owner references, service-role behavior, privilege grants,
immutable-row triggers, rollback, schema compatibility and query indexes.
The currently planned Postgres mutation adapter must use transactions and owner
verification with compare-and-swap, idempotency, rollback on failed commits,
and immutable approval/version semantics. Its interface, transaction RPCs,
access grants and function `search_path` require separate review before the
browser or backend gains write access. No transaction RPC is installed here.

The operation context schema follows the current separate immutable input-row
contract. Reconcile it with the final integrated operation implementation before
applying this draft or persisting AI operations.
Plan and test a repeatable migration of explicitly mapped creator-owned SQLite
data, preserve ambiguous legacy data without guessed ownership, and exercise
backup, rollback and restoration before any production migration.

## Remaining integration and live gates

1. Select and implement the hosted Postgres storage adapter and its transactional
   operations. Keep local SQLite as a separate trusted local path.
2. Establish verified session and token refresh handling, CSRF protection for
   any cookie-based flow, expiry behavior, and restrictions on legacy global
   routes. Register the authenticator only as part of that reviewed integration.
3. Implement isolated, labelled guest seeding, persistent return visits and an
   explicit verified transfer flow into a Google account.
4. Evaluate API cost and rate limits for live guest AI before connecting a
   provider. Configure Cloudflare Workers AI using the separate setup document.
5. Verify actual Google and anonymous sign-in, forged/expired tokens, key rotation,
   JWKS outage, owner isolation, concurrent retries, exact export and recovery
   across a deployment restart. These require project configuration and live
   services and are not covered by the offline authentication tests.
