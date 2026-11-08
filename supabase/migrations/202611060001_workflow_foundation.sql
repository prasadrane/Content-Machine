-- Hosted foundation. Install only through the explicit backup-first operator
-- tool after transaction, owner-isolation and restore verification.
-- Browser roles receive owner-scoped reads only. Mutations use the verified
-- server session adapter; this file is never applied during app startup.
-- One-shot foundation: migration ledger applies exactly once. Reapplying fails
-- atomically rather than masking drift with IF NOT EXISTS. This artifact does
-- not activate hosted storage. JSON payloads retain the runtime's canonical
-- serialization as TEXT, without jsonb normalization or changed digests.
-- Scalar PostgreSQL TEXT still rejects NUL/invalid Unicode; adapters must reject
-- unsupported scalar input explicitly before writes, never silently rewrite it.
BEGIN;

CREATE TABLE public.workflow_items (
  item_id text PRIMARY KEY, owner_id uuid NOT NULL,
  title text NOT NULL, destination text NOT NULL, format text NOT NULL,
  stage text NOT NULL CHECK (stage IN ('idea', 'draft_review', 'approve', 'export')),
  working_revision integer NOT NULL CHECK (working_revision >= 1),
  context_json text NOT NULL, artifact_json text NOT NULL,
  parent_version_id text, active_approval_id text,
  created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
  UNIQUE (item_id, owner_id)
);

CREATE TABLE public.workflow_versions (
  version_id text PRIMARY KEY, item_id text NOT NULL, owner_id uuid NOT NULL,
  revision integer NOT NULL CHECK (revision >= 1),
  context_json text NOT NULL, artifact_json text NOT NULL,
  destination text NOT NULL, format text NOT NULL,
  artifact_digest text NOT NULL CHECK (artifact_digest ~ '^sha256:[0-9a-f]{64}$'),
  purpose text NOT NULL CHECK (purpose IN ('review', 'skip_review', 'approval', 'restore', 'adaptation')),
  created_by uuid NOT NULL, created_at timestamptz NOT NULL,
  UNIQUE (item_id, revision), UNIQUE (version_id, owner_id),
  UNIQUE (version_id, owner_id, item_id),
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id)
);

CREATE TABLE public.workflow_approvals (
  approval_id text PRIMARY KEY, owner_id uuid NOT NULL, item_id text NOT NULL,
  version_id text NOT NULL,
  artifact_digest text NOT NULL CHECK (artifact_digest ~ '^sha256:[0-9a-f]{64}$'),
  destination text NOT NULL, format text NOT NULL, approved_by uuid NOT NULL,
  approved_at timestamptz NOT NULL, UNIQUE (approval_id, owner_id, item_id),
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id),
  FOREIGN KEY (version_id, owner_id, item_id) REFERENCES public.workflow_versions (version_id, owner_id, item_id)
);

ALTER TABLE public.workflow_items ADD CONSTRAINT workflow_items_parent_owner_fk
  FOREIGN KEY (parent_version_id, owner_id) REFERENCES public.workflow_versions (version_id, owner_id);
ALTER TABLE public.workflow_items ADD CONSTRAINT workflow_items_approval_owner_fk
  FOREIGN KEY (active_approval_id, owner_id, item_id)
  REFERENCES public.workflow_approvals (approval_id, owner_id, item_id);

CREATE TABLE public.workflow_operations (
  operation_id text PRIMARY KEY, owner_id uuid NOT NULL, item_id text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('generate', 'review')), input_version_id text NOT NULL,
  context_snapshot_json text NOT NULL, state text NOT NULL CHECK (state IN ('pending', 'completed', 'failed')),
  request_id text NOT NULL, result_json text, error_json text,
  started_at timestamptz, finished_at timestamptz,
  UNIQUE (operation_id, owner_id, item_id),
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id),
  FOREIGN KEY (input_version_id, owner_id, item_id) REFERENCES public.workflow_versions (version_id, owner_id, item_id)
);

CREATE TABLE public.workflow_operation_inputs (
  operation_id text PRIMARY KEY, owner_id uuid NOT NULL, item_id text NOT NULL,
  request_digest text NOT NULL, editorial_snapshot_json text NOT NULL,
  FOREIGN KEY (operation_id, owner_id, item_id)
    REFERENCES public.workflow_operations (operation_id, owner_id, item_id)
);

CREATE TABLE public.workflow_reviews (
  review_id text PRIMARY KEY, owner_id uuid NOT NULL, item_id text NOT NULL,
  input_version_id text NOT NULL, request_id text NOT NULL,
  state text NOT NULL CHECK (state IN ('pending', 'completed', 'failed', 'skipped')),
  actions_json text NOT NULL DEFAULT '{}', score_basis_json text,
  proposals_json text NOT NULL DEFAULT '[]', model_config text,
  started_at timestamptz, finished_at timestamptz,
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id),
  FOREIGN KEY (input_version_id, owner_id, item_id) REFERENCES public.workflow_versions (version_id, owner_id, item_id)
);

CREATE TABLE public.workflow_idempotency (
  owner_id uuid NOT NULL, request_id text NOT NULL, method text NOT NULL
    CHECK (method IN ('POST', 'PATCH', 'PUT', 'DELETE')),
  resource_path text NOT NULL, request_digest text NOT NULL,
  response_status integer NOT NULL CHECK (response_status BETWEEN 100 AND 599),
  response_body_json text NOT NULL, created_at timestamptz NOT NULL,
  PRIMARY KEY (owner_id, request_id)
);

CREATE TABLE public.workflow_profiles (
  owner_id uuid PRIMARY KEY, name text NOT NULL, role text NOT NULL, bio text NOT NULL,
  revision integer NOT NULL CHECK (revision >= 1), updated_at timestamptz NOT NULL
);

CREATE TABLE public.workflow_sources (
  source_id text PRIMARY KEY, owner_id uuid NOT NULL, kind text NOT NULL CHECK (kind = 'rss'),
  name text NOT NULL, url text NOT NULL, enabled integer NOT NULL CHECK (enabled IN (0,1)),
  revision integer NOT NULL CHECK (revision >= 1),
  created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
  UNIQUE (source_id, owner_id)
);

CREATE TABLE public.workflow_preferences (
  preference_id text PRIMARY KEY, owner_id uuid NOT NULL, text text NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'pending', 'stopped', 'rejected')),
  origin text NOT NULL CHECK (origin IN ('manual', 'item', 'legacy')),
  origin_ref text, conflict_preference_id text, revision integer NOT NULL CHECK (revision >= 1),
  created_at timestamptz NOT NULL, updated_at timestamptz NOT NULL,
  UNIQUE (preference_id, owner_id),
  FOREIGN KEY (conflict_preference_id, owner_id) REFERENCES public.workflow_preferences (preference_id, owner_id)
);

CREATE TABLE public.workflow_preference_events (
  event_id text PRIMARY KEY, preference_id text NOT NULL, owner_id uuid NOT NULL,
  revision integer NOT NULL CHECK (revision >= 1), text text NOT NULL,
  status text NOT NULL, event text NOT NULL, created_at timestamptz NOT NULL,
  UNIQUE (preference_id, revision),
  FOREIGN KEY (preference_id, owner_id) REFERENCES public.workflow_preferences (preference_id, owner_id)
);

CREATE TABLE public.workflow_guest_examples (
  owner_id uuid NOT NULL, example_key text NOT NULL, item_id text NOT NULL,
  label text NOT NULL, created_at timestamptz NOT NULL,
  PRIMARY KEY (owner_id, example_key), UNIQUE (item_id, owner_id),
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id)
);

CREATE TABLE public.workflow_discovery_cache (
  owner_id uuid NOT NULL, source_id text NOT NULL, url text NOT NULL,
  source_revision integer NOT NULL CHECK (source_revision >= 1),
  etag text CHECK (etag IS NULL OR length(etag) <= 512),
  last_modified text CHECK (last_modified IS NULL OR length(last_modified) <= 128),
  PRIMARY KEY (owner_id, source_id),
  FOREIGN KEY (source_id, owner_id) REFERENCES public.workflow_sources (source_id, owner_id)
);

-- Explicit operator archive, not browser-visible workspace data. Quarantined
-- records deliberately have no guessed owner; preserve historical approval as
-- unknown. Installation here does not run imports or assign ownership.
CREATE TABLE public.workflow_legacy_imports (
  source_namespace text NOT NULL, legacy_id text NOT NULL,
  input_digest text NOT NULL, record_json text NOT NULL,
  state text NOT NULL CHECK (state IN ('imported', 'synthetic_quarantined', 'unknown_quarantined')),
  owner_id uuid, item_id text, imported_at timestamptz NOT NULL,
  historical_approval text NOT NULL DEFAULT 'unknown' CHECK (historical_approval = 'unknown'),
  PRIMARY KEY (source_namespace, legacy_id), UNIQUE (item_id, owner_id),
  FOREIGN KEY (item_id, owner_id) REFERENCES public.workflow_items (item_id, owner_id),
  CHECK ((state = 'imported' AND owner_id IS NOT NULL AND item_id IS NOT NULL)
      OR (state != 'imported' AND owner_id IS NULL AND item_id IS NULL))
);

CREATE TABLE public.workflow_guest_transfers (
  transfer_id text PRIMARY KEY, source_owner_id uuid NOT NULL, destination_owner_id uuid NOT NULL,
  request_id text NOT NULL, source_fingerprint text NOT NULL, policy text NOT NULL,
  archive_json text NOT NULL, response_json text NOT NULL, created_at timestamptz NOT NULL,
  UNIQUE (transfer_id, destination_owner_id),
  UNIQUE (source_owner_id, destination_owner_id, request_id),
  UNIQUE (source_owner_id, destination_owner_id), CHECK (source_owner_id <> destination_owner_id)
);

CREATE TABLE public.workflow_guest_transfer_items (
  transfer_id text NOT NULL, source_item_id text NOT NULL, target_item_id text NOT NULL,
  destination_owner_id uuid NOT NULL, context_mapping_json text NOT NULL, example_label text,
  PRIMARY KEY (transfer_id, source_item_id), UNIQUE (target_item_id, destination_owner_id),
  FOREIGN KEY (transfer_id, destination_owner_id) REFERENCES public.workflow_guest_transfers (transfer_id, destination_owner_id),
  FOREIGN KEY (target_item_id, destination_owner_id) REFERENCES public.workflow_items (item_id, owner_id)
);

CREATE TABLE public.workflow_provider_budget_days (
  pool text NOT NULL, day text NOT NULL, daily_limit bigint NOT NULL CHECK (daily_limit > 0),
  max_inflight integer NOT NULL CHECK (max_inflight > 0), PRIMARY KEY (pool, day)
);

CREATE TABLE public.workflow_provider_reservations (
  pool text NOT NULL, request_id text NOT NULL, day text NOT NULL,
  subject_id text NOT NULL, provider text NOT NULL, model text NOT NULL,
  reserved_units bigint NOT NULL CHECK (reserved_units > 0),
  charged_units bigint NOT NULL CHECK (charged_units >= 0),
  state text NOT NULL CHECK (state IN ('reserved','dispatched','uncertain','settled','released')),
  PRIMARY KEY (pool, request_id),
  FOREIGN KEY (pool, day) REFERENCES public.workflow_provider_budget_days (pool, day)
);
ALTER TABLE public.workflow_provider_budget_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_provider_budget_days FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.workflow_provider_budget_days FROM PUBLIC, anon, authenticated;
ALTER TABLE public.workflow_provider_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_provider_reservations FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.workflow_provider_reservations FROM PUBLIC, anon, authenticated;

CREATE INDEX workflow_items_owner_updated ON public.workflow_items (owner_id, updated_at DESC);
CREATE INDEX workflow_sources_owner ON public.workflow_sources (owner_id, created_at, source_id);
CREATE INDEX workflow_preferences_owner_status ON public.workflow_preferences (owner_id, status);
CREATE UNIQUE INDEX workflow_preferences_legacy_source ON public.workflow_preferences (origin_ref) WHERE origin = 'legacy';
CREATE INDEX workflow_versions_item ON public.workflow_versions (item_id, revision);
CREATE INDEX workflow_operations_item ON public.workflow_operations (item_id, started_at);
CREATE INDEX workflow_reviews_item ON public.workflow_reviews (item_id, started_at);
CREATE INDEX workflow_approvals_item ON public.workflow_approvals (item_id, approved_at);

CREATE FUNCTION public.reject_workflow_history_change() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
  RAISE EXCEPTION 'immutable workflow history';
END;
$$;
CREATE TRIGGER workflow_versions_immutable BEFORE UPDATE OR DELETE ON public.workflow_versions
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_approvals_immutable BEFORE UPDATE OR DELETE ON public.workflow_approvals
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_preference_events_immutable BEFORE UPDATE OR DELETE ON public.workflow_preference_events
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_operation_inputs_immutable BEFORE UPDATE OR DELETE ON public.workflow_operation_inputs
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_legacy_imports_immutable BEFORE UPDATE OR DELETE ON public.workflow_legacy_imports
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_guest_transfers_immutable BEFORE UPDATE OR DELETE ON public.workflow_guest_transfers
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();
CREATE TRIGGER workflow_guest_transfer_items_immutable BEFORE UPDATE OR DELETE ON public.workflow_guest_transfer_items
  FOR EACH ROW EXECUTE FUNCTION public.reject_workflow_history_change();

DO $$
DECLARE name text;
BEGIN
  FOREACH name IN ARRAY ARRAY['workflow_guest_transfers', 'workflow_guest_transfer_items'] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', name);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', name);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', name);
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO authenticated', name);
    EXECUTE format('CREATE POLICY destination_select ON public.%I FOR SELECT TO authenticated USING (destination_owner_id = (SELECT auth.uid()))', name);
  END LOOP;
END;
$$;

ALTER TABLE public.workflow_legacy_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workflow_legacy_imports FORCE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.workflow_legacy_imports FROM PUBLIC, anon, authenticated;

-- All client-visible relations require the verified Supabase subject. Anonymous
-- Supabase identities use the authenticated role with their own auth.uid().
DO $$
DECLARE name text;
BEGIN
  FOREACH name IN ARRAY ARRAY[
    'workflow_items', 'workflow_versions', 'workflow_approvals', 'workflow_operations', 'workflow_operation_inputs',
    'workflow_reviews', 'workflow_idempotency', 'workflow_profiles', 'workflow_sources',
    'workflow_preferences', 'workflow_preference_events',
    'workflow_guest_examples', 'workflow_discovery_cache'
  ] LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', name);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', name);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated', name);
    EXECUTE format('GRANT SELECT ON TABLE public.%I TO authenticated', name);
    EXECUTE format('CREATE POLICY owner_select ON public.%I FOR SELECT TO authenticated USING (owner_id = (SELECT auth.uid()))', name);
  END LOOP;
END;
$$;

COMMIT;
