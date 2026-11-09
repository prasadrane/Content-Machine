"""Free-provider registry and router (offline; adapters are fakes or mock transports)."""
import math

import pytest

from content_machine.config import AppConfig
from content_machine.router import free_providers as fp
from content_machine.router.base import ModelError, ProviderRejected

ACCT = "a" * 32
CF = {"CLOUDFLARE_ACCOUNT_ID": ACCT, "CLOUDFLARE_API_TOKEN": "cf-secret-token"}
GEM = {"GEMINI_API_KEY": "gem-secret-key"}
CF_MODEL = "@cf/qwen/qwen3.8-27b"


def names(env):
    return [p.name for p in fp.available_providers(env)]


def test_availability_combinations():
    assert names({}) == []
    assert not fp.free_ai_available({})
    assert names(CF) == ["cloudflare_workers_ai"]
    assert names(GEM) == ["gemini"]
    assert names({**CF, **GEM}) == ["cloudflare_workers_ai", "gemini"]
    assert fp.free_ai_available(GEM)


def test_partial_or_malformed_cloudflare_credentials_unavailable():
    assert names({"CLOUDFLARE_ACCOUNT_ID": ACCT}) == []
    assert names({"CLOUDFLARE_API_TOKEN": "t"}) == []
    assert names({"CLOUDFLARE_ACCOUNT_ID": "short", "CLOUDFLARE_API_TOKEN": "t"}) == []
    assert names({"CLOUDFLARE_ACCOUNT_ID": ACCT, "CLOUDFLARE_API_TOKEN": "has space"}) == []
    assert names({**{"CLOUDFLARE_ACCOUNT_ID": "bad", "CLOUDFLARE_API_TOKEN": "t"}, **GEM}) == ["gemini"]


def test_defaults_to_process_environment(monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv(fp.ENV_ORDER, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert names(None) == ["gemini"]


def test_registry_order():
    assert [p.name for p in fp.REGISTRY[:2]] == ["cloudflare_workers_ai", "gemini"]


def test_order_override_and_allowlist():
    both = {**CF, **GEM}
    assert names({**both, fp.ENV_ORDER: "gemini,cloudflare_workers_ai"}) == ["gemini", "cloudflare_workers_ai"]
    assert names({**both, fp.ENV_ORDER: "gemini"}) == ["gemini"]
    assert names({**both, fp.ENV_ORDER: "nope, gemini ,bogus"}) == ["gemini"]
    assert names({**both, fp.ENV_ORDER: "gemini,gemini"}) == ["gemini"]
    # allowlisted but credentials missing -> unavailable
    assert names({**GEM, fp.ENV_ORDER: "cloudflare_workers_ai"}) == []


def test_alias_translation_per_provider():
    seen = {}

    class Rec:
        def complete(self, model, prompt, *, system=None, schema=None, **kw):
            seen.update(model=model, kw=kw)
            return "ok"

    cf, gem = fp.REGISTRY[0], fp.REGISTRY[1]
    for provider, strong, fast, timeout in [(cf, CF_MODEL, CF_MODEL, 30.0),
                                            (gem, "gemini-2.5-flash", "gemini-2.5-flash-lite", 25.0)]:
        alias = fp.AliasAdapter(provider, Rec())
        for given, expected in [("free-strong", strong), ("free-fast", fast), (strong, strong)]:
            assert alias.complete(given, "p") == "ok"
            assert seen["model"] == expected
            assert seen["kw"]["timeout_s"] == timeout
        alias.complete("free-fast", "p", timeout_s=5)
        assert seen["kw"]["timeout_s"] == 5
        assert provider.default_timeout_s == timeout


def test_cost_values():
    cf, gem = fp.REGISTRY[0], fp.REGISTRY[1]
    assert cf.cost(10_000, 2000) == math.ceil(((10_000 + 1024) * 450 + 2000 * 3200) / 11)
    assert cf.cost(0, 1) == math.ceil((1024 * 450 + 3200) / 11)
    assert gem.cost(1_000_000, 4096) == 1
    assert (cf.pool, gem.pool) == ("cloudflare-guest", "gemini-guest")


def test_provider_for():
    assert fp.provider_for("cloudflare_workers_ai", CF_MODEL).name == "cloudflare_workers_ai"
    assert fp.provider_for("cloudflare_workers_ai", "free-strong").name == "cloudflare_workers_ai"
    assert fp.provider_for("gemini", "gemini-2.5-flash-lite").name == "gemini"
    assert fp.provider_for("gemini", "free-fast").name == "gemini"
    assert fp.provider_for("gemini", CF_MODEL) is None
    assert fp.provider_for("messages", "free-strong") is None


def test_build_returns_expected_adapters_without_other_env():
    cf = fp.REGISTRY[0].build({**CF, "OTHER": "x"})
    assert cf.__class__.__name__ == "CloudflareWorkersAI"
    assert fp.REGISTRY[1].build({}) is None
    assert fp.REGISTRY[1].build(GEM).__class__.__name__ == "GeminiAdapter"


def _cfg(**council):
    return AppConfig.model_validate({
        "routes": {"relay": {"protocol": "messages", "base_url": "https://relay.example", "auth_token": "x"}},
        "route_models": {"*": ["relay"]},
        "models": {"writer": "qwen3.8-max", "council": council or {
            "a": "gemini-2.5-flash", "b": "qwen3.8-max", "c": "gemini-2.5-flash-lite"}},
    })


def test_router_has_no_relay_or_messages_route_and_maps_config():
    base = _cfg()
    router, cfg = fp.build_free_router({**CF, **GEM}, base)
    assert list(router.routes) == ["cloudflare_workers_ai", "gemini"]
    assert router.route_models == {"*": ["cloudflare_workers_ai", "gemini"]}
    assert router.fallthrough_model_errors is True
    assert all(r.protocol != "messages" for r in router.routes.values())
    assert cfg.routes == {} and cfg.route_models == {}
    assert cfg.models.writer == "free-strong"
    assert cfg.models.council == {"a": "free-fast", "b": "free-strong", "c": "free-fast"}
    assert "relay" in base.routes and base.models.writer == "qwen3.8-max"  # input untouched


def test_router_uses_load_config_by_default_and_orders_by_override():
    router, cfg = fp.build_free_router({**CF, **GEM, fp.ENV_ORDER: "gemini,cloudflare_workers_ai"})
    assert list(router.routes) == ["gemini", "cloudflare_workers_ai"]
    assert cfg.models.writer == "free-strong"
    assert all(v in ("free-strong", "free-fast") for v in cfg.models.council.values())


def test_no_provider_raises_without_secrets():
    with pytest.raises(RuntimeError) as raised:
        fp.build_free_router({"CLOUDFLARE_API_TOKEN": "cf-secret-token"}, _cfg())
    assert "cf-secret-token" not in str(raised.value)
    assert "free AI provider" in str(raised.value)


class Scripted:
    def __init__(self, outcome):
        self.outcome, self.calls = outcome, []

    def complete(self, model, prompt, *, system=None, schema=None, **kw):
        self.calls.append((model, kw))
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _router_with(monkeypatch, first, second):
    monkeypatch.setattr(fp, "_BUILDERS", {
        "cloudflare_workers_ai": lambda env, t: first,
        "gemini": lambda env, t: second,
    })
    return fp.build_free_router({**CF, **GEM}, _cfg())[0]


@pytest.mark.parametrize("failure", [ProviderRejected("429"), ModelError("bad output")])
def test_falls_through_from_failing_first_provider(monkeypatch, failure):
    first, second = Scripted(failure), Scripted("from-gemini")
    router = _router_with(monkeypatch, first, second)
    assert router.complete(["free-strong"], "hi") == "from-gemini"
    assert first.calls[0][0] == CF_MODEL
    assert second.calls[0][0] == "gemini-2.5-flash"
    assert second.calls[0][1]["timeout_s"] == 25.0


def test_all_failing_raises_without_secrets(monkeypatch):
    from content_machine.router.base import AllRoutesFailed

    router = _router_with(monkeypatch, Scripted(ProviderRejected("a")), Scripted(ModelError("b")))
    with pytest.raises(AllRoutesFailed) as raised:
        router.complete(["free-fast"], "hi")
    assert len(raised.value.errors) == 2


def test_extensibility_third_provider_is_picked_up(monkeypatch):
    third = Scripted("from-third")
    dummy = fp.FreeProvider(
        name="dummy", protocol="dummy", pool="dummy-guest", unit_label="requests",
        env_vars=("DUMMY_KEY",), native_models=frozenset({"dummy-1"}),
        aliases={"free-strong": "dummy-1", "free-fast": "dummy-1"}, default_timeout_s=10.0,
        builder=lambda env, t: third if env.get("DUMMY_KEY") else None,
    )
    monkeypatch.setattr(fp, "REGISTRY", [*fp.REGISTRY, dummy])
    env = {"DUMMY_KEY": "d", **CF}
    assert names(env) == ["cloudflare_workers_ai", "dummy"]
    assert fp.provider_for("dummy", "free-fast") is dummy
    assert names({"DUMMY_KEY": ""}) == []

    router, _ = fp.build_free_router(env, _cfg())
    assert list(router.routes) == ["cloudflare_workers_ai", "dummy"]
    # real cloudflare adapter would hit the network; replace it with a failing fake
    router.routes["cloudflare_workers_ai"].adapter.adapter = Scripted(ProviderRejected("down"))
    assert router.complete(["free-strong"], "hi") == "from-third"
    assert third.calls[0] == ("dummy-1", {"timeout_s": 10.0})
