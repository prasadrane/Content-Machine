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


def test_demo_seed_writes_synthetic_persona(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTENT_MACHINE_HOME", str(tmp_path))
    monkeypatch.setenv("DEMO_MODE", "1")
    from content_machine.demo_seed import seed_demo
    from content_machine.profile.manager import ProfileManager
    from content_machine.storage import db, paths

    paths.ensure_tree()
    conn = db.connect()
    try:
        seed_demo(conn)
    finally:
        conn.close()
    profile = ProfileManager(home_root=tmp_path).get_profile()
    assert profile.name == "John Doe"
    assert "Prasad" not in profile.full_markdown
    assert len(profile.hard_invariants) >= 5


def test_sync_seed_skipped_under_demo_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "1")
    from content_machine.storage import paths as paths_mod

    seed = tmp_path / "seed.md"
    runtime = tmp_path / "runtime.md"
    seed.write_text("REAL SEED", encoding="utf-8")
    runtime.write_text("demo synthetic", encoding="utf-8")
    paths_mod.sync_seed(seed, runtime)
    assert runtime.read_text(encoding="utf-8") == "demo synthetic"


# --- Quota-exhausted replay ---------------------------------------------------

def _seed_home(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTENT_MACHINE_HOME", str(tmp_path))
    from content_machine.demo_seed import seed_demo
    from content_machine.storage import db, paths

    paths.ensure_tree()
    conn = db.connect()
    try:
        seed_demo(conn)
    finally:
        conn.close()


def test_council_replays_seed_when_live_run_fails_in_demo(tmp_path, monkeypatch, demo_env):
    _seed_home(tmp_path, monkeypatch)
    from content_machine.api import app as app_mod

    def boom(**_kw):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(app_mod, "run_council", boom)
    monkeypatch.setattr(app_mod, "_make_router", lambda: object())
    with TestClient(app_mod.app) as client:
        r = client.post("/api/council/run", json={"draft": "my draft", "spike_id": "mine"})
    assert r.status_code == 200
    body = r.json()
    assert body["replayed"] is True
    assert body["score"] == 9.3
    assert body["draft"] is None  # never overwrite the user's draft with a replay


def test_council_failure_still_errors_outside_demo(tmp_path, monkeypatch):
    _seed_home(tmp_path, monkeypatch)
    monkeypatch.delenv("DEMO_MODE", raising=False)
    from content_machine.api import app as app_mod

    def boom(**_kw):
        raise RuntimeError("upstream down")

    monkeypatch.setattr(app_mod, "run_council", boom)
    monkeypatch.setattr(app_mod, "_make_router", lambda: object())
    with TestClient(app_mod.app, raise_server_exceptions=False) as client:
        r = client.post("/api/council/run", json={"draft": "my draft", "spike_id": "mine"})
    assert r.status_code == 500


def test_distribute_replays_seed_when_live_run_fails_in_demo(tmp_path, monkeypatch, demo_env):
    _seed_home(tmp_path, monkeypatch)
    from content_machine.api import app as app_mod
    from content_machine.distribution import engine as engine_mod

    def boom(self, *a, **k):
        raise RuntimeError("quota")

    monkeypatch.setattr(engine_mod.DistributionEngine, "generate_all", boom)
    monkeypatch.setattr(app_mod, "_make_router", lambda: object())
    with TestClient(app_mod.app) as client:
        r = client.post("/api/distribute/run", json={"anchor_post": "a long enough anchor post", "project_slug": "mine"})
    assert r.status_code == 200
    body = r.json()
    assert body["replayed"] is True
    assert body["linkedin"]
