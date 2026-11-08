"""Shared HTTP seams for the workflow API.

Authentication is resolved before the request-scoped database connection is
opened. In local operation, the connection factory defaults lazily to the app
``_make_db`` seam. Hosted deployments require an explicitly configured factory;
tests and hosted adapters may inject a trusted server-owned
factory through ``app.state.workflow_connection_factory``. Browser input never
supplies a database path or owner.

Workflow failures serialize as a readable ``detail`` and stable ``code``.
Acknowledged conflict metadata is merged at the top level. Request-validation
failures use the same shape with a readable string, while unrelated legacy
routes keep FastAPI's existing validation response.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from typing import Any, TypeVar

from fastapi import Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from content_machine.workflow.access import _hosted_deployment, resolve_principal
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.schemas import Principal

WORKFLOW_PREFIX = "/api/workflow"
INVALID_REQUEST = "invalid_request"
STORAGE_MISCONFIGURED = "workflow_storage_misconfigured"

T = TypeVar("T")


def workflow_error_response(error: WorkflowError) -> JSONResponse:
    """Serialize a workflow failure without losing acknowledged state."""

    payload: dict[str, Any] = {
        "detail": error.detail,
        "code": error.code,
    }
    if error.current is not None:
        payload.update(error.current)
    return JSONResponse(status_code=error.status_code, content=payload)


def workflow_validation_response(
    error: RequestValidationError,
) -> JSONResponse:
    """Return one readable 422 string for a workflow request error."""

    errors = error.errors()
    if not errors:
        detail = "Invalid workflow request"
    else:
        first = errors[0]
        location = ".".join(
            str(part)
            for part in first.get("loc", ())
            if part not in ("body", "query", "path")
        )
        message = str(first.get("msg", "Invalid request"))
        detail = (
            f"Invalid workflow request: {location}: {message}"
            if location
            else f"Invalid workflow request: {message}"
        )
    return JSONResponse(
        status_code=422,
        content={"detail": detail, "code": INVALID_REQUEST},
    )


def commit_workflow_mutation(
    conn: sqlite3.Connection, operation: Callable[[], T]
) -> T:
    """Commit request-owned work before the caller builds a success response.

    Accepted workflow services use a savepoint when the trusted factory has
    already started the request transaction. The HTTP boundary owns that outer
    transaction: commit it here before acknowledging success, or roll it back
    and propagate the failure. Never commit from dependency teardown after a
    response may have been sent.
    """

    try:
        result = operation()
        if conn.in_transaction:
            conn.commit()
    except BaseException:
        if conn.in_transaction:
            conn.rollback()
        raise
    return result


def get_workflow_connection(
    request: Request,
    _principal: Principal = Depends(resolve_principal),
) -> Iterator[sqlite3.Connection]:
    """Open after authentication and always close the request connection."""

    factory = getattr(
        request.app.state, "workflow_connection_factory", None
    )
    if factory is None:
        if _hosted_deployment():
            raise WorkflowError(
                503,
                STORAGE_MISCONFIGURED,
                'Hosted workspace durable storage is not configured. Saving is unavailable.',
            )
        from content_machine.api.app import _make_db

        factory = _make_db
    if not callable(factory):
        raise WorkflowError(
            503,
            STORAGE_MISCONFIGURED,
            "Workflow storage is not configured",
        )

    conn = factory()
    try:
        yield conn
    finally:
        conn.close()


__all__ = [
    "INVALID_REQUEST",
    "STORAGE_MISCONFIGURED",
    "WORKFLOW_PREFIX",
    "commit_workflow_mutation",
    "get_workflow_connection",
    "workflow_error_response",
    "workflow_validation_response",
]
