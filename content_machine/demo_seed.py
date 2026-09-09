"""Synthetic demo-data seeder for showcase environments.

Used by:
- Local sanitized screenshot runs (CONTENT_MACHINE_HOME=tmp/demo-home).
- Vercel public demo cold starts (CONTENT_MACHINE_HOME=/tmp/cm, DEMO_MODE=1).

All rows are fictional: invented titles, example.com URLs, no personal names,
no employer references, no credentials. Safe to render publicly.

Run directly:  python -m content_machine.demo_seed
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from content_machine.storage import paths

DEMO_SPIKES = [
    ("demo-cache-stampede", "Cache stampedes turn one expired key into a database firestorm", 9.3, "pass", "Distributed Systems"),
    ("demo-pool-sizing", "Connection pool sizing is a core-count problem, not a load problem", 9.1, "pass", "Database Performance"),
    ("demo-outbox-pattern", "The transactional outbox removes the dual-write guesswork", 8.9, "pass", "Distributed Systems"),
    ("demo-guid-fragmentation", "Random GUIDs quietly tax every B-tree insert", 8.7, "pass", "Database Performance"),
    ("demo-lease-renewal", "Fixed-TTL locks expire exactly when you need them most", 8.6, "candidate", "Resilience Engineering"),
    ("demo-poison-pill", "One malformed event can stall an entire consumer group", 8.4, "candidate", "Event-Driven Architecture"),
    ("demo-trace-context", "Trace context headers turn hours of log grepping into minutes", 8.2, "candidate", "Observability"),
    ("demo-idempotency-keys", "Idempotency keys make retries boring, which is the point", 8.0, "candidate", "API Design"),
    ("demo-cardinality", "A single user_id label can spawn a hundred thousand time series", 7.6, "reject", "Observability"),
    ("demo-cold-starts", "Lambda cold starts are a packaging problem before a capacity problem", 7.2, "reject", "Serverless"),
]

DEMO_LESSONS = [
    "Open directly on the technical failure or observation. No greetings, no buzzword warm-ups.",
    "Keep posts between 120 and 280 words with 1-2 sentence paragraphs.",
    "Close with an honest practitioner observation, never an engagement question.",
    "Never invent corporate production outages to manufacture drama.",
    "Limit hashtags to 2-3 hyper-relevant technical tags at the bottom.",
    "Cite concrete failure modes (timeouts, retries, schema drift) instead of vague generalities.",
]

DEMO_COMMENTS = [
    (
        "We moved our cache layer to a probabilistic early-expiry strategy last quarter.",
        "insightful",
        "The early-expiry move matches what we saw: the stampede window shrinks to almost nothing once readers refresh ahead of TTL. Worth pairing it with a per-key mutex for the cold path.",
    ),
    (
        "Our team standardized on UUIDv7 for all new primary keys this year.",
        "contrarian",
        "UUIDv7 fixed our write locality, but the migration story is the part nobody warns about: dual-write windows and index rebuilds dominate the project, not the key format.",
    ),
]


def _ts(days_ago: float) -> str:
    dt = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


def seed_demo(conn: sqlite3.Connection) -> dict[str, int]:
    """Insert the synthetic showcase dataset. Idempotent: skips if already seeded."""
    _write_demo_voice_guide()  # before the guard: cheap, content-identical rewrite
    existing = conn.execute("SELECT COUNT(*) FROM spikes WHERE id LIKE 'demo-%'").fetchone()[0]
    if existing:
        return {"spikes": 0, "lessons": 0, "iterations": 0, "comments": 0}

    for i, (sid, thesis, score, status, topic) in enumerate(DEMO_SPIKES):
        scores = {
            "median_composite": score,
            "verdict": status,
            "samples": [
                {"model": "gemini-2.5-flash", "composite": round(score - 0.2, 2)},
                {"model": "gemini-2.5-pro", "composite": score},
                {"model": "gemini-2.5-flash-lite", "composite": round(score + 0.1, 2)},
            ],
        }
        conn.execute(
            "INSERT INTO spikes (id, created_at, category, hook_thesis, evidence_json, scores_json, status, topic_tag, source_url) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                sid,
                _ts(1.0 + i * 0.3),
                "demo.example.com",
                thesis,
                json.dumps({"notes": "synthetic showcase signal"}),
                json.dumps(scores),
                status,
                topic,
                f"https://demo.example.com/articles/{i + 1}",
            ),
        )

    for rule in DEMO_LESSONS:
        conn.execute(
            "INSERT INTO lessons (rule_text, category, provenance_project, created_at, last_touched_at, status) "
            "VALUES (?,?,?,?,?,?)",
            (rule, "style", "demo-seed", _ts(2.0), _ts(2.0), "active"),
        )

    draft = (
        "A hot cache key expired at peak traffic and five hundred requests saw the same miss.\n\n"
        "The pool exhausted in seconds. What worked better for me: a per-key mutex so one query "
        "serves the crowd, plus probabilistic early refresh so the crowd never forms."
    )
    for iteration, raw, met in ((1, 8.1, 0), (2, 8.8, 0), (3, 9.3, 1)):
        review = {
            "iteration": iteration,
            "draft": draft,
            "threshold_met": bool(met),
            "gate_basis": "raw",
            "composite_raw": raw,
            "composite_normalized": None,
            "resampled": False,
            "notes": "synthetic showcase review",
            "scores": {
                "narrative": round(raw - 0.1, 2),
                "punch": round(raw + 0.2, 2),
                "depth": raw,
                "slop": round(raw - 0.3, 2),
            },
            "required_actions": [] if met else ["Tighten the opening hook."],
        }
        conn.execute(
            "INSERT INTO iterations (spike_id, iteration, draft_path, council_review_json, composite_raw, composite_normalized, threshold_met, created_at, draft_content) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "demo-cache-stampede",
                iteration,
                "(demo) iteration %d" % iteration,
                json.dumps(review),
                raw,
                None,
                met,
                _ts(0.5 + (3 - iteration) * 0.1),
                draft,
            ),
        )
        for slot, dim in (("narrative", "narrative_arc"), ("punch", "directness"), ("depth", "depth"), ("slop", "purity")):
            conn.execute(
                "INSERT INTO judge_score_history (judge_slot, model_config, spike_id, iteration, dimension, raw_score, normalized_score, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (slot, "gemini-2.5-pro", "demo-cache-stampede", iteration, dim, review["scores"][slot], None, _ts(0.5)),
            )

    for i, (post, angle, final) in enumerate(DEMO_COMMENTS, start=1):
        conn.execute(
            "INSERT INTO comments (id, post_content, angle, perspective_text, initial_draft, final_comment, iteration_count, peak_score, verdict, judge_critiques, created_at, humanized, humanize_tone, burstiness_score) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (f"demo-comment-{i}", post, angle, "synthetic perspective", final, final, 1, 9.1, "pass", "[]", _ts(0.2), 1, "pragmatic_architect", 4.1),
        )

    conn.commit()
    _write_bundles()
    return {
        "spikes": len(DEMO_SPIKES),
        "lessons": len(DEMO_LESSONS),
        "iterations": 3,
        "comments": len(DEMO_COMMENTS),
    }


DEMO_VOICE_GUIDE = """# Voice & Persona Guide — Demo Author

Synthetic persona for the public demo. No real person's identity.

- **Persona**: Demo Author - synthetic senior engineer persona for showcase environments
- **Current Operational Reality**: Hands-on distributed-systems engineer running local
  agent harnesses, eval suites, and homelab load tests.
- **Technical Domains**: Distributed Systems, Database Performance, Observability, Resilience Engineering

## 2. Voice Invariants & Negative Constraints

1. Never cite previous employers or company attributions.
2. No false corporate employment claims ("my company", "our team at work").
3. Job-status agnostic senior tone with architectural authority.
4. Zero generic praise, buzzwords, or emoji openers.
5. No fabricated production or payment outages.
"""


def _write_demo_voice_guide() -> None:
    """Replace the synced real-author voice guide with the synthetic persona."""
    from content_machine.profile.manager import ProfileManager

    manager = ProfileManager()
    manager.runtime_path.write_text(DEMO_VOICE_GUIDE, encoding="utf-8")


def _write_bundles() -> None:
    """Two fake distribution bundles so the Distribute history drawer has cards."""
    bundles = {
        "demo-cache-stampede": {
            "anchor.md": "A hot cache key expired at peak traffic and five hundred requests saw the same miss.\n",
            "linkedin.md": "A hot cache key expired at peak traffic.\n\nFive hundred requests saw the same miss, the pool exhausted, and CPU pinned.\n\nWhat works better for me: a per-key mutex so one query serves the crowd, plus probabilistic early refresh so the crowd never forms.\n\n#DistributedSystems #Caching\n",
            "x_thread.md": "1/ A hot cache key expired at peak traffic. Five hundred requests saw the same miss.\n",
            "newsletter.md": "This week: cache stampedes, and why early expiry beats a bigger pool.\n",
            "video_script.md": "[Visual Cue: terminal scroll] A hot cache key expires. Five hundred requests miss at once.\n",
        },
        "demo-pool-sizing": {
            "anchor.md": "Connection pool sizing is a core-count problem, not a load problem.\n",
            "linkedin.md": "I bumped a pool from 50 to 500 and throughput fell off a cliff.\n\nAn 8-core database cannot run 500 queries at once. The scheduler thrashes while statements wait.\n\nWhat works better for me: size from core count, then prove it with a load test.\n\n#DatabasePerformance #BackendEngineering\n",
            "x_thread.md": "1/ We sized our pool from core count and throughput went up, not down.\n",
            "newsletter.md": "This week: why bigger connection pools make slow databases slower.\n",
            "video_script.md": "[Camera Zoom: dashboard] Watch throughput fall as connections climb past core count.\n",
        },
    }
    for slug, files in bundles.items():
        dist = paths.project_dir(slug) / "distribution"
        dist.mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (dist / name).write_text(text, encoding="utf-8")


def main() -> None:
    from content_machine.storage import db

    paths.ensure_tree()
    conn = db.connect()
    try:
        counts = seed_demo(conn)
    finally:
        conn.close()
    print(f"demo seed: {counts}")


if __name__ == "__main__":
    main()
