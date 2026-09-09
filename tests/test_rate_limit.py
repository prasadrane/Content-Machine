"""Per-IP POST rate limit middleware (demo quota guard)."""
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from content_machine.api.rate_limit import RateLimitMiddleware


def _app(limit: int) -> Starlette:
    async def echo(request):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/api/gen", echo, methods=["POST"]), Route("/api/health", echo)])
    app.add_middleware(RateLimitMiddleware, limit_per_min=limit)
    return app


def test_allows_under_limit():
    client = TestClient(_app(2))
    assert client.post("/api/gen").status_code == 200
    assert client.post("/api/gen").status_code == 200


def test_blocks_over_limit():
    client = TestClient(_app(2))
    client.post("/api/gen")
    client.post("/api/gen")
    resp = client.post("/api/gen")
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["detail"]


def test_get_requests_not_limited():
    client = TestClient(_app(1))
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health").status_code == 200
