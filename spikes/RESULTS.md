# Spike Results — 2026-09-04

## Environment discovered

- LLM access on this machine = Aliyun Token Plan gateway ONLY.
  - Base: `https://token-plan.ap-southeast-1.maas.aliyuncs.com`
  - Anthropic Messages protocol relay at `/apps/anthropic` (env `ANTHROPIC_BASE_URL`).
  - No OpenAI-protocol path exists (probed `/compatible-mode/v1`, `/apps/openai/v1`, `/v1` → 401/404).
  - Token-plan key does NOT authenticate against standard DashScope OpenAI-compatible endpoint.
  - Catalog (bl model list): qwen3.8-max / qwen3.8-flash / qwen3.8-opensource / qwen3.7-max / qwen3.7-plus / qwen3.7-flash / qwen3.6-{max,plus,flash} + wan-video. **Qwen family only. Zero non-Qwen text families.**
  - "Claude" model slots in this session map to qwen3.8-max/flash via env overrides.
- Hardware: i7-1255U (12 threads), 16GB RAM, Intel Iris Xe iGPU. **No NVIDIA GPU, no CUDA.**
- Installed: Python 3.11.9, anthropic 1.4.0, openai 2.41.0, pydantic 2.11.7, google-genai, sentence-transformers 6.0.0. No faster-whisper/whisper.cpp/ffmpeg yet.

## Spike 1+2 — Structured outputs (DONE, scope-limited)

Script: `archive/spike_structured_outputs.py` (archived 2026-09-09; CouncilScores replica superseded by `content_machine.schemas`). Council schema: 4 float scores (0-10), bool, enum verdict, actions array. Tests: T1 reliability, T2 numeric-bound stress, T3 enum stress.

### Relay (Anthropic SDK → gateway /apps/anthropic, model qwen3.8-max)

| Test | n | JSON parsed | Pydantic-valid | Notes |
| :--- | :--- | :--- | :--- | :--- |
| T1 reliability | 3 | 3/3 | 2/3 | 1 malformed JSON (EOF mid-string) |
| T2 bound stress | 3 | 3/3 | 2/3 | 1 trial emitted narrative=26.94, velocity>10 — bounds NOT enforced |
| T3 enum stress | 2 | 2/2 | 2/2 | prompt pressure for out-of-set verdict resisted |

- `messages.parse(output_format=PydanticModel)` accepted through relay. Latency 29-50s/call (slow; relay + qwen3.8-max reasoning).
- **No grammar-constrained guarantee**: JSON can be malformed; numeric bounds not enforced. Pydantic client-side validation caught every violation → plan v2 §9 rule confirmed empirically.
- Real Anthropic grammar-constrained testing impossible here (no real Anthropic endpoint). Pass-1 finding P1-F9 stands as evidence, unreplicated locally.

### Qwen native (OpenAI-compatible / DashScope)

- Blocked: token-plan credentials rejected on `/compatible-mode/v1` (401) and all other paths (404).
- Would need a separate standard DashScope API key to test native `response_format json_schema`.

### Blocked parity items

- OpenAI Structured Outputs API, Gemini structured output: no keys. Test harness ready in spike script (add providers).

## Spike 3 — ASR feasibility (verdict, benchmark deferred)

- No CUDA → CPU-only ASR. This reshapes plan v2 §3.1:
  - **Batch engine: faster-whisper int8** (small or base to start). Parakeet/Canary not practical without GPU (NeMo CPU throughput poor; research WER wins were GPU-measured).
  - **Live path: whisper.cpp** small/base model, chunked streaming on CPU. Expect seconds-level latency per utterance — fine for transcript monitoring, not keystroke-fast.
  - WER on operator's voice unknown. Benchmark needs: `pip install faster-whisper` + ffmpeg + 1-2 min voice recording from user.

## Spike 4 — Judge calibration (BLOCKED)

- Needs 20 human-scored anchor drafts + judge endpoints from ≥4 model families.
- Single-family gateway makes calibration meaningless for the bias findings it exists to operationalize (P1-F3/F5 require cross-family panels). Unblocks after external keys exist.

## Spike 5 — Slack bookmarks (BLOCKED on token)

- Design confirmed by research (P2-F1): `conversations.list` → `bookmarks.list`, scope `bookmarks:read`, ~100 bookmarks/channel cap, starred items dropped.
- Needs: Slack bot or user token with `bookmarks:read` + `channels:read` (+ `groups:read` for private channels).

## Spike 6 — Gmail OAuth (user-interactive)

Checklist for the user:
1. console.cloud.google.com → create/select project.
2. APIs & Services → enable Gmail API.
3. OAuth consent screen → External, add `.../auth/gmail.readonly` scope, add own address as test user.
4. Credentials → OAuth client ID → Desktop app → download JSON → save as `~/.content_machine/secrets/gcp_oauth_client.json`.
5. First run uses installed-app flow (browser popup) to mint refresh token; store refresh token locally.
Budget: 20-40 min including Google's verification screens for test-user mode.

## Architecture impact (headline)

1. **Plan v2 council design (5 distinct families) cannot run on this gateway.** Only Qwen family available. Options:
   - OpenRouter key (one purchase, many families, documented multi-model failover — matches P1-F2 pattern);
   - direct keys: Anthropic + OpenAI + Google + one of Mistral/DeepSeek;
   - accept single-family panel with documented bias risk (contradicts P1-F3/F5; not recommended).
2. Gateway layer in `ModelRouter` must speak Anthropic Messages protocol for the token-plan route; OpenAI-compatible for OpenRouter/other routes. Thin router abstraction confirmed necessary (plan v2 §8.2 design holds).
3. Pydantic-always rule (§9) is now locally proven, not just evidence-cited.
4. ASR plan (§3.1) needs rewrite for CPU-only: faster-whisper batch + whisper.cpp live; Parakeet dropped unless GPU later added.
5. bl CLI auto-updated 1.14.2 → 1.20.0 during `bl config show` despite user choosing to stay on 1.14.2 (CLI self-update behavior).
