"""Offline Supabase JWT verification with ephemeral signing keys."""
import time
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.hosted_auth import SupabaseAuthenticator
from content_machine.workflow.http import workflow_error_response

PROJECT = 'https://example.supabase.co'
ISSUER = f'{PROJECT}/auth/v1'
OWNER = str(uuid.uuid4())


class HostedAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = ec.generate_private_key(ec.SECP256R1())
        cls.other = ec.generate_private_key(ec.SECP256R1())
        cls.rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.keys = Mock()
        self.keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        self.auth = SupabaseAuthenticator(PROJECT, jwks_client=self.keys)
        self.app = FastAPI()
        self.app.state.workflow_authenticator = self.auth
        self.app.add_exception_handler(WorkflowError, lambda request, error: workflow_error_response(error))

        @self.app.get('/principal')
        async def principal(request: Request):
            identity = await resolve_principal(request)
            return JSONResponse(identity.model_dump(mode='json'))

        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def token(self, changes=None, key=None, algorithm='ES256'):
        claims = {'iss': ISSUER, 'aud': 'authenticated', 'sub': OWNER, 'role': 'authenticated',
                  'iat': int(time.time()) - 5, 'exp': int(time.time()) + 300,
                  'app_metadata': {'provider': 'google'}}
        if changes:
            claims.update(changes)
        return jwt.encode(claims, key or self.key, algorithm=algorithm, headers={'kid': 'test-key'})

    def get(self, token):
        return self.client.get('/principal', headers={'Authorization': f'Bearer {token}'})

    def test_accepts_verified_google_and_anonymous_creator_identity(self):
        for claims in ({'app_metadata': {'provider': 'google'}},
                       {'is_anonymous': True, 'app_metadata': {'provider': 'anonymous'}}):
            response = self.get(self.token(claims))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['owner_id'], OWNER)
            self.assertEqual(response.json()['mode'], 'hosted_verified')

    def test_verified_session_uses_only_strict_top_level_signed_anonymous_claim(self):
        for anonymous in (True, False):
            session = self.auth.verify_session(self.token({'is_anonymous': anonymous}))
            self.assertEqual(session.principal.owner_id, OWNER)
            self.assertIs(session.is_anonymous, anonymous)
        for value in (None, 1, 0, 'true', 'false'):
            with self.subTest(value=value):
                self.assertIsNone(self.auth.verify_session(self.token({'is_anonymous': value})))
        self.assertIsNone(self.auth.verify_session(self.token({'user_metadata': {'is_anonymous': True}})))

    def test_verified_session_rejects_invalid_proofs_and_forgery(self):
        for token in ('', None, {}, 'a' * 16385, self.token({'is_anonymous': True}, key=self.other),
                      self.token({'is_anonymous': True, 'exp': int(time.time()) - 1})):
            with self.subTest(kind=type(token).__name__):
                self.assertIsNone(self.auth.verify_session(token))

    def test_rejects_forgery_expiry_wrong_issuer_audience_role_and_subject(self):
        invalid = [self.token(key=self.other), self.token({'exp': int(time.time()) - 1}),
                   self.token({'iss': 'https://attacker.example/auth/v1'}), self.token({'aud': 'wrong'}),
                   self.token({'role': 'anon'}), self.token({'sub': 'not-a-uuid'}),
                   self.token({'iat': int(time.time()) + 600})]
        for token in invalid:
            with self.subTest(token=token[:20]):
                self.assertEqual(self.get(token).status_code, 401)
        claims = {'iss': ISSUER, 'aud': 'authenticated', 'sub': OWNER, 'role': 'authenticated', 'iat': int(time.time())}
        self.assertEqual(self.get(jwt.encode(claims, self.key, algorithm='ES256', headers={'kid': 'test-key'})).status_code, 401)

    def test_rejects_algorithm_confusion_and_missing_bearer_header(self):
        invalid = jwt.encode({'sub': OWNER}, 'not-a-key' * 5, algorithm='HS256', headers={'kid': 'test-key'})
        self.assertEqual(self.get(invalid).status_code, 401)
        self.assertEqual(self.client.get('/principal').status_code, 401)
        self.assertEqual(self.client.get('/principal', headers={'Authorization': 'Basic abc'}).status_code, 401)
        self.assertEqual(self.client.get('/principal', headers={'Authorization': 'Bearer a b'}).status_code, 401)

    def test_accepts_rsa_signatures_and_rejects_token_directed_key_locations(self):
        self.keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.rsa_key.public_key())
        rsa_token = self.token(key=self.rsa_key, algorithm='RS256')
        self.assertEqual(self.get(rsa_token).status_code, 200)
        self.keys.reset_mock()
        claims = {'iss': ISSUER, 'aud': 'authenticated', 'sub': OWNER, 'role': 'authenticated',
                  'iat': int(time.time()), 'exp': int(time.time()) + 60}
        for extra in ({'jku': 'https://attacker.example/keys'}, {'x5u': 'https://attacker.example/key'},
                      {'kid': ''}, {'crit': ['unknown']}):
            headers = {'kid': 'test-key', **extra}
            token = jwt.encode(claims, self.rsa_key, algorithm='RS256', headers=headers)
            self.assertEqual(self.get(token).status_code, 401)
        self.keys.get_signing_key_from_jwt.assert_not_called()

    def test_rejects_audience_arrays_and_missing_or_blank_subject(self):
        for values in ({'aud': ['authenticated', 'other']}, {'sub': ''}, {'sub': None}, {'role': 'service_role'}):
            self.assertEqual(self.get(self.token(values)).status_code, 401)

    def test_unavailable_jwks_and_invalid_config_fail_closed(self):
        self.keys.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientError('unavailable')
        self.assertEqual(self.get(self.token()).status_code, 401)
        for url in ('http://example.supabase.co', 'https://user:secret@example.com',
                    'https://example.com/path', 'https://example.com/?token=secret', 'https://'):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    SupabaseAuthenticator(url, jwks_client=self.keys)


if __name__ == '__main__':
    unittest.main()
