"""Workflow history, explicit decisions, and exact export endpoints."""

import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse, Response

from content_machine.workflow import adaptations, approvals, exports, history
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.format_registry import capability_payloads
from content_machine.workflow.http import (
    commit_workflow_mutation,
    get_workflow_connection,
)
from content_machine.workflow.schemas import (
    AdaptRequest,
    ApproveRequest,
    Principal,
    RestoreRequest,
    SkipReviewRequest,
)
from content_machine.workflow.skip_review import skip_review
from content_machine.workflow.runtime import get_provider
from content_machine.workflow.versions import get_version

router = APIRouter()


@router.get("/capabilities")
def capabilities(request: Request, principal: Principal = Depends(resolve_principal)):
    pairs = capability_payloads()
    for pair in pairs:
        pair["can_generate"] = callable(get_provider(request.app, 'generate'))
        pair["can_review"] = callable(get_provider(request.app, 'review'))
    return {"principal": principal.model_dump(mode="json"), "pairs": pairs}


@router.get("/items/{item_id}/versions")
def versions(
    item_id: str,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
):
    return history.get_history(conn, principal, item_id)


@router.get("/items/{item_id}/versions/{version_id}")
def version_snapshot(
    item_id: str,
    version_id: str,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
):
    version = get_version(conn, principal, version_id, item_id=item_id)
    return {"version": version.model_dump(mode="json")}


@router.get("/items/{item_id}/exports/{version_id}")
def export(
    item_id: str,
    version_id: str,
    output: Literal["json"] | None = Query(None, alias="as"),
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
):
    result = exports.export_version(conn, principal, item_id, version_id)
    if output == "json":
        return JSONResponse(content=result.as_json())
    return Response(content=result.content, headers=result.headers)


@router.post("/items/{item_id}/skip-review")
def skip(
    item_id: str,
    payload: SkipReviewRequest,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    key: str | None = Header(None, alias="Idempotency-Key"),
):
    result = commit_workflow_mutation(
        conn,
        lambda: skip_review(conn, principal, item_id, payload, request_id=key or ""),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/items/{item_id}/approve")
def approve(
    item_id: str,
    payload: ApproveRequest,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    key: str | None = Header(None, alias="Idempotency-Key"),
):
    result = commit_workflow_mutation(
        conn,
        lambda: approvals.approve_item(
            conn, principal, item_id, payload, request_id=key or ""
        ),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/items/{item_id}/restore")
def restore(
    item_id: str,
    payload: RestoreRequest,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    key: str | None = Header(None, alias="Idempotency-Key"),
):
    result = commit_workflow_mutation(
        conn,
        lambda: history.restore_version(
            conn, principal, item_id, payload, request_id=key or ""
        ),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/items/{item_id}/adapt")
def adapt(
    item_id: str,
    payload: AdaptRequest,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    key: str | None = Header(None, alias="Idempotency-Key"),
):
    result = commit_workflow_mutation(
        conn,
        lambda: adaptations.adapt_version(
            conn, principal, item_id, payload, request_id=key or ""
        ),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)
