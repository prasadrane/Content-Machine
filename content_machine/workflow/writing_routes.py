"""Owned generation proposals with committed input identity and honest failures."""
import sqlite3

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.artifact_validation import validate_final_artifact
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.http import get_workflow_connection
from content_machine.workflow.operations import (
    begin_operation, complete_operation, decode_editorial_snapshot, fail_operation,
    get_operation, list_operations,
)
from content_machine.workflow.schemas import Artifact, GenerateRequest, Principal, ReviewRequest
from content_machine.workflow.reviews import record_review, validate_review_advice
from content_machine.workflow.runtime import get_provider
from content_machine.workflow.provider_execution import ProviderExecution

router = APIRouter()


def operation_response(operation):
    if operation['state'] == 'failed':
        error = operation.get('error') or {}
        actionable = error.get('code', '').startswith(('guest_', 'ai_session_'))
        return JSONResponse(status_code=error.get('status', 503) if actionable else 502, content={
            'detail': error['detail'] if actionable else 'The AI request failed. Your saved draft is preserved.',
            'code': error['code'] if actionable else 'provider_failed', 'operation': operation,
        })
    status = 202 if operation['state'] == 'pending' else 200
    return JSONResponse(status_code=status, content={'operation': operation})


def _provider_error(error, detail, execution):
    result = {'code': 'provider_failed', 'detail': detail}
    if isinstance(error, WorkflowError):
        result.update(code=error.code, detail=error.detail, status=error.status_code)
    if execution is not None and execution.calls:
        result['provider_calls'] = execution.calls
    return result


@router.get('/items/{item_id}/operations')
def operations(item_id: str, principal: Principal = Depends(resolve_principal),
               conn: sqlite3.Connection = Depends(get_workflow_connection)):
    return {'operations': list_operations(conn, principal, item_id)}


@router.get('/items/{item_id}/operations/{operation_id}')
def operation(item_id: str, operation_id: str,
              principal: Principal = Depends(resolve_principal),
              conn: sqlite3.Connection = Depends(get_workflow_connection)):
    return {'operation': get_operation(conn, principal, item_id, operation_id)}


@router.post('/items/{item_id}/generate')
def generate(item_id: str, payload: GenerateRequest, request: Request,
             principal: Principal = Depends(resolve_principal),
             conn: sqlite3.Connection = Depends(get_workflow_connection),
             key: str | None = Header(None, alias='Idempotency-Key')):
    generator = get_provider(request.app, 'generate')
    if not callable(generator):
        raise WorkflowError(503, 'generation_unavailable', 'AI drafting is unavailable. You can write your draft manually.')
    claimed, created = begin_operation(conn, principal, item_id, payload.expected_revision,
                                       'generate', key or '')
    if not created:
        return operation_response(claimed)
    snapshot = decode_editorial_snapshot(claimed['editorial_snapshot'])
    execution = None
    try:
        execution = ProviderExecution.for_request(request, principal, claimed['operation_id'])
        proposal = Artifact.model_validate(execution.invoke(generator, snapshot))
        validate_final_artifact(proposal, snapshot.destination, snapshot.format)
    except Exception as error:
        failed = fail_operation(conn, principal, item_id, claimed['operation_id'],
            _provider_error(error, 'AI drafting did not return a valid proposal.', execution))
        return operation_response(failed)
    completed = complete_operation(conn, principal, item_id, claimed['operation_id'], {
        'artifact': proposal.model_dump(mode='json'),
        'input_version_id': claimed['input_version_id'],
        **({'provider_calls': execution.calls} if execution.calls else {}),
    })
    return operation_response(completed)


@router.post('/items/{item_id}/review')
def review(item_id: str, payload: ReviewRequest, request: Request,
           principal: Principal = Depends(resolve_principal),
           conn: sqlite3.Connection = Depends(get_workflow_connection),
           key: str | None = Header(None, alias='Idempotency-Key')):
    reviewer = get_provider(request.app, 'review')
    if not callable(reviewer):
        raise WorkflowError(503, 'review_unavailable', 'Council review is unavailable. You can skip review and continue.')
    claimed, created = begin_operation(conn, principal, item_id, payload.expected_revision, 'review', key or '')
    if not created:
        return operation_response(claimed)
    snapshot = decode_editorial_snapshot(claimed['editorial_snapshot'])
    execution = None
    try:
        execution = ProviderExecution.for_request(request, principal, claimed['operation_id'])
        advice = validate_review_advice(execution.invoke(reviewer, snapshot), snapshot)
    except Exception as error:
        return operation_response(fail_operation(conn, principal, item_id, claimed['operation_id'],
            _provider_error(error, 'Council review did not return valid advice.', execution)))
    return operation_response(record_review(conn, principal, item_id, claimed['operation_id'], advice,
                                            provider_calls=execution.calls or None))
