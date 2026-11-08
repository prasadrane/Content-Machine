"""Hosted wiring opens only trusted PostgreSQL and never applies DDL."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from content_machine.workflow.errors import WorkflowError


class HostedBootstrapTest(unittest.TestCase):
    def test_missing_config_leaves_closed_unconfigured_application(self):
        from content_machine.workflow.hosted_bootstrap import configure_hosted_workflow
        app = SimpleNamespace(state=SimpleNamespace())
        configure_hosted_workflow(app, {})
        self.assertFalse(hasattr(app.state, 'workflow_connection_factory'))
        self.assertFalse(hasattr(app.state, 'workflow_authenticator'))

    def test_mounts_verifier_and_lazy_factory_without_connecting(self):
        from content_machine.workflow.hosted_bootstrap import configure_hosted_workflow
        app = SimpleNamespace(state=SimpleNamespace())
        values = {'SUPABASE_URL': 'https://example.supabase.co',
                  'CONTENT_MACHINE_DATABASE_MODE': 'direct',
                  'CONTENT_MACHINE_DATABASE_URL': 'postgresql://user:secret@example.test/postgres?sslmode=verify-full'}
        raw = Mock(autocommit=True)
        raw.info.transaction_status = 0
        with patch('psycopg.connect', return_value=raw) as connect:
            configure_hosted_workflow(app, values)
            connect.assert_not_called()
            self.assertTrue(callable(app.state.workflow_authenticator))
            session = app.state.workflow_connection_factory()
            self.assertEqual(session.dialect, 'postgresql')
            self.assertEqual(connect.call_args.kwargs['autocommit'], True)
            self.assertFalse(any('CREATE' in str(call) for call in raw.execute.call_args_list))
            session.close()

    def test_connection_errors_are_typed_and_redacted(self):
        from content_machine.workflow.hosted_bootstrap import configure_hosted_workflow
        app = SimpleNamespace(state=SimpleNamespace())
        values = {'SUPABASE_URL': 'https://example.supabase.co',
                  'CONTENT_MACHINE_DATABASE_MODE': 'transaction_pooler',
                  'CONTENT_MACHINE_DATABASE_URL': 'postgresql://user:secret@example.test/postgres?sslmode=verify-full'}
        configure_hosted_workflow(app, values)
        with patch('psycopg.connect', side_effect=RuntimeError('secret password')):
            with self.assertRaises(WorkflowError) as error:
                app.state.workflow_connection_factory()
        self.assertEqual(error.exception.code, 'workflow_storage_unavailable')
        self.assertNotIn('secret', str(error.exception))

    def test_preference_insert_uses_portable_qmark_parameters(self):
        from content_machine.workflow.preferences import _insert
        from content_machine.workflow.schemas import Principal
        conn = Mock()
        _insert(conn, Principal(owner_id='owner', mode='hosted_verified'),
                'Concrete examples', 'pending', 'manual', None)
        sql, params = conn.execute.call_args_list[0].args
        self.assertNotIn(':preference_id', sql)
        self.assertIsInstance(params, tuple)
        self.assertEqual(sql.count('?'), len(params))
