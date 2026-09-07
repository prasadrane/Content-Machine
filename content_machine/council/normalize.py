"""Per-judge score normalization (plan v2 §5.2).

Raw scores are not comparable across judges (per-model score tendencies).
z-scores are computed per (judge_slot, model_config) from judge_score_history.
Until normalization_min_samples exist for every judge, callers fall back to
the raw composite and record normalized values for monitoring only.
"""

from __future__ import annotations

import sqlite3

DIMENSIONS = ("narrative", "velocity", "depth", "slop_purity")


def normalization_stats(
    conn: sqlite3.Connection, judge_slot: str, model_config: str, min_samples: int = 30
) -> dict[str, tuple[float, float]] | None:
    """dimension -> (mean, std) once enough history exists, else None."""
    rows = conn.execute(
        "SELECT dimension, raw_score FROM judge_score_history"
        " WHERE judge_slot = ? AND model_config = ? ORDER BY id DESC LIMIT ?",
        (judge_slot, model_config, min_samples * len(DIMENSIONS)),
    ).fetchall()
    by_dim: dict[str, list[float]] = {d: [] for d in DIMENSIONS}
    for r in rows:
        if r["dimension"] in by_dim:
            by_dim[r["dimension"]].append(r["raw_score"])
    if any(len(v) < min_samples for v in by_dim.values()):
        return None
    stats: dict[str, tuple[float, float]] = {}
    for dim, vals in by_dim.items():
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = var**0.5
        stats[dim] = (mean, std if std > 1e-9 else 1.0)
    return stats


def z_normalize(
    raw: dict[str, float], stats: dict[str, tuple[float, float]]
) -> dict[str, float]:
    return {dim: (raw[dim] - stats[dim][0]) / stats[dim][1] for dim in raw if dim in stats}
