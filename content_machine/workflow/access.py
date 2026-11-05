"""Resolve the trusted workflow principal for one request.

Identity is established only by server-side configuration:

* Hosted mode calls ``request.app.state.workflow_authenticator``, an
  application-supplied callable that verifies the caller and returns a
  ``Principal(mode="hosted_verified")`` or no principal. Sync callables and
  awaitables are supported. Missing authenticator configuration fails closed.
* Trusted-local mode is enabled only by explicitly setting
  ``CONTENT_MACHINE_WORKFLOW_MODE=trusted_local`` together with a nonblank
  ``CONTENT_MACHINE_LOCAL_OWNER_ID``. The actual peer address must be a
  validated IPv4/IPv6 loopback address. Forwarding headers never grant local
  trust, and local mode is forbidden on hosted deployments.

Request bodies, query strings, owner fields and forwarding headers are never
identity inputs. Environment values are read per request; no principal is
persisted or cached.
"""

from __future__ import annotations

import inspect
import ipaddress
import os

from fastapi import Request

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.schema_types import PrincipalMode
from content_machine.workflow.schemas import Principal

WORKFLOW_MODE_ENV = "CONTENT_MACHINE_WORKFLOW_MODE"
LOCAL_OWNER_ENV = "CONTENT_MACHINE_LOCAL_OWNER_ID"
DEPLOYMENT_MODE_ENV = "CONTENT_MACHINE_DEPLOYMENT_MODE"

UNAUTHENTICATED = "unauthenticated"
AUTH_MISCONFIGURED = "workflow_auth_misconfigured"


def _unauthenticated(detail: str) -> WorkflowError:
    return WorkflowError(401, UNAUTHENTICATED, detail)


def _misconfigured(detail: str) -> WorkflowError:
    return WorkflowError(503, AUTH_MISCONFIGURED, detail)


def _trusted_local_requested() -> bool:
    mode = os.environ.get(WORKFLOW_MODE_ENV, "")
    return mode.strip().lower() == PrincipalMode.TRUSTED_LOCAL.value


def _hosted_deployment() -> bool:
    """Return whether this process is running on a hosted deployment."""

    deployment = os.environ.get(DEPLOYMENT_MODE_ENV, "")
    return "VERCEL" in os.environ or deployment.strip().lower() == "hosted"


def _resolve_local(request: Request) -> Principal:
    if _hosted_deployment():
        raise _misconfigured(
            "trusted local mode is not available on a hosted deployment"
        )

    owner_id = os.environ.get(LOCAL_OWNER_ENV)
    if owner_id is None or not owner_id.strip():
        raise _misconfigured(
            "trusted local mode requires CONTENT_MACHINE_LOCAL_OWNER_ID"
        )

    client = request.client
    if client is None:
        raise _unauthenticated("trusted local mode requires a loopback request")
    try:
        address = ipaddress.ip_address(client.host)
    except ValueError:
        raise _unauthenticated(
            "trusted local mode requires a loopback request"
        ) from None
    if not address.is_loopback:
        raise _unauthenticated("trusted local mode requires a loopback request")

    try:
        return Principal(owner_id=owner_id, mode=PrincipalMode.TRUSTED_LOCAL)
    except ValueError as exc:
        raise _misconfigured("configured local owner id is invalid") from exc


async def _resolve_hosted(request: Request) -> Principal:
    authenticator = getattr(request.app.state, "workflow_authenticator", None)
    if authenticator is None or not callable(authenticator):
        raise _misconfigured("workflow authentication is not configured")

    try:
        result = authenticator(request)
        if inspect.isawaitable(result):
            result = await result
    except Exception:
        raise _unauthenticated("authentication failed") from None

    if result is None:
        raise _unauthenticated("authentication required")
    if not isinstance(result, Principal):
        raise _unauthenticated("authentication failed")
    if result.mode != PrincipalMode.HOSTED_VERIFIED:
        raise _unauthenticated("authentication failed")
    if not result.owner_id.strip():
        raise _unauthenticated("authentication failed")
    return result


async def resolve_principal(request: Request) -> Principal:
    """Resolve the principal once for this request, failing closed."""

    if _trusted_local_requested():
        return _resolve_local(request)
    return await _resolve_hosted(request)


__all__ = [
    "AUTH_MISCONFIGURED",
    "UNAUTHENTICATED",
    "resolve_principal",
]
