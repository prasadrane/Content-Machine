"""Authenticated HTTP boundary for governed creator preferences."""
import sqlite3

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.http import commit_workflow_mutation, get_workflow_connection
from content_machine.workflow.preferences import list_preferences, mutate_preference, preference_history
from content_machine.workflow.schemas import Principal

router = APIRouter()


class CreatePreference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=10000)
    consent: bool


class EditPreference(CreatePreference):
    expected_revision: int = Field(ge=1)


class ActivatePreference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=1)
    consent: bool


class StopPreference(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=1)


@router.get('/preferences')
def get_preferences(principal: Principal = Depends(resolve_principal),
                    conn: sqlite3.Connection = Depends(get_workflow_connection)):
    return {'preferences': list_preferences(conn, principal)}


@router.get('/preferences/{preference_id}/history')
def get_history(preference_id: str, principal: Principal = Depends(resolve_principal),
                conn: sqlite3.Connection = Depends(get_workflow_connection)):
    return {'events': preference_history(conn, principal, preference_id)}


def _mutation(conn, principal, action, preference_id, payload, key):
    result = commit_workflow_mutation(
        conn, lambda: mutate_preference(conn, principal, action, preference_id,
                                        payload.model_dump(mode='json'), key or ''),
    )
    return JSONResponse(status_code=result.status_code, content=result.body)


@router.post('/preferences')
def create_preference(payload: CreatePreference,
                      principal: Principal = Depends(resolve_principal),
                      conn: sqlite3.Connection = Depends(get_workflow_connection),
                      key: str | None = Header(None, alias='Idempotency-Key')):
    return _mutation(conn, principal, 'create', None, payload, key)


@router.patch('/preferences/{preference_id}')
def edit_preference(preference_id: str, payload: EditPreference,
                    principal: Principal = Depends(resolve_principal),
                    conn: sqlite3.Connection = Depends(get_workflow_connection),
                    key: str | None = Header(None, alias='Idempotency-Key')):
    return _mutation(conn, principal, 'edit', preference_id, payload, key)


@router.post('/preferences/{preference_id}/activate')
def activate_preference(preference_id: str, payload: ActivatePreference,
                        principal: Principal = Depends(resolve_principal),
                        conn: sqlite3.Connection = Depends(get_workflow_connection),
                        key: str | None = Header(None, alias='Idempotency-Key')):
    return _mutation(conn, principal, 'activate', preference_id, payload, key)


@router.post('/preferences/{preference_id}/stop')
def stop_preference(preference_id: str, payload: StopPreference,
                    principal: Principal = Depends(resolve_principal),
                    conn: sqlite3.Connection = Depends(get_workflow_connection),
                    key: str | None = Header(None, alias='Idempotency-Key')):
    return _mutation(conn, principal, 'stop', preference_id, payload, key)


@router.post('/preferences/{preference_id}/reject')
def reject_preference(preference_id: str, payload: StopPreference,
                      principal: Principal = Depends(resolve_principal),
                      conn: sqlite3.Connection = Depends(get_workflow_connection),
                      key: str | None = Header(None, alias='Idempotency-Key')):
    return _mutation(conn, principal, 'reject', preference_id, payload, key)
