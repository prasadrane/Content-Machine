"""HTTP routes for creator-owned profile and source settings."""

import sqlite3
from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from content_machine.workflow import settings
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.http import commit_workflow_mutation, get_workflow_connection
from content_machine.workflow.schemas import Principal

router = APIRouter()


@router.get("/settings")
def get_settings(principal: Principal = Depends(resolve_principal),
                 conn: sqlite3.Connection = Depends(get_workflow_connection)):
    return {"profile": settings.get_profile(conn, principal), "sources": settings.list_sources(conn, principal)}


@router.put("/settings/profile")
def save_profile(payload: settings.ProfileSave, principal: Principal = Depends(resolve_principal),
                 conn: sqlite3.Connection = Depends(get_workflow_connection),
                 key: str | None = Header(None, alias="Idempotency-Key")):
    result = commit_workflow_mutation(conn, lambda: settings.save_profile(conn, principal, payload, request_id=key or ""))
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post("/settings/sources")
def create_source(payload: settings.SourceCreate, principal: Principal = Depends(resolve_principal),
                  conn: sqlite3.Connection = Depends(get_workflow_connection),
                  key: str | None = Header(None, alias="Idempotency-Key")):
    result = commit_workflow_mutation(conn, lambda: settings.create_source(conn, principal, payload, request_id=key or ""))
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.patch("/settings/sources/{source_id}")
def update_source(source_id: str, payload: settings.SourceUpdate,
                  principal: Principal = Depends(resolve_principal),
                  conn: sqlite3.Connection = Depends(get_workflow_connection),
                  key: str | None = Header(None, alias="Idempotency-Key")):
    result = commit_workflow_mutation(conn, lambda: settings.update_source(conn, principal, source_id, payload, request_id=key or ""))
    return JSONResponse(status_code=result.status_code, content=result.body)
