"""Council pass/fail gate — pure, calibration-aware, configurable (task-2).

Extracts the decision logic the council loop needs so it can be tested and
tuned independently of judge routing. Two questions live here:

1. ``decide_threshold_met`` — did the draft pass? Modes:
   - ``"raw"``: compare the raw composite against ``council_min_score_raw``
     (the legacy behavior; absolute 9.0 gate, miscalibrated per NOTES.md).
   - ``"normalized"``: compare the per-judge z-normalized composite against
     ``council_min_score_z``; falls back to the raw rule when no normalized
     composite is available (judges lack ``normalization_min_samples`` history).
   - ``"auto"``: normalized rule when a normalized composite exists, raw
     rule otherwise. (Config default is ``"raw"`` — the legacy absolute
     gate — because auto/normalized with ``council_min_score_z=0.0`` would
     silently lower the pass bar to ~50th percentile once per-judge
     normalization history accumulates. Opt in after calibration.)

2. ``within_margin`` — should a near-miss trigger a resample instead of an
   immediate fail? Mirrors exactly the band condition in council/loop.py:
   ``gate - margin <= composite < gate`` (lower edge inclusive, gate
   exclusive — a composite at/above the gate has already passed).

This module is pure: no DB, no router, no imports from loop.py.
"""

from __future__ import annotations

from ..config import ThresholdsConfig


def decide_threshold_met(
    composite_raw: float,
    composite_norm: float | None,
    th: ThresholdsConfig,
) -> bool:
    """Pass/fail decision for one council composite under ``th.council_gate_mode``."""
    mode = th.council_gate_mode
    if mode == "raw":
        return composite_raw >= th.council_min_score_raw
    if mode in ("normalized", "auto"):
        # Both prefer the z-gate when a normalized composite exists and fall
        # back to the raw rule until judges have normalization history.
        if composite_norm is None:
            return composite_raw >= th.council_min_score_raw
        return composite_norm >= th.council_min_score_z
    raise ValueError(f"unknown council_gate_mode: {mode!r}")


def within_margin(composite: float, gate: float, margin: float) -> bool:
    """True when ``composite`` sits just below ``gate`` and deserves a resample.

    Mirrors council/loop.py band trigger ``gate - margin <= composite < gate``:
    lower edge inclusive, gate exclusive.
    """
    return gate - margin <= composite < gate
