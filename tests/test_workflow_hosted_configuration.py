"""Hosted readiness parses explicit fixture mappings, never environment secrets."""
import unittest

from content_machine.workflow.hosted_configuration import (
    DatabaseConnectionMode, HostedConfigurationError, parse_hosted_configuration,
)


class HostedConfigurationTest(unittest.TestCase):
    def config(self, **changes):
        return {'SUPABASE_URL': 'https://fixture.supabase.co/',
                'CONTENT_MACHINE_DATABASE_URL': 'postgresql://fixture:fixture-secret@db.example.com:5432/postgres?sslmode=verify-full',
                'CONTENT_MACHINE_DATABASE_MODE': 'direct', **changes}

    def assert_invalid(self, values, code):
        with self.assertRaises(HostedConfigurationError) as error:
            parse_hosted_configuration(values)
        self.assertEqual(error.exception.code, code)
        self.assertNotIn('fixture-secret', str(error.exception))
        self.assertNotIn('fixture-secret', repr(error.exception))
        return error.exception

    def test_configuration_only_readiness_and_secret_redaction(self):
        values = self.config()
        before = dict(values)
        parsed = parse_hosted_configuration(values)
        self.assertEqual(values, before)
        self.assertEqual(parsed.supabase_url, 'https://fixture.supabase.co')
        self.assertEqual(parsed.database_mode, DatabaseConnectionMode.DIRECT)
        self.assertEqual(parsed.database_url, values['CONTENT_MACHINE_DATABASE_URL'])
        self.assertNotIn('fixture-secret', repr(parsed))
        self.assertEqual(parsed.readiness(), {'configuration_ready': True,
            'database_mode': 'direct', 'live_database_verified': False,
            'hosted_storage_enabled': False})

    def test_requires_every_explicit_setting(self):
        for name in self.config():
            for value in (None, '', '  '):
                with self.subTest(name=name, value=value):
                    values = self.config()
                    values[name] = value
                    error = self.assert_invalid(values, 'hosted_configuration_missing')
                    self.assertEqual(error.variable, name)

    def test_explicit_connection_mode_is_not_inferred_from_host_or_port(self):
        for mode in DatabaseConnectionMode:
            parsed = parse_hosted_configuration(self.config(CONTENT_MACHINE_DATABASE_MODE=mode.value))
            self.assertEqual(parsed.database_mode, mode)
        for mode in ('auto', 'pooler', 'DIRECT', ' direct ', 1):
            self.assert_invalid(self.config(CONTENT_MACHINE_DATABASE_MODE=mode), 'hosted_database_mode_invalid')

    def test_rejects_non_origin_supabase_urls(self):
        for origin in ('http://fixture.supabase.co', 'https://u:p@fixture.supabase.co',
                       'https://fixture.supabase.co/auth/v1', 'https://fixture.supabase.co?token=x',
                       'https://fixture.supabase.co#x', 'https://fixture.supabase.co:444',
                       ' https://fixture.supabase.co', 'https://fixture.supabase.co\n',
                       'https://', 'https://fixture%2esupabase.co', 'https://fixture.supabase.co\\evil', 5):
            with self.subTest(origin=origin):
                self.assert_invalid(self.config(SUPABASE_URL=origin), 'hosted_supabase_url_invalid')

    def test_postgres_dsn_requires_tls_verification_and_single_database(self):
        for dsn in ('sqlite:///tmp/fixture.db', 'host=db.example.com password=fixture-secret',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=require',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=disable',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full&sslmode=disable',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full&host=evil.example',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full&options=-cfoo',
                    'postgresql://fixture:fixture-secret@db.example.com:bad/postgres?sslmode=verify-full',
                    'postgresql://fixture:fixture-secret@db.example.com/a/b?sslmode=verify-full',
                    'postgresql://fixture:fixture-secret@/postgres?sslmode=verify-full',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full#fragment',
                    'postgresql://fixture:fixture-secret@db.example.com:0/postgres?sslmode=verify-full',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full&sslrootcert=%ZZ',
                    'postgresql://fixture:fixture-secret@db.example.com/postgres?sslmode=verify-full\n'):
            with self.subTest(dsn_kind=dsn.split(':')[0]):
                self.assert_invalid(self.config(CONTENT_MACHINE_DATABASE_URL=dsn), 'hosted_database_url_invalid')

    def test_accepts_percent_encoded_credentials_and_explicit_ca_bundle(self):
        url = 'postgres://user:p%40ss%3Aword@db.example.com:6543/postgres?sslmode=verify-full&sslrootcert=C%3A%2Fcerts%2Fca.pem'
        parsed = parse_hosted_configuration(self.config(CONTENT_MACHINE_DATABASE_URL=url,
            CONTENT_MACHINE_DATABASE_MODE='transaction_pooler'))
        self.assertEqual(parsed.database_url, url)
        self.assertNotIn('p%40ss', repr(parsed))

    def test_rejects_missing_user_password_or_database_and_unknown_query_parameters(self):
        for url in ('postgres://db.example.com/postgres?sslmode=verify-full',
                    'postgres://user@db.example.com/postgres?sslmode=verify-full',
                    'postgres://user:@db.example.com/postgres?sslmode=verify-full',
                    'postgres://user:fixture-secret@db.example.com/?sslmode=verify-full',
                    'postgres://user:fixture-secret@db.example.com/postgres?sslmode=verify-full&service=x',
                    'postgres://user:fixture-secret@db.example.com/postgres?sslmode=verify-full&sslrootcert='):
            self.assert_invalid(self.config(CONTENT_MACHINE_DATABASE_URL=url), 'hosted_database_url_invalid')

    def test_mapping_is_required_and_unknown_environment_keys_are_not_reported(self):
        self.assert_invalid(None, 'hosted_configuration_invalid')
        parsed = parse_hosted_configuration(self.config(UNRELATED_SECRET='fixture-secret'))
        self.assertNotIn('UNRELATED_SECRET', repr(parsed.readiness()))
        self.assertNotIn('fixture-secret', repr(parsed.readiness()))
