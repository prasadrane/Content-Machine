"""Authenticated discovery with an explicit deployment opt-in for safe RSS.

Set CONTENT_MACHINE_WORKFLOW_DISCOVERY_RSS=1 to use the process-isolated
transport. An injected app-state fetcher always takes precedence, including
explicit None to disable retrieval. No network is enabled by default.
"""
import os
import sqlite3

from fastapi import APIRouter, Depends, Request

from content_machine.workflow import discovery
from content_machine.workflow.access import resolve_principal
from content_machine.workflow.http import get_workflow_connection
from content_machine.workflow.schemas import Principal

router = APIRouter()
_UNSET = object()


def runtime_fetcher(app):
    fetcher = getattr(app.state, "workflow_discovery_fetcher", _UNSET)
    if fetcher is not _UNSET:
        return fetcher
    if os.environ.get("CONTENT_MACHINE_WORKFLOW_DISCOVERY_RSS") == "1":
        from content_machine.workflow.safe_rss import fetch
        return fetch
    return None


@router.post("/discovery/refresh")
def refresh_discovery(
    request: Request,
    principal: Principal = Depends(resolve_principal),
    conn: sqlite3.Connection = Depends(get_workflow_connection),
):
    fetch = runtime_fetcher(request.app)
    result = discovery.refresh(conn, principal, fetch)
    # A request-owned factory may open an enclosing transaction. Cache failure
    # must roll back that transaction without discarding valid feed results.
    if conn is not None and conn.in_transaction:
        try:
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            result.setdefault('cache_warnings', []).append({
                'message': 'Conditional feed metadata could not be saved; source results are preserved.',
            })
    return result
