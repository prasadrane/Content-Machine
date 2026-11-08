"""Supabase access-token verifier for a trusted hosted application adapter.

This module does not configure the application or provide database access.
The project URL is trusted server configuration. The token only supplies a
JWT, never a key URL or an owner identifier outside the signed subject claim.
"""
from __future__ import annotations

import uuid
from urllib.parse import urlsplit

import jwt
from fastapi import Request

from content_machine.workflow.schemas import Principal
from content_machine.workflow.guests import VerifiedGuestSession

_ALGORITHMS = ("ES256", "RS256")
_MAX_TOKEN_LENGTH = 16_384


class SupabaseAuthenticator:
    """Verify signed Supabase access tokens before resolving creator identity.

    ``jwks_client`` is injectable for offline tests. In production PyJWT's
    JWKS client uses the fixed issuer-derived HTTPS URL and caches signing keys.
    """

    def __init__(self, project_url: str, *, jwks_client=None):
        if not isinstance(project_url, str) or project_url != project_url.strip():
            raise ValueError("A trusted Supabase HTTPS project URL is required")
        try:
            parsed = urlsplit(project_url)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid Supabase project URL") from exc
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path not in ("", "/")
                or parsed.query or parsed.fragment or port not in (None, 443)
                or any(character.isspace() for character in project_url)):
            raise ValueError("A trusted Supabase HTTPS project URL is required")
        self.issuer = f"{project_url.rstrip('/')}/auth/v1"
        self.jwks_client = jwks_client if jwks_client is not None else jwt.PyJWKClient(
            f"{self.issuer}/.well-known/jwks.json", timeout=5, cache_jwk_set=True,
        )

    def __call__(self, request: Request) -> Principal | None:
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer" or len(parts[1]) > _MAX_TOKEN_LENGTH:
            return None
        verified = self._verify_token(parts[1])
        return verified[0] if verified is not None else None

    def verify_session(self, token: str) -> VerifiedGuestSession | None:
        """Resolve guest status only from a verified, strict top-level claim.

        Missing/ambiguous flags and editable user metadata cannot authorize
        guest bootstrap or transfer. Principal-only verification stays compatible
        with older tokens that omit this optional claim.
        """
        verified = self._verify_token(token)
        if verified is None or type(verified[1].get('is_anonymous')) is not bool:
            return None
        return VerifiedGuestSession(verified[0], is_anonymous=verified[1]['is_anonymous'])

    def _verify_token(self, token):
        if not isinstance(token, str) or not token or len(token) > _MAX_TOKEN_LENGTH:
            return None
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in _ALGORITHMS or not isinstance(header.get("kid"), str):
                return None
            if not header["kid"] or any(key in header for key in ("jku", "x5u", "crit")):
                return None
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token, signing_key.key, algorithms=list(_ALGORITHMS),
                audience="authenticated", issuer=self.issuer,
                options={"require": ["iss", "aud", "sub", "role", "iat", "exp"],
                         "strict_aud": True},
            )
            if claims.get("role") != "authenticated" or not isinstance(claims.get("sub"), str):
                return None
            subject = claims["sub"]
            if str(uuid.UUID(subject)) != subject:
                return None
            return Principal(owner_id=subject, mode="hosted_verified"), claims
        except (jwt.PyJWTError, ValueError, TypeError, AttributeError):
            return None


__all__ = ["SupabaseAuthenticator"]
