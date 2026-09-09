"""Router tests — offline fakes + optional live relay smoke.

Run: python tests/test_router.py
Live smoke (1 relay call): set CONTENT_MACHINE_LIVE=1
"""

from __future__ import annotations

import sys
from pathlib import Path

import anthropic  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.router import messages_adapter  # noqa: E402
from content_machine.router.base import (  # noqa: E402
    AllRoutesFailed, ModelError, ModelRouter, ProviderError, Route,
)
from content_machine.schemas import CouncilScores  # noqa: E402


class FakeAdapter:
    """Scripted outcomes per model: value | Exception instance."""

    def __init__(self, outcomes: dict[str, object]):
        self.outcomes = outcomes
        self.calls: list[str] = []
        self.last_kwargs: dict = {}

    def complete(self, model, prompt, *, system=None, schema=None, **kwargs):
        self.calls.append(model)
        self.last_kwargs = kwargs
        out = self.outcomes.get(model)
        if isinstance(out, Exception):
            raise out
        return out


def make_router(adapters: dict[str, FakeAdapter], route_models=None, **kw) -> ModelRouter:
    routes = {name: Route(name=name, protocol="messages", adapter=a) for name, a in adapters.items()}
    return ModelRouter(routes=routes, route_models=route_models or {"*": list(adapters)}, **kw)


def test_first_model_success() -> None:
    r = make_router({"r1": FakeAdapter({"m1": "ok"})})
    assert r.complete(["m1"], "p") == "ok"


def test_provider_failover_same_model() -> None:
    r = make_router({
        "r1": FakeAdapter({"m1": ProviderError("down")}),
        "r2": FakeAdapter({"m1": "ok-r2"}),
    })
    assert r.complete(["m1"], "p") == "ok-r2"


def test_model_error_advances_layer() -> None:
    r = make_router({
        "r1": FakeAdapter({"m1": ModelError("context overflow"), "m2": "ok-m2"}),
    })
    assert r.complete(["m1", "m2"], "p") == "ok-m2"


def test_all_fail() -> None:
    r = make_router({"r1": FakeAdapter({"m1": ProviderError("x"), "m2": ModelError("y")})})
    try:
        r.complete(["m1", "m2"], "p")
    except AllRoutesFailed as e:
        assert len(e.errors) == 2
    else:
        raise AssertionError("expected AllRoutesFailed")


def test_classify_status() -> None:
    c = messages_adapter.classify_status
    assert c(500, "boom") is ProviderError
    assert c(429, "rate") is ProviderError
    assert c(401, "auth") is ProviderError
    assert c(400, "maximum context length exceeded") is ModelError
    assert c(400, "refusal: content policy") is ModelError
    assert c(400, "weird schema complaint") is ModelError
    assert c(None, "moderation block") is ModelError


def test_parse_retry(monkeypatch=None) -> None:
    adapter = messages_adapter.MessagesAdapter(base_url="http://invalid.local", api_key="x")

    class FakeParse:
        def __init__(self):
            self.n = 0

        def parse(self, **kw):
            self.n += 1
            if self.n == 1:
                raise ValueError("EOF while parsing")

            class R:
                parsed_output = CouncilScores(
                    narrative=8, velocity=7, depth=9, slop_purity=6,
                    threshold_met=False, verdict="revise", required_actions=["tighten hook"],
                )
            return R()

    fake = FakeParse()

    class FakeMessages:
        def __getattr__(self, name):
            return getattr(fake, name)

    class FakeClient:
        messages = FakeMessages()

    adapter._client = FakeClient()
    out = adapter.complete("m", "p", schema=CouncilScores)
    assert isinstance(out, CouncilScores) and fake.n == 2

    # exhaust retries -> ModelError
    class AlwaysBad(FakeMessages):
        def parse(self, **kw):
            raise ValueError("bad json")

    fake2 = AlwaysBad()

    class FakeClient2:
        messages = fake2

    adapter._client = FakeClient2()
    try:
        adapter.complete("m", "p", schema=CouncilScores)
    except ModelError:
        pass
    else:
        raise AssertionError("expected ModelError after retries")


def test_plain_json_fallback() -> None:
    """Relay translates old-generation parse into response_format=json_object
    and 400s; adapter must degrade to explicit JSON prompting."""
    import httpx

    adapter = messages_adapter.MessagesAdapter(base_url="http://invalid.local", api_key="x")

    class FakeText:
        type = "text"

        def __init__(self, text):
            self.text = text

    class FakeResp:
        def __init__(self, text):
            self.content = [FakeText(text)]
            self.stop_reason = "end_turn"

    class FakeMessages:
        def parse(self, **kw):
            resp = httpx.Response(400, request=httpx.Request("POST", "http://x"))
            raise anthropic.BadRequestError(
                "'messages' must contain the word 'json'", response=resp, body=None
            )

        def create(self, **kw):
            return FakeResp(
                '{"narrative": 8, "velocity": 7, "depth": 9, "slop_purity": 6,'
                ' "threshold_met": false, "verdict": "revise",'
                ' "required_actions": ["cut the preamble"]}'
            )

    class FakeClient:
        messages = FakeMessages()

    adapter._client = FakeClient()
    out = adapter.complete("m", "p", schema=CouncilScores)
    assert isinstance(out, CouncilScores) and out.narrative == 8


def test_latency_cap_does_not_skip_sole_route() -> None:
    r = make_router(
        {"r1": FakeAdapter({"m1": "ok-slow"})},
        preferred_max_latency_s=50.0,
    )
    # Artificially record high latency on sole route
    r._health_for("r1", "m1").record(95.0, ok=True)
    # It should still execute because it is the sole route
    assert r.complete(["m1"], "p") == "ok-slow"


def test_latency_cap_skips_when_alternative_available() -> None:
    r = make_router(
        {
            "r1": FakeAdapter({"m1": "ok-slow"}),
            "r2": FakeAdapter({"m1": "ok-fast"}),
        },
        preferred_max_latency_s=50.0,
    )
    # Artificially record high latency on r1
    r._health_for("r1", "m1").record(95.0, ok=True)
    # r1 should be skipped in favor of r2
    assert r.complete(["m1"], "p") == "ok-fast"
    assert "r1" not in [a for a in r.routes["r1"].adapter.calls]


def test_router_forwards_thinking_and_extra_params() -> None:
    fake = FakeAdapter({"m1": "reasoned-output"})
    r = make_router({"r1": fake})
    out = r.complete(
        ["m1"], "p",
        thinking={"type": "enabled", "budget_tokens": 4096},
        extra_body={"reasoning_effort": "high"},
    )
    assert out == "reasoned-output"
    assert fake.last_kwargs.get("thinking") == {"type": "enabled", "budget_tokens": 4096}
    assert fake.last_kwargs.get("extra_body") == {"reasoning_effort": "high"}


def live_smoke() -> None:
    from content_machine.config import load_config
    from content_machine.router import router_from_config

    cfg = load_config()
    router = router_from_config(cfg)
    draft = ("Last quarter we killed our most popular feature. Onboarding completion rose 22 percent. "
             "Score this draft as one judge on the editorial council.")
    prompt = ("You are one judge on a content editorial council. Score the draft on four dimensions, "
              "0.0 to 10.0 each.\n\nDRAFT:\n" + draft)
    result = router.complete([cfg.models.writer], prompt, schema=CouncilScores)
    assert isinstance(result, CouncilScores)
    print(f"LIVE OK: narrative={result.narrative} verdict={result.verdict}")


def main() -> None:
    import os

    for fn in (test_first_model_success, test_provider_failover_same_model,
               test_model_error_advances_layer, test_all_fail, test_classify_status,
               test_parse_retry, test_plain_json_fallback,
               test_latency_cap_does_not_skip_sole_route,
               test_latency_cap_skips_when_alternative_available,
               test_router_forwards_thinking_and_extra_params):
        fn()
        print(f"PASS {fn.__name__}")
    if os.environ.get("CONTENT_MACHINE_LIVE") == "1":
        live_smoke()
    else:
        print("live smoke skipped (set CONTENT_MACHINE_LIVE=1)")
    print("ALL PASS")


if __name__ == "__main__":
    main()
