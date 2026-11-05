"""Tests for C04 trusted workflow principal resolution.

The principal is chosen only by server configuration: a hosted authenticator
boundary or an explicitly configured, loopback-only trusted-local mode.
Request bodies, query strings, owner fields and forwarding headers are never
identity inputs.

All tests are in-process and offline. Environment changes are restored and no
storage home or runtime directory is created.
"""

from __future__ import annotations

import os
import sys
import unittest

from fastapi import FastAPI, Request

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from content_machine.workflow.access import (  # noqa: E402
    AUTH_MISCONFIGURED,
    UNAUTHENTICATED,
    resolve_principal,
)
from content_machine.workflow.errors import WorkflowError  # noqa: E402
from content_machine.workflow.schema_types import PrincipalMode  # noqa: E402
from content_machine.workflow.schemas import Principal  # noqa: E402

_UNSET = object()
_ENV_KEYS = (
    "CONTENT_MACHINE_WORKFLOW_MODE",
    "CONTENT_MACHINE_LOCAL_OWNER_ID",
    "CONTENT_MACHINE_DEPLOYMENT_MODE",
    "VERCEL",
)


class WorkflowAccessTest(unittest.IsolatedAsyncioTestCase):
    """Resolve principals for injected hosted and local configurations."""

    def setUp(self) -> None:
        self._previous_env = {key: os.environ.get(key) for key in _ENV_KEYS}
        self._clear_environment()

        def restore_environment() -> None:
            for key, value in self._previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.addCleanup(restore_environment)

    def _clear_environment(self) -> None:
        for key in _ENV_KEYS:
            os.environ.pop(key, None)

    def _configure_local(
        self, owner: str | None = "own_local", mode: str | None = "trusted_local"
    ) -> None:
        self._clear_environment()
        if mode is not None:
            os.environ["CONTENT_MACHINE_WORKFLOW_MODE"] = mode
        if owner is not None:
            os.environ["CONTENT_MACHINE_LOCAL_OWNER_ID"] = owner

    @staticmethod
    def _hosted_principal(owner: str = "own_A") -> Principal:
        return Principal(owner_id=owner, mode=PrincipalMode.HOSTED_VERIFIED)

    @staticmethod
    def _sync_auth(result):
        def authenticate(request: Request):
            return result

        return authenticate

    @staticmethod
    def _async_auth(result):
        async def authenticate(request: Request):
            return result

        return authenticate

    def _request(
        self,
        *,
        host: str | None = "127.0.0.1",
        authenticator=_UNSET,
        query: bytes = b"",
        headers: tuple[tuple[bytes, bytes], ...] = (),
        body: bytes = b"",
    ) -> tuple[Request, list[bool]]:
        app = FastAPI()
        if authenticator is not _UNSET:
            app.state.workflow_authenticator = authenticator
        path = "/api/workflow/items/itm_a"
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "root_path": "",
            "query_string": query,
            "headers": list(headers),
            "client": (host, 51234) if host is not None else None,
            "server": ("testserver", 80),
            "app": app,
        }
        body_reads: list[bool] = []

        async def receive() -> dict[str, object]:
            body_reads.append(True)
            return {"type": "http.request", "body": body, "more_body": False}

        return Request(scope, receive), body_reads

    async def _resolve_error(self, request: Request) -> WorkflowError:
        with self.assertRaises(WorkflowError) as raised:
            await resolve_principal(request)
        return raised.exception

    async def test_hosted_principal_ignores_spoofed_owner_inputs(self) -> None:
        os.environ["CONTENT_MACHINE_LOCAL_OWNER_ID"] = "own_B"
        headers = (
            (b"x-owner-id", b"own_B"),
            (b"x-forwarded-for", b"127.0.0.1"),
            (b"x-forwarded-user", b"own_B"),
            (b"authorization", b"Bearer verified-A"),
        )
        request, body_reads = self._request(
            host="203.0.113.10",
            authenticator=self._sync_auth(self._hosted_principal("own_A")),
            query=b"owner_id=own_B",
            headers=headers,
            body=b'{"owner_id":"own_B"}',
        )

        principal = await resolve_principal(request)

        self.assertEqual(principal.owner_id, "own_A")
        self.assertEqual(principal.mode, PrincipalMode.HOSTED_VERIFIED)
        self.assertEqual(body_reads, [])

    async def test_hosted_async_authenticator_keeps_a_and_b_distinct(self) -> None:
        for owner in ("own_A", "own_B"):
            with self.subTest(owner=owner):
                request, _ = self._request(
                    authenticator=self._async_auth(self._hosted_principal(owner))
                )
                principal = await resolve_principal(request)
                self.assertEqual(principal.owner_id, owner)
                self.assertEqual(principal.mode, PrincipalMode.HOSTED_VERIFIED)

    async def test_hosted_missing_or_malformed_authenticator_fails_closed(self) -> None:
        for label, authenticator in (
            ("absent", _UNSET),
            ("none", None),
            ("not callable", "workflow_authenticator"),
        ):
            with self.subTest(label=label):
                request, _ = self._request(authenticator=authenticator)
                error = await self._resolve_error(request)
                self.assertEqual(error.status_code, 503)
                self.assertEqual(error.code, AUTH_MISCONFIGURED)

    async def test_hosted_invalid_principal_results_fail_closed(self) -> None:
        malformed = (
            ("no principal", None),
            ("mapping instead of principal", {"owner_id": "own_A"}),
            (
                "wrong mode",
                Principal(owner_id="own_A", mode=PrincipalMode.TRUSTED_LOCAL),
            ),
            (
                "blank owner",
                Principal(owner_id="   ", mode=PrincipalMode.HOSTED_VERIFIED),
            ),
        )
        for label, result in malformed:
            with self.subTest(label=label):
                request, _ = self._request(
                    authenticator=self._sync_auth(result)
                )
                error = await self._resolve_error(request)
                self.assertEqual(error.status_code, 401)
                self.assertEqual(error.code, UNAUTHENTICATED)

    async def test_hosted_authenticator_exception_is_not_leaked(self) -> None:
        async def authenticate(request: Request):
            raise RuntimeError("provider secret")

        request, _ = self._request(authenticator=authenticate)
        error = await self._resolve_error(request)

        self.assertEqual(error.status_code, 401)
        self.assertEqual(error.code, UNAUTHENTICATED)
        self.assertNotIn("provider secret", error.detail)

    async def test_explicit_local_mode_accepts_loopback_and_ignores_spoofing(self) -> None:
        for host in ("127.0.0.1", "127.9.8.7", "::1"):
            with self.subTest(host=host):
                self._configure_local(owner="own_local")
                request, body_reads = self._request(
                    host=host,
                    authenticator=lambda request: self.fail(
                        "local mode must not call the hosted authenticator"
                    ),
                    query=b"owner_id=own_B",
                    headers=(
                        (b"x-owner-id", b"own_B"),
                        (b"x-forwarded-for", b"203.0.113.9"),
                    ),
                    body=b'{"owner_id":"own_B"}',
                )

                principal = await resolve_principal(request)

                self.assertEqual(principal.owner_id, "own_local")
                self.assertEqual(principal.mode, PrincipalMode.TRUSTED_LOCAL)
                self.assertEqual(body_reads, [])

    async def test_local_configuration_must_be_explicit_and_complete(self) -> None:
        cases = (
            ("implicit local", None, "own_local"),
            ("missing owner", "trusted_local", None),
            ("empty owner", "trusted_local", ""),
            ("blank owner", "trusted_local", "   "),
        )
        for label, mode, owner in cases:
            with self.subTest(label=label):
                self._configure_local(owner=owner, mode=mode)
                request, _ = self._request(host="127.0.0.1")
                error = await self._resolve_error(request)
                self.assertEqual(error.status_code, 503)
                self.assertEqual(error.code, AUTH_MISCONFIGURED)

    async def test_local_mode_rejects_remote_or_invalid_client_even_with_forwarded_headers(
        self,
    ) -> None:
        self._configure_local(owner="own_local")
        for host in ("203.0.113.9", "testclient", None):
            with self.subTest(host=host):
                request, _ = self._request(
                    host=host,
                    headers=(
                        (b"x-forwarded-for", b"127.0.0.1"),
                        (b"forwarded", b"for=127.0.0.1"),
                        (b"x-real-ip", b"127.0.0.1"),
                    ),
                )
                error = await self._resolve_error(request)
                self.assertEqual(error.status_code, 401)
                self.assertEqual(error.code, UNAUTHENTICATED)

    async def test_local_mode_is_prohibited_on_hosted_deployments(self) -> None:
        for label, deployment in (
            ("vercel", {"VERCEL": "1"}),
            ("deployment mode", {"CONTENT_MACHINE_DEPLOYMENT_MODE": "hosted"}),
            ("padded mode", {"CONTENT_MACHINE_DEPLOYMENT_MODE": " HOSTED "}),
        ):
            with self.subTest(label=label):
                self._configure_local(owner="own_local")
                os.environ.update(deployment)
                request, _ = self._request(host="127.0.0.1")
                error = await self._resolve_error(request)
                self.assertEqual(error.status_code, 503)
                self.assertEqual(error.code, AUTH_MISCONFIGURED)

    async def test_nonlocal_mode_never_falls_back_to_the_local_owner(self) -> None:
        self._configure_local(owner="own_local", mode="local")
        request, _ = self._request(host="127.0.0.1")
        error = await self._resolve_error(request)
        self.assertEqual(error.status_code, 503)
        self.assertEqual(error.code, AUTH_MISCONFIGURED)

        request, _ = self._request(
            host="127.0.0.1",
            authenticator=self._sync_auth(self._hosted_principal("own_A")),
        )
        principal = await resolve_principal(request)
        self.assertEqual(principal.owner_id, "own_A")
        self.assertEqual(principal.mode, PrincipalMode.HOSTED_VERIFIED)


class WorkflowErrorTest(unittest.TestCase):
    def test_error_exposes_http_metadata_and_acknowledged_current(self) -> None:
        current = {
            "working_revision": 2,
            "stage": "draft_review",
            "updated_at": "2026-11-05T09:12:00.000Z",
            "active_approval_id": None,
        }
        error = WorkflowError(
            status_code=409,
            code="revision_conflict",
            detail="Revision changed",
            current=current,
        )

        self.assertEqual(error.status_code, 409)
        self.assertEqual(error.code, "revision_conflict")
        self.assertEqual(error.detail, "Revision changed")
        self.assertEqual(str(error), "Revision changed")
        self.assertEqual(error.current, current)
        current["working_revision"] = 99
        self.assertEqual(error.current["working_revision"], 2)

    def test_acknowledged_current_is_optional(self) -> None:
        error = WorkflowError(401, UNAUTHENTICATED, "Authentication required")
        self.assertIsNone(error.current)
