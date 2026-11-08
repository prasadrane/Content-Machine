"""Explicit hosted wiring. Schema installation remains an operator migration."""
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.hosted_auth import SupabaseAuthenticator
from content_machine.workflow.hosted_configuration import HostedConfigurationError, parse_hosted_configuration
from content_machine.workflow.postgres_session import PostgresSession


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
        except Exception:
            if raw is not None:
                raw.close()
            raise WorkflowError(503, 'workflow_storage_unavailable',
                                'Workspace storage is temporarily unavailable. Try again.') from None

    app.state.workflow_authenticator = authenticator
    app.state.workflow_connection_factory = connection
