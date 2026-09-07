"""Authorship obfuscation (plan v2 §5.1 rule 3).

Within a single model family the familiarity/perplexity component of judge
bias goes undiluted, so drafts are stripped of model-attribution hints before
scoring. Deliberately conservative: removes generation headers and model-family
tokens; never alters sentences that carry substantive content.
"""

from __future__ import annotations

import re

MODEL_TOKENS = re.compile(
    r"\b(qwen|claude|chatgpt|gpt-?\d[\w.-]*|gemini|llama|mistral|deepseek|anthropic|openai)\b",
    re.IGNORECASE,
)
GENERATED_HEADER = re.compile(
    r"^\s*(generated|written|drafted)\s+(by|with)\b.*$", re.IGNORECASE | re.MULTILINE
)


def obfuscate(draft: str) -> str:
    text = GENERATED_HEADER.sub("", draft)
    text = MODEL_TOKENS.sub("the model", text)
    return text.strip()
