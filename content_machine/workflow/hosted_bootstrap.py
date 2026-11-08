"""Explicit hosted wiring. Schema installation remains an operator migration."""
import sys

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.hosted_auth import SupabaseAuthenticator
from content_machine.workflow.hosted_configuration import HostedConfigurationError, parse_hosted_configuration
from content_machine.workflow.postgres_session import PostgresSession


_FAILURE_HINTS = (
    ('root certificate', 'root_certificate_missing'),
    ('certificate verify failed', 'certificate_untrusted'),
    ('password authentication failed', 'bad_credentials'),
    ('tenant or user not found', 'bad_pooler_user'),
    ('could not translate host', 'dns'),
    ('network is unreachable', 'network_unreachable'),
    ('timeout', 'timeout'),
    ('ssl', 'tls_other'),
)


def configure_hosted_workflow(app, values):
    try:
        config = parse_hosted_configuration(values)
    except HostedConfigurationError:
        # Keep readiness/static routes available while workspace access fails
        # closed through the existing missing-auth/storage guards.
        return
    authenticator = SupabaseAuthenticator(config.supabase_url)

    def connection():
        raw = None
        try:
            import psycopg
            raw = psycopg.connect(config.database_url, autocommit=True,
                                   connect_timeout=10, prepare_threshold=None,
                                   options='-c search_path=public,pg_catalog -c statement_timeout=30000 -c lock_timeout=10000')
            return PostgresSession(raw)
        except Exception as exc:
            if raw is not None:
                raw.close()
            # Operator diagnostic: a fixed category only, never driver text.
            text = str(exc).lower()
            category = next((name for key, name in _FAILURE_HINTS if key in text), 'other')
            print(f'workflow_storage_unavailable class={type(exc).__name__} category={category}',
                  file=sys.stderr, flush=True)
            raise WorkflowError(503, 'workflow_storage_unavailable',
                                'Workspace storage is temporarily unavailable. Try again.') from None

    app.state.workflow_authenticator = authenticator
    app.state.workflow_connection_factory = connection
