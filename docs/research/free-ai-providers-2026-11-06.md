# Free AI API options for Content Machine

Verified against official sources on 2026-11-06 UTC. This review covers backend APIs for the application and its live guest mode. Published terms and quotas were checked. Account-specific access, response quality and live integration remain untested.

I recommend evaluating Cloudflare Workers AI and Groq first. Gemini is the quickest additional candidate for the existing codebase, with a separate decision about its unpaid-service data terms. OpenRouter is useful for controlled model experiments and low-volume fallback.

| Provider | Current free access | Fit for this application | Official evidence |
| --- | --- | --- | --- |
| Cloudflare Workers AI | 10,000 neurons daily on Workers Free. Usage stops at the allocation. Several frontier models require paid access. | First candidate for a bounded guest pool. Current smaller-model candidates include Gemma 4 26B A4B and Qwen 3.8 27B. | [Pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/), [current model migration notice](https://developers.cloudflare.com/changelog/post/2026-11-05-planned-model-deprecations/) |
| Groq | Free quotas vary by model and organization. The published GPT-OSS-120B and Qwen 3.8 27B rows show 30 requests/minute, 1,000/day, 8,000 tokens/minute and 200,000/day. The account limits page is authoritative. | First candidate for writing and review comparisons. Token limits need attention when several judges run together. | [Rate limits](https://console.groq.com/docs/rate-limits), [data controls](https://console.groq.com/docs/your-data) |
| Gemini Developer API | Current pricing lists free input/output for Gemini 3.8 Flash. Limits depend on the model, project and tier. | Existing native adapter reduces integration work. The unpaid-service data policy needs an explicit privacy decision for creator content. | [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [terms](https://ai.google.dev/gemini-api/terms) |
| OpenRouter | The current free-model collection lists 20 requests/minute and 50/day for free variants, with a higher daily allowance after a qualifying credit purchase. Availability also depends on the upstream provider. | Useful for comparing named free models. Pin model/provider choices and verify their individual data policies. | [Free collection and limits](https://openrouter.ai/collections/free-models), [privacy controls](https://openrouter.ai/docs/guides/privacy/data-collection) |
| Hugging Face Inference Providers | Free accounts receive $0.10 in monthly credits, subject to change. Extra usage requires purchased credits. | A small integration experiment allowance. Public guest capacity would depend on additional funding. | [Pricing](https://huggingface.co/docs/inference-providers/pricing) |
| Cerebras | Current pages describe limited trial credits. The pricing page advertises a one-time $5 promotion after adding a payment method, expiring after 30 days. Older cached documentation still advertises a standing free tier. | Evaluate through the current account console before treating it as ongoing free capacity. | [Current pricing](https://www.cerebras.ai/pricing), [current trial description](https://www.cerebras.ai/code) |
| Mistral | Current usage documentation says Free mode covers trying Vibe and Studio. API keys and API usage require billing activation and pay-as-you-go. Some experimental Labs models have zero model pricing. | Labs can support experiments, with billing and model-lifecycle conditions checked first. | [Current usage rules](https://docs.mistral.ai/admin/billing-usage/usage-limits), [Labs lifecycle](https://docs.mistral.ai/inference/model-lifecycle) |
| NVIDIA API Catalog | Developer access supports prototyping, research, development and testing. Production serving has separate licensing requirements. | Suitable for evaluation under the catalog terms. Public guest deployment requires a production-eligible hosting arrangement. | [Developer and production access](https://docs.api.nvidia.com/nim/docs/product) |

## Privacy and model selection

Cloudflare states that standard Workers AI inference retains content only while processing it, subject to documented exceptions, and that customer content is excluded from model training. Logging, storage, caching and other selected stateful features have their own retention behavior. Each model also has its own license terms. [Workers AI data usage](https://developers.cloudflare.com/workers-ai/platform/data-usage/)

Groq documents limited reliability/abuse retention and offers Zero Data Retention controls to all customers. Confirm the organization's settings before sending creator drafts. Features such as batch processing and fine-tuning have separate storage behavior. [Groq data controls](https://console.groq.com/docs/your-data)

Gemini's unpaid-service terms permit product-improvement use and human review of submitted content. Guest access can include a person's own notes, so sample seeding alone cannot establish that every request contains public material. Provider selection and fallback must honor the creator's chosen data policy. [Gemini terms](https://ai.google.dev/gemini-api/terms)

OpenRouter documents its own collection controls and differences among upstream providers. A named model, approved provider and recorded operation metadata make review results reproducible. Check actual account limits before allocating a shared guest pool. [Data collection](https://openrouter.ai/docs/guides/privacy/data-collection), [account limit reporting](https://openrouter.ai/docs/api_reference/limits)

Cloudflare announced model retirements on November 5, with listed removals scheduled for November 15. Candidate configurations should use the current replacement list and account catalog. [Model lifecycle update](https://developers.cloudflare.com/changelog/post/2026-11-05-planned-model-deprecations/)

## Integration work for the implementer

The shared API/CLI bootstrap already constructs the native Gemini adapter. Its other current branch constructs the Anthropic Messages adapter. An explicit OpenAI-compatible adapter and factory branch are needed for Groq, Cloudflare's compatible endpoint and OpenRouter. Tests must exercise the shared bootstrap and the retained router factory. Relevant source files are `content_machine/bootstrap.py`, `content_machine/router/__init__.py`, `content_machine/router/gemini.py` and `content_machine/config.py`.

Prepare three small provider packets after selecting the initial account and models.

1. Add the OpenAI-compatible adapter with schema validation, bounded retries, timeout handling and normal API/CLI factory tests. Preserve existing Messages and Gemini behavior.
2. Add explicit provider-native model IDs and environment-variable bindings for the approved routes. Capture the actual model/provider with each operation. Verify model availability, complete structured responses and failure handling through representative grounded drafts.
3. Add shared guest budgeting across server instances using the durable workspace store. Honor provider limits and retry hints. A free-only guest route must require an explicit configuration decision before it can use a paid fallback. Keep quota controls in the backend and preserve drafts when AI is unavailable.

The reviewed configuration has four Council judge slots and three samples per scored idea. Provider request counts therefore translate into fewer completed workflows. Measure actual prompt/output tokens, retries and editorial quality before presenting a capacity estimate. A provider's promotional speed or model ranking cannot establish writing quality for this app.

Groq also publishes Whisper transcription allowances. This is a candidate for hosted dictation if the deployment needs remote ASR, with the actual audio-processing path explained beside microphone controls. The local CPU transcription path remains available for local operation. [Groq limits](https://console.groq.com/docs/rate-limits)
