"""Tests for content_machine.bootstrap — shared CLI/API factory wiring.

Covers:
- make_router(cfg) -> ModelRouter with routes matching cfg
- make_db(...) -> sqlite3.Connection with expected tables (spikes, lessons)
- build_oracle_components(...) -> (orchestrator, scorer) wired from cfg (offline)
- asr.util.strip_timestamps — single shared implementation
- Delegates in __main__ / api.app remain the monkeypatch points:
  they must resolve bootstrap functions AND class names at call time.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from content_machine.config import (
    AppConfig,
    ModelsConfig,
    RouteConfig,
    ThresholdsConfig,
)


def _cfg() -> AppConfig:
    return AppConfig(
        routes={
            "alpha": RouteConfig(protocol="messages", base_url="https://a.example/v1", api_key="k1"),
            "beta": RouteConfig(protocol="messages", base_url_env="CM_TB_BETA_URL", auth_token_env="CM_TB_BETA_TOKEN"),
        },
        route_models={"*": ["alpha", "beta"]},
        models=ModelsConfig(scanner="scan-x"),
        thresholds=ThresholdsConfig(
            idea_gate=7.5, idea_margin=0.7, idea_samples=5, preferred_max_latency_s=42.0,
        ),
    )


# ---------------------------------------------------------------------------
# make_router
# ---------------------------------------------------------------------------

class TestMakeRouter:

    def test_returns_model_router_with_routes_matching_cfg(self):
        from content_machine.bootstrap import make_router
        from content_machine.router.base import ModelRouter

        router = make_router(_cfg())
        assert isinstance(router, ModelRouter)
        assert set(router.routes) == {"alpha", "beta"}
        assert router.route_models == {"*": ["alpha", "beta"]}
        assert router.preferred_max_latency_s == 42.0

    def test_routes_carry_protocol_and_adapter(self):
        from content_machine.bootstrap import make_router

        router = make_router(_cfg())
        r = router.routes["alpha"]
        assert r.name == "alpha"
        assert r.protocol == "messages"
        assert r.adapter is not None

    def test_env_vars_win_when_set(self, monkeypatch):
        from content_machine.bootstrap import make_router

        monkeypatch.setenv("CM_TB_BETA_URL", "https://env.example/v1")
        monkeypatch.setenv("CM_TB_BETA_TOKEN", "tok-123")
        router = make_router(_cfg())
        adapter = router.routes["beta"].adapter
        assert str(adapter._client.base_url).startswith("https://env.example")
        assert adapter._client.auth_token == "tok-123"


# ---------------------------------------------------------------------------
# make_db
# ---------------------------------------------------------------------------

class TestMakeDb:

    def test_returns_connection_with_expected_tables(self):
        from content_machine.bootstrap import make_db

        conn = make_db(":memory:")
        assert isinstance(conn, sqlite3.Connection)
        names = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"spikes", "lessons"} <= names
        conn.close()


# ---------------------------------------------------------------------------
# build_oracle_components
# ---------------------------------------------------------------------------

class TestBuildOracleComponents:

    def test_wires_scorer_and_orchestrator_from_cfg(self):
        from content_machine.bootstrap import build_oracle_components

        cfg = _cfg()
        router = object()
        conn = object()
        connectors = [object()]
        scorer_cls = MagicMock(name="IdeaScorer")
        orch_cls = MagicMock(name="OracleOrchestrator")

        orch, scorer = build_oracle_components(
            cfg=cfg,
            router=router,
            db_conn=conn,
            connectors=connectors,
            scorer_cls=scorer_cls,
            orchestrator_cls=orch_cls,
        )

        scorer_cls.assert_called_once_with(
            router=router,
            scanner_model="scan-x",
            n_samples=5,
            idea_gate=7.5,
            idea_margin=0.7,
        )
        orch_cls.assert_called_once_with(connectors=connectors, scorer=scorer, db_conn=conn)
        assert scorer is scorer_cls.return_value
        assert orch is orch_cls.return_value


# ---------------------------------------------------------------------------
# Delegates in __main__ / api.app must keep working as monkeypatch points
# ---------------------------------------------------------------------------

class TestDelegates:

    def test_main_make_router_delegates_at_call_time(self):
        import content_machine.__main__ as cli_main

        cfg = _cfg()
        with patch("content_machine.config.load_config", return_value=cfg), \
             patch("content_machine.bootstrap.make_router") as mock_make:
            result = cli_main._make_router()
        mock_make.assert_called_once_with(cfg)
        assert result is mock_make.return_value

    def test_main_make_db_delegates_at_call_time(self):
        import content_machine.__main__ as cli_main

        with patch("content_machine.bootstrap.make_db") as mock_db:
            result = cli_main._make_db()
        mock_db.assert_called_once_with()
        assert result is mock_db.return_value

    def test_main_build_oracle_components_uses_module_class_names(self, monkeypatch):
        """Patch points: tests patch content_machine.__main__.IdeaScorer/OracleOrchestrator."""
        import content_machine.__main__ as cli_main

        scorer_cls = MagicMock(name="IdeaScorer")
        orch_cls = MagicMock(name="OracleOrchestrator")
        monkeypatch.setattr(cli_main, "IdeaScorer", scorer_cls)
        monkeypatch.setattr(cli_main, "OracleOrchestrator", orch_cls)

        router = object()
        conn = object()
        orch, scorer = cli_main._build_oracle_components(
            cfg=_cfg(), router=router, db_conn=conn, connectors=[],
        )
        scorer_cls.assert_called_once()
        orch_cls.assert_called_once_with(connectors=[], scorer=scorer, db_conn=conn)
        assert orch is orch_cls.return_value

    def test_api_make_router_delegates_at_call_time(self):
        import content_machine.api.app as api_app

        cfg = _cfg()
        with patch("content_machine.config.load_config", return_value=cfg), \
             patch("content_machine.bootstrap.make_router") as mock_make:
            result = api_app._make_router()
        mock_make.assert_called_once_with(cfg)
        assert result is mock_make.return_value

    def test_api_make_db_delegates_at_call_time(self):
        import content_machine.api.app as api_app

        with patch("content_machine.bootstrap.make_db") as mock_db:
            result = api_app._make_db()
        mock_db.assert_called_once_with()
        assert result is mock_db.return_value

    def test_api_build_oracle_components_uses_module_class_names(self, monkeypatch):
        """Patch points: tests patch content_machine.api.app.IdeaScorer/OracleOrchestrator/_make_router."""
        import content_machine.api.app as api_app

        from content_machine.api.app import OracleRunRequest

        scorer_cls = MagicMock(name="IdeaScorer")
        orch_cls = MagicMock(name="OracleOrchestrator")
        db_mock = MagicMock(name="_make_db")
        monkeypatch.setattr(api_app, "IdeaScorer", scorer_cls)
        monkeypatch.setattr(api_app, "OracleOrchestrator", orch_cls)
        monkeypatch.setattr(api_app, "RSSConnector", MagicMock(name="RSSConnector"))
        monkeypatch.setattr(api_app, "_make_router", lambda: object())
        monkeypatch.setattr(api_app, "_make_db", db_mock)

        req = OracleRunRequest(rss_urls=["https://example.com/feed"], no_persist=False)
        orch, connectors = api_app._build_oracle_components(req)

        db_mock.assert_called_once_with()
        orch_cls.assert_called_once()
        kwargs = orch_cls.call_args.kwargs
        assert kwargs["connectors"] == connectors
        assert kwargs["db_conn"] is db_mock.return_value
        assert kwargs["scorer"] is scorer_cls.return_value
        assert orch is orch_cls.return_value

    def test_api_build_oracle_components_no_persist_skips_db(self, monkeypatch):
        import content_machine.api.app as api_app

        from content_machine.api.app import OracleRunRequest

        monkeypatch.setattr(api_app, "IdeaScorer", MagicMock())
        monkeypatch.setattr(api_app, "OracleOrchestrator", MagicMock())
        monkeypatch.setattr(api_app, "RSSConnector", MagicMock())
        monkeypatch.setattr(api_app, "_make_router", lambda: object())
        db_mock = MagicMock()
        monkeypatch.setattr(api_app, "_make_db", db_mock)

        req = OracleRunRequest(rss_urls=["https://example.com/feed"], no_persist=True)
        orch, connectors = api_app._build_oracle_components(req)

        db_mock.assert_not_called()
        assert len(connectors) == 1  # one RSSConnector per rss url


# ---------------------------------------------------------------------------
# asr.util.strip_timestamps
# ---------------------------------------------------------------------------

class TestStripTimestamps:

    def test_single_line(self):
        from content_machine.asr.util import strip_timestamps

        assert strip_timestamps("[00:00.100 --> 00:03.000]  Hello world") == "Hello world"

    def test_multi_line_joined(self):
        from content_machine.asr.util import strip_timestamps

        raw = (
            "[00:00.000 --> 00:03.000]  First sentence\n"
            "[00:03.500 --> 00:06.000]  Second sentence\n"
            "\n"
        )
        assert strip_timestamps(raw) == "First sentence Second sentence"

    def test_clean_text_untouched(self):
        from content_machine.asr.util import strip_timestamps

        assert strip_timestamps("plain prose\nsecond line") == "plain prose second line"

    def test_empty(self):
        from content_machine.asr.util import strip_timestamps

        assert strip_timestamps("") == ""

    def test_batch_and_live_share_implementation(self):
        from content_machine.asr import batch, live
        from content_machine.asr.util import strip_timestamps

        assert batch.strip_timestamps is strip_timestamps
        assert live.strip_timestamps is strip_timestamps
        assert not hasattr(batch, "_strip_timestamps")
        assert not hasattr(live, "_strip_timestamps")
