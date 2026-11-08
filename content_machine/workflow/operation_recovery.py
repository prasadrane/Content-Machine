"""Explicit, owner-scoped recovery of interrupted AI operations."""
import sqlite3

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StrictBool, field_validator

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.http import commit_workflow_mutation, get_workflow_connection
from content_machine.workflow.operations import get_operation
from content_machine.workflow.persistence import atomic_write, canonical_json
from content_machine.workflow.schemas import Principal, utc_timestamp

router = APIRouter()


class AbandonConfirmation(BaseModel):
    confirm: StrictBool

    @field_validator('confirm')
    @classmethod
    def require_confirmation(cls, value):
        if not value:
            raise ValueError('Explicit confirmation is required')
        return value


def abandon_operation(conn, principal, item_id, operation_id):
    with atomic_write(conn):
        operation = get_operation(conn, principal, item_id, operation_id)
        if operation['state'] == 'pending':
            error = {'code': 'operation_abandoned', 'detail': 'The creator abandoned this request.'}
            conn.execute("UPDATE workflow_operations SET state='failed', error_json=?, finished_at=? "
                         "WHERE owner_id=? AND item_id=? AND operation_id=? AND state='pending'",
                         (canonical_json(error), utc_timestamp(), principal.owner_id, item_id, operation_id))
            operation = get_operation(conn, principal, item_id, operation_id)
        return operation


@router.post('/items/{item_id}/operations/{operation_id}/abandon')
def abandon(item_id: str, operation_id: str, payload: AbandonConfirmation,
            principal: Principal = Depends(resolve_principal),
            conn: sqlite3.Connection = Depends(get_workflow_connection)):
    operation = commit_workflow_mutation(
        conn, lambda: abandon_operation(conn, principal, item_id, operation_id))
    return {'operation': operation}
