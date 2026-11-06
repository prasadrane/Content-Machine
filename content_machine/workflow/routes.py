"""Owned workflow item CRUD for the C09 API router.

Every route resolves the trusted principal and then opens one request-scoped
connection. Mutations pass the concrete Idempotency-Key to the accepted item
services and commit the enclosing request-owned transaction before returning
their status/body pair. Read responses contain actual stored content and owned
review/approval metadata only; absent records remain null.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from content_machine.workflow import approvals, items
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.http import (
    commit_workflow_mutation,
    get_workflow_connection,
)
from content_machine.workflow.persistence import WorkflowResult
from content_machine.workflow.schemas import (
    ContentItem,
    ItemCreate,
    ItemPatch,
    Principal,
    Review,
)

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

_REVIEW_SELECT = (
    "SELECT review_id, owner_id, item_id, input_version_id, request_id,"
    " state, actions_json, score_basis_json, proposals_json, model_config,"
    " started_at, finished_at FROM workflow_reviews"
)


def _result_response(result: WorkflowResult) -> JSONResponse:
    return JSONResponse(status_code=result.status_code, content=result.body)


def _summary(item: ContentItem) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "title": item.title,
        "destination": item.destination,
        "format": item.format,
        "stage": item.stage.value,
        "working_revision": item.working_revision,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _review_payload(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        f"{_REVIEW_SELECT} WHERE owner_id = ? AND item_id = ?"
        " ORDER BY COALESCE(started_at, '') DESC, review_id ASC LIMIT 1",
        (principal.owner_id, item_id),
    ).fetchone()
    if row is None:
        return None
    review = Review.model_validate(
        {
            "review_id": row["review_id"],
            "owner_id": row["owner_id"],
            "item_id": row["item_id"],
            "input_version_id": row["input_version_id"],
            "request_id": row["request_id"],
            "state": row["state"],
            "actions": json.loads(row["actions_json"] or "{}"),
            "score_basis": (
                json.loads(row["score_basis_json"])
                if row["score_basis_json"]
                else None
            ),
            "proposals": json.loads(row["proposals_json"] or "[]"),
            "model_config": row["model_config"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
        }
    )
    return review.model_dump(mode="json", by_alias=True)


def _approval_payload(
    conn: sqlite3.Connection,
    principal: Principal,
    item: ContentItem,
) -> dict[str, Any] | None:
    if item.active_approval_id is None:
        return None
    return approvals.get_approval(
        conn,
        principal,
        item.active_approval_id,
        item_id=item.item_id,
    ).model_dump(mode="json")


@router.post("/items")
def create_workflow_item(
    payload: ItemCreate,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key"
    ),
) -> JSONResponse:
    result = commit_workflow_mutation(
        conn,
        lambda: items.create_item(
            conn,
            principal,
            payload,
            request_id=idempotency_key or "",
        ),
    )
    return _result_response(result)


@router.get("/items")
def list_workflow_items(
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "items": [
                _summary(item)
                for item in items.list_items(conn, principal)
            ]
        },
    )


@router.get("/items/{item_id}")
def get_workflow_item(
    item_id: str,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
) -> JSONResponse:
    item = items.get_item(conn, principal, item_id)
    return JSONResponse(
        status_code=200,
        content={
            "item": item.model_dump(mode="json"),
            "review": _review_payload(conn, principal, item.item_id),
            "approval": _approval_payload(conn, principal, item),
        },
    )


@router.patch("/items/{item_id}")
def save_workflow_item(
    item_id: str,
    payload: ItemPatch,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key"
    ),
) -> JSONResponse:
    result = commit_workflow_mutation(
        conn,
        lambda: items.save_item(
            conn,
            principal,
            item_id,
            payload,
            request_id=idempotency_key or "",
        ),
    )
    return _result_response(result)


__all__ = ["router"]
