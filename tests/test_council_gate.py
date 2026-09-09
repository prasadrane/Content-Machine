"""Tests for council/gate.py — calibration-aware pass/fail decision (task-2)."""

from __future__ import annotations

import pytest

from content_machine.config import ThresholdsConfig
from content_machine.council.gate import decide_threshold_met, within_margin


# ---------------------------------------------------------------- ThresholdsConfig defaults

def test_thresholds_defaults_include_new_fields():
    th = ThresholdsConfig()
    assert th.council_gate_mode == "raw"
    assert th.council_min_score_z == 0.0
    # pre-existing defaults unchanged
    assert th.council_min_score_raw == 9.0
    assert th.council_margin == 0.3


def test_thresholds_load_from_dict_with_new_fields():
    th = ThresholdsConfig.model_validate(
        {"council_gate_mode": "normalized", "council_min_score_z": 1.5}
    )
    assert th.council_gate_mode == "normalized"
    assert th.council_min_score_z == 1.5


# ---------------------------------------------------------------- decide_threshold_met: raw mode

def test_raw_mode_passes_at_boundary():
    th = ThresholdsConfig(council_gate_mode="raw")
    # composite == gate passes (>=)
    assert decide_threshold_met(9.0, None, th) is True
    assert decide_threshold_met(9.0, 5.0, th) is True  # norm ignored in raw mode


def test_raw_mode_below_and_above():
    th = ThresholdsConfig(council_gate_mode="raw")
    assert decide_threshold_met(8.99, None, th) is False
    assert decide_threshold_met(9.01, None, th) is True


def test_raw_mode_uses_council_min_score_raw_not_z():
    th = ThresholdsConfig(council_gate_mode="raw", council_min_score_z=-100.0)
    assert decide_threshold_met(8.0, 0.0, th) is False  # z gate irrelevant in raw mode


# ---------------------------------------------------------------- decide_threshold_met: normalized mode

def test_normalized_mode_uses_z_gate():
    th = ThresholdsConfig(council_gate_mode="normalized", council_min_score_z=0.5)
    assert decide_threshold_met(9.9, 0.5, th) is True   # boundary: norm == gate passes
    assert decide_threshold_met(9.9, 0.49, th) is False
    assert decide_threshold_met(0.0, 0.6, th) is True   # raw irrelevant in normalized mode


def test_normalized_mode_falls_back_to_raw_when_norm_none():
    th = ThresholdsConfig(council_gate_mode="normalized", council_min_score_z=-100.0)
    # fallback raw rule: composite_raw >= council_min_score_raw
    assert decide_threshold_met(9.0, None, th) is True
    assert decide_threshold_met(8.9, None, th) is False


# ---------------------------------------------------------------- decide_threshold_met: auto mode

def test_auto_uses_normalized_when_norm_present():
    th = ThresholdsConfig(council_gate_mode="auto", council_min_score_z=0.0)
    # raw 9.5 would pass raw gate, but norm -0.1 fails z gate -> normalized rule wins
    assert decide_threshold_met(9.5, -0.1, th) is False
    assert decide_threshold_met(5.0, 0.0, th) is True   # boundary passes


def test_auto_falls_back_to_raw_when_norm_none():
    th = ThresholdsConfig(council_gate_mode="auto")
    assert decide_threshold_met(9.0, None, th) is True
    assert decide_threshold_met(8.9, None, th) is False


def test_raw_is_default_mode():
    # Default preserves legacy behavior: absolute raw gate, normalized
    # composite ignored for the decision (recorded for monitoring only).
    th = ThresholdsConfig()
    assert th.council_gate_mode == "raw"
    assert decide_threshold_met(9.5, -1.0, th) is True   # raw passes despite low z
    assert decide_threshold_met(8.0, None, th) is False


def test_unknown_mode_rejected():
    th = ThresholdsConfig(council_gate_mode="bogus")
    with pytest.raises(ValueError):
        decide_threshold_met(9.0, None, th)


# ---------------------------------------------------------------- within_margin — mirror loop.py
# loop.py line 303: `if gate - margin <= composite < gate:` (raw basis, default gate 9.0, margin 0.3)

def test_within_margin_inside_band():
    assert within_margin(8.85, 9.0, 0.3) is True
    assert within_margin(8.75, 9.0, 0.3) is True   # exactly lower edge
    assert within_margin(8.999, 9.0, 0.3) is True


def test_within_margin_outside_band_below():
    assert within_margin(8.69, 9.0, 0.3) is False
    assert within_margin(0.0, 9.0, 0.3) is False


def test_within_margin_exactly_at_gate_edge_is_false():
    # upper bound is strict: composite == gate is NOT inside the band
    assert within_margin(9.0, 9.0, 0.3) is False


def test_within_margin_above_gate_is_false():
    assert within_margin(9.5, 9.0, 0.3) is False
    assert within_margin(10.0, 9.0, 0.3) is False


def test_within_margin_zero_margin_empty_band():
    # gate - 0 <= composite < gate is never true (empty interval)
    assert within_margin(9.0, 9.0, 0.0) is False
    assert within_margin(8.9, 9.0, 0.0) is False


def test_within_margin_negative_composite_relative_gate():
    # generic gate values, semantics must hold regardless of magnitude
    assert within_margin(-0.1, 0.0, 0.3) is True    # -0.3 <= -0.1 < 0.0
    assert within_margin(0.0, 0.0, 0.3) is False    # strict upper
    assert within_margin(-0.3, 0.0, 0.3) is True    # inclusive lower
    assert within_margin(-0.31, 0.0, 0.3) is False
