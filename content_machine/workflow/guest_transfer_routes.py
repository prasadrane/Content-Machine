"""Explicit dual-session guest copy with authentication before storage."""
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, StrictBool

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession
from content_machine.workflow.guest_transfer import (
    copy_guest_workspace, get_transfer_receipt, preview_guest_copy,
)
from content_machine.workflow.http import commit_workflow_mutation, get_workflow_connection
from content_machine.workflow.schemas import Principal

router = APIRouter()


class CopyPreview(BaseModel):
    model_config = ConfigDict(extra='forbid')


class CopyRequest(CopyPreview):
    consent: StrictBool
    source_fingerprint: str


@dataclass(frozen=True)
class TransferSessions:
    guest: VerifiedGuestSession
    creator: VerifiedGuestSession


def _session(request, header, anonymous, principal=None):
    verifier = getattr(getattr(request.app.state, 'workflow_authenticator', None), 'verify_session', None)
    if not callable(verifier):
        raise WorkflowError(503, 'guest_auth_unavailable', 'Guest session verification is unavailable.')
    parts = request.headers.get(header, '').split()
    try:
        session = verifier(parts[1]) if len(parts) == 2 and parts[0].lower() == 'bearer' else None
    except Exception:
        session = None
    if (not isinstance(session, VerifiedGuestSession) or session.is_anonymous is not anonymous
            or not isinstance(session.principal, Principal) or session.principal.mode.value != 'hosted_verified'
            or (principal is not None and session.principal != principal)):
        raise WorkflowError(401, 'unauthenticated', 'The required verified session is unavailable.')
    return session


def verified_creator(request: Request, principal: Principal = Depends(resolve_principal)):
    return _session(request, 'Authorization', False, principal)


def transfer_sessions(request: Request, creator=Depends(verified_creator)):
    guest = _session(request, 'X-Guest-Authorization', True)
    if guest.principal.owner_id == creator.principal.owner_id:
        raise WorkflowError(409, 'invalid_transfer', 'Guest and creator sessions must be distinct.')
    return TransferSessions(guest, creator)


def transfer_connection(request: Request, sessions=Depends(transfer_sessions)):
    yield from get_workflow_connection(request, sessions.creator.principal)


def receipt_connection(request: Request, creator=Depends(verified_creator)):
    yield from get_workflow_connection(request, creator.principal)


@router.post('/guest/transfer/preview')
def preview(payload: CopyPreview, sessions=Depends(transfer_sessions), conn=Depends(transfer_connection)):
    return commit_workflow_mutation(conn, lambda: preview_guest_copy(
        conn, sessions.guest, sessions.creator, lambda proof: proof))


@router.post('/guest/transfer')
def transfer(payload: CopyRequest, sessions=Depends(transfer_sessions), conn=Depends(transfer_connection),
             request_id: str = Header(alias='Idempotency-Key')):
    return commit_workflow_mutation(conn, lambda: copy_guest_workspace(
        conn, sessions.guest, sessions.creator, lambda proof: proof,
        consent=payload.consent, request_id=request_id, source_fingerprint=payload.source_fingerprint))


@router.get('/guest/transfers/{transfer_id}')
def receipt(transfer_id: str, creator=Depends(verified_creator), conn=Depends(receipt_connection)):
    return get_transfer_receipt(conn, creator.principal, transfer_id)
