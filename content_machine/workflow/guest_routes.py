"""Guest bootstrap requires verified anonymous identity before opening storage.

No automatic startup seed, browser ownership claims, transfer, or persistence
configuration is introduced here. Hosted deployment still requires its reviewed
authenticator and explicit durable connection factory.
"""
import sqlite3

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from content_machine.workflow.access import resolve_principal
from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.guests import VerifiedGuestSession, bootstrap_guest
from content_machine.workflow.http import commit_workflow_mutation, get_workflow_connection
from content_machine.workflow.schemas import Principal

router = APIRouter()


class GuestBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


def verified_guest(request: Request, principal: Principal = Depends(resolve_principal)) -> VerifiedGuestSession:
    authenticator = getattr(request.app.state, 'workflow_authenticator', None)
    verifier = getattr(authenticator, 'verify_session', None)
    if not callable(verifier):
        raise WorkflowError(503, 'guest_auth_unavailable', 'Guest session verification is unavailable.')
    parts = request.headers.get('Authorization', '').split()
    try:
        session = verifier(parts[1]) if len(parts) == 2 and parts[0].lower() == 'bearer' else None
    except Exception:
        session = None
    if (not isinstance(session, VerifiedGuestSession) or session.is_anonymous is not True
            or not isinstance(session.principal, Principal)
            or session.principal.mode.value != 'hosted_verified'
            or principal.mode.value != 'hosted_verified'
            or session.principal.owner_id != principal.owner_id):
        raise WorkflowError(401, 'unauthenticated', 'A verified anonymous session is required.')
    return session


@router.post('/guest/bootstrap')
def bootstrap_guest_workspace(
    payload: GuestBootstrapRequest,
    session: VerifiedGuestSession = Depends(verified_guest),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
) -> dict:
    # This proof is an in-process verifier result, never request JSON. The
    # existing service retains its own proof checks and transaction semantics.
    return commit_workflow_mutation(conn, lambda: bootstrap_guest(conn, session, lambda proof: proof))
