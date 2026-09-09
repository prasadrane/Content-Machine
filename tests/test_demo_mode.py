"""DEMO_MODE config override + /api/meta + council iteration cap."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def demo_env(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


def test_demo_mode_routes_to_gemini_flash(demo_env):
    from content_machine.config import load_config

    cfg = load_config()
    assert cfg.route_models == {"*": ["gemini"]}
    assert cfg.models.scanner.startswith("gemini-")
    assert cfg.models.council and all(m.startswith("gemini-") for m in cfg.models.council.values())
    assert "gemini" in cfg.routes


def test_no_demo_mode_unchanged(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    from content_machine.config import load_config

    cfg = load_config()
    assert cfg.route_models != {"*": ["gemini"]}


def test_demo_mode_without_key_unchanged(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    from content_machine.config import load_config

    cfg = load_config()
    assert cfg.route_models != {"*": ["gemini"]}


def test_meta_endpoint_reports_demo(demo_env):
    from content_machine.api.app import app

    with TestClient(app) as client:
        body = client.get("/api/meta").json()
    assert body["demo_mode"] is True
    assert body["llm"] == "gemini"


def test_meta_endpoint_reports_prod(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    from content_machine.api.app import app

    with TestClient(app) as client:
        body = client.get("/api/meta").json()
    assert body["demo_mode"] is False


def test_council_cap_in_demo(demo_env):
    from content_machine.api import app as app_mod

    assert app_mod.demo_council_max_iterations(requested=3) == 1
    assert app_mod.demo_council_max_iterations(requested=None) == 1


def test_council_cap_respects_request_in_prod(monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    from content_machine.api import app as app_mod

    assert app_mod.demo_council_max_iterations(requested=3) == 3


def test_seed_idempotent_on_second_cold_start(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTENT_MACHINE_HOME", str(tmp_path))
    from content_machine.demo_seed import seed_demo
    from content_machine.storage import db, paths

    paths.ensure_tree()
    conn = db.connect()
    try:
        first = seed_demo(conn)
        second = seed_demo(conn)
        assert first["spikes"] == 10
        assert second == {"spikes": 0, "lessons": 0, "iterations": 0, "comments": 0}
        n = conn.execute("SELECT COUNT(*) FROM spikes WHERE id LIKE 'demo-%'").fetchone()[0]
        assert n == 10
    finally:
        conn.close()
