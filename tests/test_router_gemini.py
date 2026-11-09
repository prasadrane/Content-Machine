"""GeminiAdapter: request shape, text join, error mapping (offline)."""
import json

import httpx
import pytest

from content_machine.router.base import ModelError, ProviderError, ProviderRejected
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
def adapter():
    return GeminiAdapter(api_key="test-key", transport=httpx.MockTransport(_handler))


def _spy_adapter(captured, text="ok", status=200, timeout_s=60.0):
    def handler(request):
        captured["json"] = json.loads(request.content)
        captured["headers"] = dict(request.headers)
        captured["timeout"] = request.extensions.get("timeout")
        if status != 200:
            return httpx.Response(status, text="LEAK-BODY secret-k")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    return GeminiAdapter(api_key="secret-k", timeout_s=timeout_s, transport=httpx.MockTransport(handler))


def test_joins_part_texts(adapter):
    assert adapter.complete("gemini-2.5-flash", "hi") == "hello world"


def test_system_becomes_system_instruction():
    captured = {}
    _spy_adapter(captured).complete("m", "p", system="be terse")
    assert captured["json"]["systemInstruction"] == {"parts": [{"text": "be terse"}]}
    assert captured["headers"]["x-goog-api-key"] == "secret-k"
    assert captured["json"]["contents"] == [{"role": "user", "parts": [{"text": "p"}]}]


def test_429_maps_to_provider_rejected(adapter):
    with pytest.raises(ProviderRejected):
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
    from content_machine.schemas import CouncilScores

    captured = {}
    payload = json.dumps({
        "narrative": 9.0, "velocity": 8.5, "depth": 9.2, "slop_purity": 9.4,
        "threshold_met": True, "verdict": "pass", "required_actions": ["none"],
    })
    out = _spy_adapter(captured, text=payload).complete("m", "p", schema=CouncilScores)
    assert isinstance(out, CouncilScores)
    assert out.verdict == "pass"
    gen = captured["json"]["generationConfig"]
    assert gen["responseMimeType"] == "application/json"
    assert gen["responseSchema"]["properties"]["threshold_met"]["type"] == "BOOLEAN"
    assert gen["responseSchema"]["properties"]["verdict"]["enum"] == ["pass", "revise", "reject"]
    assert gen["responseSchema"]["properties"]["required_actions"]["type"] == "ARRAY"


def test_schema_invalid_json_maps_to_model_error():
    from content_machine.schemas import CouncilScores

    with pytest.raises(ModelError):
        _spy_adapter({}, text='{"narrative": ').complete("m", "p", schema=CouncilScores)


def test_topic_briefing_schema_preserves_nested_question_objects():
    from content_machine.router.gemini import _gemini_schema
    from content_machine.schemas import TopicBriefing

    schema = _gemini_schema(TopicBriefing)
    questions = schema["properties"]["questions"]
    assert questions["type"] == "ARRAY"
    assert questions["items"] == {
        "type": "OBJECT",
        "properties": {
            "persona": {"type": "STRING"},
            "focus": {"type": "STRING"},
            "question": {"type": "STRING"},
        },
        "required": ["persona", "focus", "question"],
    }


@pytest.mark.parametrize("model", ["gemini-2.5-flash", "gemini-2.5-flash-lite"])
def test_flash_models_always_disable_thinking(monkeypatch, model):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    captured = {}
    _spy_adapter(captured).complete(model, "hello")
    assert captured["json"]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_non_flash_model_keeps_default_thinking():
    captured = {}
    _spy_adapter(captured).complete("gemini-2.5-pro", "hello")
    assert "generationConfig" not in captured["json"]


def test_max_tokens_becomes_max_output_tokens():
    captured = {}
    _spy_adapter(captured).complete("m", "hello", max_tokens=321)
    assert captured["json"]["generationConfig"]["maxOutputTokens"] == 321


def test_timeout_kwarg_clamped_to_constructor_timeout():
    captured = {}
    adapter = _spy_adapter(captured, timeout_s=10.0)
    adapter.complete("m", "p", timeout_s=3)
    assert captured["timeout"]["read"] == 3.0
    adapter.complete("m", "p", timeout_s=500)
    assert captured["timeout"]["read"] == 10.0
    adapter.complete("m", "p")
    assert captured["timeout"]["read"] == 10.0
    with pytest.raises(ValueError):
        adapter.complete("m", "p", timeout_s=0)


def test_client_ignores_env_and_redirects(monkeypatch):
    seen = {}
    real = httpx.Client

    def spy_client(*a, **kw):
        seen.update(kw)
        return real(*a, **kw)

    monkeypatch.setattr(httpx, "Client", spy_client)
    _spy_adapter({}).complete("m", "p")
    assert seen["trust_env"] is False and seen["follow_redirects"] is False


@pytest.mark.parametrize("status,exc", [
    (401, ProviderRejected), (403, ProviderRejected), (429, ProviderRejected),
    (500, ProviderRejected), (503, ProviderRejected), (400, ModelError), (404, ModelError),
])
def test_status_mapping_and_no_leaks(status, exc):
    with pytest.raises(exc) as raised:
        _spy_adapter({}, status=status).complete("m", "p")
    text = str(raised.value)
    assert "LEAK-BODY" not in text and "secret-k" not in text
    assert str(status) in text


def test_network_error_does_not_leak_key():
    def boom(request):
        raise httpx.ConnectError("key secret-k in " + str(request.url), request=request)

    adapter = GeminiAdapter(api_key="secret-k", transport=httpx.MockTransport(boom))
    with pytest.raises(ProviderError) as raised:
        adapter.complete("m", "p")
    assert "secret-k" not in str(raised.value)
