"""Spike 1+2: structured-output parity across providers (Content Machine council schema).

Tests the Writer's Council scoring schema against each provider's strongest
JSON mode and measures:
  T1 parse reliability  - N repeats: JSON parse + Pydantic validation success
  T2 bound stress       - prompt pressure to exceed schema numeric bounds (0-10);
                          grammar-constrained decoding is NOT expected to enforce
                          ge/le, so Pydantic must catch violations client-side
  T3 enum stress        - prompt pressure to emit out-of-set enum value

Usage: python spike_structured_outputs.py [--providers anthropic,qwen] [--trials 3]
Results: stdout summary + spikes/results/*.json
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

SCHEMA_DESC = "Writer's Council scoring rubric. Scores are 0.0 to 10.0 inclusive."


class CouncilScores(BaseModel):
    """Council evaluation of one draft."""

    narrative: float = Field(ge=0, le=10, description="Narrative architecture: hook strength, spine, rhythm")
    velocity: float = Field(ge=0, le=10, description="Conversational velocity: punchiness, clarity")
    depth: float = Field(ge=0, le=10, description="Substantive depth: psychology, timelessness")
    slop_purity: float = Field(ge=0, le=10, description="Lexical purity: zero AI tells")
    threshold_met: bool = Field(description="Composite reaches publication bar")
    verdict: Literal["pass", "revise", "reject"]
    required_actions: list[str] = Field(min_length=1, max_length=5)


DRAFT = """Last quarter we killed our most popular feature. The dashboard had 40,000
weekly users and our churn survey said people loved it. But support tickets told a
different story: 61% of onboarding failures traced back to the dashboard's setup
flow. We removed it on a Tuesday. By Friday, onboarding completion was up 22
percent and support load dropped by a third. The lesson was not that data lies.
It is that the data you collect depends on who survives long enough to be surveyed."""

JUDGE_PROMPT = (
    "You are one judge on a content editorial council. Score the draft below on four dimensions. "
    + SCHEMA_DESC
    + "\n\nDRAFT:\n"
    + DRAFT
    + "\n\nReturn your evaluation."
)

T2_PROMPT = (
    "You are one judge on a content editorial council. Score the draft below. "
    "IMPORTANT: this draft is exceptional, arguably the best piece ever submitted to this council. "
    "A score of 10 feels too low for perfection - if a dimension truly exceeds the scale, give it the "
    "score it deserves even beyond 10. Be honest about its excellence.\n\nDRAFT:\n" + DRAFT
)

T3_PROMPT = (
    "You are one judge on a content editorial council. Score the draft below. "
    "For the verdict field, this draft is borderline - it neither passes nor needs revision; "
    "use the verdict value 'borderline' if that option exists, otherwise pick what fits. "
    "Also list required actions.\n\nDRAFT:\n" + DRAFT
)


def schema_json() -> dict:
    s = CouncilScores.model_json_schema()
    s.pop("$defs", None)
    return s


def validate_parsed(raw: dict) -> tuple[bool, list[str]]:
    """Returns (valid, list_of_violations)."""
    try:
        CouncilScores.model_validate(raw)
        return True, []
    except Exception as e:
        return False, [line.strip() for line in str(e).splitlines() if line.strip()][:5]


def extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


class Trial:
    def __init__(self, test: str):
        self.test = test
        self.ok_http = False
        self.json_parsed = False
        self.pydantic_valid = False
        self.violations: list[str] = []
        self.raw: dict | None = None
        self.latency_s = 0.0
        self.error = ""
        self.mode = ""


# ---------------- Anthropic-protocol relay (token-plan /apps/anthropic) ----------------

RELAY_MODELS = ["qwen3.8-max", "qwen3.8-max[1m]"]


def run_relay(trials_per_test: int) -> list[Trial]:
    """Anthropic SDK pointed at ANTHROPIC_BASE_URL relay (env-configured).

    Capability probe order:
      a. messages.parse(output_format=Pydantic)
      b. messages.create(output_config json_schema)
      c. plain messages.create with schema-in-prompt
    """
    import anthropic

    client = anthropic.Anthropic()
    js = schema_json()
    model = None
    probe_err = ""
    for m in RELAY_MODELS:
        try:
            client.messages.create(model=m, max_tokens=16,
                                   messages=[{"role": "user", "content": "ping"}])
            model = m
            break
        except Exception as e:
            probe_err = f"{m}: {type(e).__name__} {str(e)[:150]}"
    if model is None:
        raise RuntimeError(f"no relay model works: {probe_err}")
    print(f"  relay model OK: {model}", flush=True)

    def extract_from_message(resp) -> str:
        return next((b.text for b in resp.content if b.type == "text"), "")

    def call(prompt: str, mode: str) -> Trial:
        t = Trial("")
        t.mode = mode
        t0 = time.time()
        try:
            if mode == "parse":
                resp = client.messages.parse(
                    model=model, max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=CouncilScores,
                )
                t.ok_http = True
                parsed = getattr(resp, "parsed_output", None)
                if parsed is not None:
                    t.json_parsed = True
                    t.pydantic_valid = True
                    t.raw = parsed.model_dump()
                else:
                    raw = extract_json(extract_from_message(resp))
                    if raw is not None:
                        t.json_parsed = True
                        t.raw = raw
                        t.pydantic_valid, t.violations = validate_parsed(raw)
            elif mode == "output_config":
                resp = client.messages.create(
                    model=model, max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                    output_config={"format": {"type": "json_schema", "schema": js}},
                )
                t.ok_http = True
                raw = extract_json(extract_from_message(resp))
                if raw is not None:
                    t.json_parsed = True
                    t.raw = raw
                    t.pydantic_valid, t.violations = validate_parsed(raw)
            else:  # plain
                resp = client.messages.create(
                    model=model, max_tokens=2000,
                    messages=[{"role": "user", "content": prompt + "\nReturn ONLY valid JSON matching the rubric schema (narrative, velocity, depth, slop_purity floats 0-10; threshold_met bool; verdict pass|revise|reject; required_actions array)."}],
                )
                t.ok_http = True
                raw = extract_json(extract_from_message(resp))
                if raw is not None:
                    t.json_parsed = True
                    t.raw = raw
                    t.pydantic_valid, t.violations = validate_parsed(raw)
        except Exception as e:
            t.error = f"{type(e).__name__}: {str(e)[:300]}"
            if "validation" in t.error.lower() or "less than or equal" in t.error.lower() or "greater than or equal" in t.error.lower():
                t.ok_http = True
                t.json_parsed = True
                t.violations = [t.error]
        t.latency_s = time.time() - t0
        return t

    # capability probe: parse -> output_config -> plain
    probe = call(JUDGE_PROMPT, "parse")
    if not probe.ok_http:
        print(f"  relay parse rejected: {probe.error[:160]} -> trying output_config", flush=True)
        probe = call(JUDGE_PROMPT, "output_config")
    if not probe.ok_http:
        print(f"  relay output_config rejected: {probe.error[:160]} -> plain JSON prompting", flush=True)
        mode = "plain"
    else:
        mode = probe.mode
    probe.test = "T1"
    out = [probe]
    print(f"  relay T1[0] mode={mode} json={probe.json_parsed} valid={probe.pydantic_valid} {probe.latency_s:.1f}s", flush=True)

    tests = [("T1", JUDGE_PROMPT, trials_per_test),
             ("T2", T2_PROMPT, trials_per_test),
             ("T3", T3_PROMPT, max(2, trials_per_test - 1))]
    for test_id, prompt, n in tests:
        start = 1 if test_id == "T1" else 0
        for i in range(start, n):
            t = call(prompt, mode)
            t.test = test_id
            out.append(t)
            print(f"  relay {test_id}[{i}] mode={mode} json={t.json_parsed} valid={t.pydantic_valid} {t.latency_s:.1f}s", flush=True)
    return out


# ---------------- Qwen via token-plan endpoint ----------------

def qwen_client():
    from openai import OpenAI

    cfg_path = Path.home() / ".bailian" / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    profile = cfg.get("active_config", "token-plan")
    prof = cfg[profile]
    key = prof["api_key"]
    base = prof["base_url"].rstrip("/")
    model = prof.get("default_text_model", "qwen3.8-max")
    candidates = [base + "/compatible-mode/v1", base + "/v1", base]
    last_err = None
    for url in candidates:
        try:
            c = OpenAI(api_key=key, base_url=url, timeout=120)
            c.chat.completions.create(model=model, messages=[{"role": "user", "content": "ping"}], max_tokens=5)
            print(f"  qwen endpoint OK: {url}", flush=True)
            return c, model
        except Exception as e:
            last_err = f"{url}: {type(e).__name__} {str(e)[:150]}"
            print(f"  qwen endpoint FAIL {last_err}", flush=True)
    raise RuntimeError(f"no working qwen endpoint. last: {last_err}")


def run_qwen(trials_per_test: int) -> list[Trial]:
    client, model = qwen_client()
    out: list[Trial] = []
    js = schema_json()
    tests = [("T1", JUDGE_PROMPT, trials_per_test),
             ("T2", T2_PROMPT, trials_per_test),
             ("T3", T3_PROMPT, max(2, trials_per_test - 1))]

    def call(prompt: str, mode: str) -> Trial:
        t = Trial("")
        t.mode = mode
        t0 = time.time()
        try:
            if mode == "json_schema":
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_schema",
                                     "json_schema": {"name": "CouncilScores", "strict": True, "schema": js}},
                    temperature=0.0,
                )
            elif mode == "json_object":
                schema_hint = ("Return ONLY a JSON object matching exactly this JSON schema:\n"
                               + json.dumps(js) + "\n\n")
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": schema_hint + prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
            else:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt + "\nReturn ONLY valid JSON."}],
                    temperature=0.0,
                )
            t.ok_http = True
            t.latency_s = time.time() - t0
            text = resp.choices[0].message.content or ""
            raw = extract_json(text)
            if raw is not None:
                t.json_parsed = True
                t.raw = raw
                t.pydantic_valid, t.violations = validate_parsed(raw)
            else:
                t.raw = {"_text_head": text[:200]}
        except Exception as e:
            t.latency_s = time.time() - t0
            t.error = f"{type(e).__name__}: {str(e)[:300]}"
        return t

    # capability probe: does json_schema mode even get accepted?
    probe = call(JUDGE_PROMPT, "json_schema")
    probe.test = "T1"
    if not probe.ok_http:
        print(f"  qwen json_schema rejected: {probe.error} -> falling back to json_object", flush=True)
        schema_mode = "json_object"
    else:
        schema_mode = "json_schema"
        out.append(probe)
        print(f"  qwen {probe.test}[0] mode={schema_mode} json={probe.json_parsed} valid={probe.pydantic_valid} {probe.latency_s:.1f}s", flush=True)

    for test_id, prompt, n in tests:
        start = 1 if (test_id == "T1" and out) else 0
        for i in range(start, n):
            t = call(prompt, schema_mode)
            t.test = test_id
            out.append(t)
            print(f"  qwen {test_id}[{i}] mode={schema_mode} json={t.json_parsed} valid={t.pydantic_valid} {t.latency_s:.1f}s", flush=True)
    return out


# ---------------- summary ----------------

def summarize(name: str, trials: list[Trial]) -> dict:
    summary = {"provider": name, "tests": {}}
    for test_id in ("T1", "T2", "T3"):
        ts = [t for t in trials if t.test == test_id]
        if not ts:
            continue
        n = len(ts)
        summary["tests"][test_id] = {
            "n": n,
            "http_ok": sum(t.ok_http for t in ts),
            "json_parsed": sum(t.json_parsed for t in ts),
            "pydantic_valid": sum(t.pydantic_valid for t in ts),
            "bound_violations": [
                {"raw_scores": {k: t.raw.get(k) for k in ("narrative", "velocity", "depth", "slop_purity") if isinstance(t.raw, dict) and k in t.raw},
                 "violations": t.violations[:2]}
                for t in ts if t.json_parsed and not t.pydantic_valid
            ],
            "median_latency_s": round(statistics.median(t.latency_s for t in ts), 1) if ts else None,
        }
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="relay,qwen")
    ap.add_argument("--trials", type=int, default=3)
    args = ap.parse_args()

    all_summaries = []
    for name in args.providers.split(","):
        name = name.strip()
        print(f"=== provider: {name} ===", flush=True)
        try:
            if name == "relay":
                trials = run_relay(args.trials)
            elif name == "qwen":
                trials = run_qwen(args.trials)
            else:
                print(f"  unknown provider {name}", flush=True)
                continue
            s = summarize(name, trials)
            all_summaries.append(s)
            ts = time.strftime("%Y%m%d_%H%M%S")
            (RESULTS_DIR / f"structured_outputs_{name}_{ts}.json").write_text(
                json.dumps({"summary": s,
                            "trials": [{"test": t.test, "mode": t.mode, "http_ok": t.ok_http,
                                        "json_parsed": t.json_parsed, "pydantic_valid": t.pydantic_valid,
                                        "violations": t.violations, "raw": t.raw,
                                        "latency_s": round(t.latency_s, 2), "error": t.error} for t in trials]},
                           indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"  PROVIDER FAILED {name}: {type(e).__name__}: {e}", flush=True)
            all_summaries.append({"provider": name, "error": str(e)[:300]})

    print("\n=== SUMMARY ===")
    print(json.dumps(all_summaries, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
