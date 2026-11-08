# Cloudflare Workers AI adapter

The opt-in `CloudflareWorkersAI` adapter implements the existing `Route.adapter.complete` interface. Construct it on the server with an explicit 32-character account ID, scoped API token and timeout. Pass a provider-native model ID through the existing model layer and select the route explicitly. No route or model is enabled by this module.

```python
from content_machine.router.base import ModelRouter, Route
from content_machine.router.cloudflare_workers_ai import CloudflareWorkersAI

adapter = CloudflareWorkersAI(account_id, api_token, timeout_s=30)
router = ModelRouter(
    {"cloudflare": Route("cloudflare", adapter.protocol, adapter)},
    {"@cf/": ["cloudflare"]},
)
result = router.complete([configured_model_id], prompt, schema=ResponseSchema)
```

The server must obtain the token from its credential manager or environment during explicit application configuration. Never put a token in source, a browser bundle, request text, or logs. The transport uses the fixed Cloudflare account Chat Completions endpoint, disables environment-derived proxies and redirects, caps input/output and validates requested Pydantic schemas locally. Provider and model failures surface through the existing router error types with redacted messages. The adapter has no automatic fallback to another provider or model.

November 7 configuration update: `config.json` now maps the exact evaluation model `@cf/qwen/qwen3.8-27b` to `cloudflare_workers_ai`, referencing `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` on the server. The existing relay wildcard and default writer/judge assignments remain unchanged. Select the provider-native ID explicitly to exercise this route; this configuration alone does not enable workflow AI or accept the model for production. Corrected live fixture checks passed LinkedIn, X and YouTube Shorts; long-form hit the 30-second deadline, so broad editorial/Council acceptance remains open. Main-checkout `docs/implementation/local-routing-auth-verification.md` contains the redacted evidence and limits.

The caller waits at most the configured timeout for the HTTP worker. A stalled native DNS or HTTP call can outlive that wait in a bounded background thread and retains a process-local concurrency slot until it exits. A public guest deployment still requires a shared budget, rate controls, an approved provider policy and a durable owner-isolated workspace. Provider model availability, pricing, quota, response format compatibility and editorial quality require a separate live evaluation with non-sensitive fixtures before enabling the route. The offline tests use in-memory HTTP transports only and make no provider calls.
