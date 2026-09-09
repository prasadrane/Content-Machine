"""Shared bootstrap factories for the CLI and the FastAPI backend.

Unifies the previously duplicated wiring in ``content_machine/__main__.py``
and ``content_machine/api/app.py``:

- :func:`make_router` — build a ModelRouter from an AppConfig (+ environment).
- :func:`make_db` — open the live SQLite database.
- :func:`build_oracle_components` — assemble IdeaScorer + OracleOrchestrator
  from config thresholds.

Both entry points keep thin module-level delegates (``_make_router``,
``_make_db``, ``_build_oracle_components``) that call into this module at
call time, so existing tests can keep monkeypatching their own module's
names.  Connector classes and the scorer/orchestrator classes are passed in
by the caller (as its own module-level names) so those patch points are
preserved too.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Callable

from content_machine.config import AppConfig
from content_machine.router.base import ModelRouter, Route
from content_machine.router.messages_adapter import MessagesAdapter


def make_router(cfg: AppConfig) -> ModelRouter:
    """Build a ModelRouter from an already-loaded AppConfig / environment."""
    routes: dict = {}
    for name, rc in cfg.routes.items():
        base_url = os.environ.get(rc.base_url_env, "") if rc.base_url_env else rc.base_url or ""
        auth_token = os.environ.get(rc.auth_token_env, "") if rc.auth_token_env else rc.auth_token or ""
        api_key = os.environ.get(rc.api_key_env, "") if rc.api_key_env else rc.api_key or ""
        adapter = MessagesAdapter(
            base_url=base_url,
            auth_token=auth_token or api_key,
        )
        routes[name] = Route(name=name, protocol=rc.protocol, adapter=adapter)

    return ModelRouter(
        routes=routes,
        route_models=cfg.route_models,
        preferred_max_latency_s=cfg.thresholds.preferred_max_latency_s,
    )


def make_db(path: str | Path | None = None, init: bool = True) -> sqlite3.Connection:
    """Open the live SQLite database (defaults to the storage/db.py location)."""
    from content_machine.storage.db import connect

    return connect(path, init=init)


def build_oracle_components(
    *,
    cfg: AppConfig,
    router: Any,
    db_conn: sqlite3.Connection | None,
    connectors: list,
    scorer_cls: Callable,
    orchestrator_cls: Callable,
) -> tuple:
    """Wire IdeaScorer + OracleOrchestrator from cfg thresholds.

    Returns ``(orchestrator, scorer)``.  ``scorer_cls`` / ``orchestrator_cls``
    are injected by each caller (its own module-level ``IdeaScorer`` /
    ``OracleOrchestrator`` names) so test monkeypatching of those call sites
    keeps working.
    """
    scorer = scorer_cls(
        router=router,
        scanner_model=cfg.models.scanner,
        n_samples=cfg.thresholds.idea_samples,
        idea_gate=cfg.thresholds.idea_gate,
        idea_margin=cfg.thresholds.idea_margin,
    )
    orch = orchestrator_cls(connectors=connectors, scorer=scorer, db_conn=db_conn)
    return orch, scorer
