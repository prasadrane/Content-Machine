"""GeminiAdapter: request shape, text join, error mapping (offline)."""
import json

import httpx
import pytest

from content_machine.router.base import ModelError, ProviderError
from content_machine.router.gemini import GeminiAdapter


def _handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    if request.url.path.endswith(":generateContent"):
        if request.headers.get("x-goog-api-key") != "test-key":
            return httpx.Response(400, json={"error": "bad key"})
        if body.get("contents")[0]["parts"][0]["text"] == "boom429":
            return httpx.Response(429, json={"error": "quota"})
        if body.get("contents")[0]["parts"][0]["text"] == "boom400":
            return httpx.Response(400, json={"error": "schema"})
        if body.get("contents")[0]["parts"][0]["text"] == "empty":
            return httpx.Response(200, json={"candidates": [{"content": {"parts": []}}]})
        parts = [{"text": "hello "}, {"text": "world"}]
        resp = {"candidates": [{"content": {"parts": parts}}]}
        if body.get("systemInstruction"):
            resp["echo_system"] = body["systemInstruction"]["parts"][0]["text"]
        return httpx.Response(200, json=resp)
    return httpx.Response(404)


@pytest.fixture()
def adapter(monkeypatch):
    transport = httpx.MockTransport(_handler)
    monkeypatch.setattr(httpx, "post", lambda url, **kw: httpx.Client(transport=transport).post(url, **kw))
    return GeminiAdapter(api_key="test-key")


def test_joins_part_texts(adapter):
    assert adapter.complete("gemini-2.5-flash", "hi") == "hello world"


def test_system_becomes_system_instruction(adapter):
    adapter.complete("gemini-2.5-flash", "hi", system="be terse")
    # request shape asserted via echo in handler-backed response is indirect;
    # direct assertion:
    captured = {}

    def spy(url, **kw):
        captured.update(kw)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    import content_machine.router.gemini as g
    orig = g.httpx.post
    g.httpx = httpx  # keep attr patchable
    try:
        import unittest.mock as mock
        with mock.patch.object(httpx, "post", side_effect=spy):
            GeminiAdapter(api_key="test-key").complete("m", "p", system="be terse")
    finally:
        g.httpx.post = orig
    assert captured["json"]["systemInstruction"] == {"parts": [{"text": "be terse"}]}
    assert captured["headers"]["x-goog-api-key"] == "test-key"
    assert captured["json"]["contents"] == [{"role": "user", "parts": [{"text": "p"}]}]


def test_429_maps_to_provider_error(adapter):
    with pytest.raises(ProviderError):
        adapter.complete("m", "boom429")


def test_400_maps_to_model_error(adapter):
    with pytest.raises(ModelError):
        adapter.complete("m", "boom400")


def test_empty_candidates_maps_to_model_error(adapter):
    with pytest.raises(ModelError):
        adapter.complete("m", "empty")


def test_missing_key_rejected():
    with pytest.raises(ValueError):
        GeminiAdapter(api_key="")


def test_make_router_builds_gemini_route_and_skips_without_key(monkeypatch, tmp_path):
    from content_machine.bootstrap import make_router
    from content_machine.config import AppConfig

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    cfg = AppConfig.model_validate({
        "routes": {"gemini": {"protocol": "gemini", "api_key_env": "GEMINI_API_KEY"}},
        "route_models": {"*": ["gemini"]},
    })
    router = make_router(cfg)
    assert "gemini" not in router.routes  # skipped, no key

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    router = make_router(cfg)
    assert "gemini" in router.routes
    assert router.routes["gemini"].adapter.__class__.__name__ == "GeminiAdapter"


def test_schema_returns_validated_model_and_sends_response_schema():
    import json as _json
    from unittest import mock

    import httpx as _httpx

    from content_machine.router.gemini import GeminiAdapter
    from content_machine.schemas import CouncilScores

    captured = {}
    payload = _json.dumps({
        "narrative": 9.0, "velocity": 8.5, "depth": 9.2, "slop_purity": 9.4,
        "threshold_met": True, "verdict": "pass", "required_actions": ["none"],
    })

    def spy(url, **kw):
        captured.update(kw)
        return _httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": payload}]}}]})

    with mock.patch.object(_httpx, "post", side_effect=spy):
        out = GeminiAdapter(api_key="k").complete("m", "p", schema=CouncilScores)
    assert isinstance(out, CouncilScores)
    assert out.verdict == "pass"
    gen = captured["json"]["generationConfig"]
    assert gen["responseMimeType"] == "application/json"
    assert gen["responseSchema"]["properties"]["threshold_met"]["type"] == "BOOLEAN"
    assert gen["responseSchema"]["properties"]["verdict"]["enum"] == ["pass", "revise", "reject"]
    assert gen["responseSchema"]["properties"]["required_actions"]["type"] == "ARRAY"


def test_schema_invalid_json_maps_to_model_error():
    from unittest import mock

    import httpx as _httpx

    from content_machine.router.base import ModelError
    from content_machine.router.gemini import GeminiAdapter
    from content_machine.schemas import CouncilScores

    def spy(url, **kw):
        return _httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{\"narrative\": "}]}}]})

    with mock.patch.object(_httpx, "post", side_effect=spy):
        with pytest.raises(ModelError):
            GeminiAdapter(api_key="k").complete("m", "p", schema=CouncilScores)
