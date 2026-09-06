"""Council loop tests — offline, fake router.

Run: python tests/test_council.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.config import AppConfig, ModelsConfig, ThresholdsConfig  # noqa: E402
from content_machine.council.loop import CouncilError, run_council  # noqa: E402
from content_machine.council.normalize import normalization_stats  # noqa: E402
from content_machine.council.obfuscate import obfuscate  # noqa: E402
from content_machine.router.base import AllRoutesFailed  # noqa: E402
from content_machine.schemas import CouncilScores  # noqa: E402
from content_machine.storage.db import connect  # noqa: E402

SLOTS = {"perell": "jm1", "puri": "jm2", "housel": "jm3", "slop_allergist": "jm4"}


def scores(v: float, verdict="revise", actions=("tighten the hook",)) -> CouncilScores:
    return CouncilScores(
        narrative=v, velocity=v, depth=v, slop_purity=v,
        threshold_met=v >= 9.0, verdict=verdict, required_actions=list(actions),
    )


class FakeRouter:
    """judge_outcomes: model -> list of CouncilScores|Exception (popped per call).
    writer_outcomes: list of str revisions."""

    def __init__(self, judge_outcomes: dict[str, list], writer_outcomes: list[str] | None = None):
        self.judge_outcomes = {m: list(v) for m, v in judge_outcomes.items()}
        self.writer_outcomes = list(writer_outcomes or [])
        self.judge_calls: list[str] = []
        self.writer_calls: list[str] = []

    def complete(self, model_layer, prompt, *, system=None, schema=None):
        model = model_layer[0]
        if schema is CouncilScores:
            self.judge_calls.append(model)
            if not self.judge_outcomes.get(model):
                raise AllRoutesFailed([(model, "fake", "scripted outcomes exhausted")])
            out = self.judge_outcomes[model].pop(0)
            if isinstance(out, Exception):
                raise out
            return out
        self.writer_calls.append(prompt)
        if not self.writer_outcomes:
            raise AllRoutesFailed([(model, "fake", "no writer outcome scripted")])
        return self.writer_outcomes.pop(0)


def make_cfg(**th_over) -> AppConfig:
    th = ThresholdsConfig(**th_over)
    return AppConfig(
        models=ModelsConfig(writer="wm", council=dict(SLOTS)),
        thresholds=th,
    )


def insert_spike(conn, spike_id: str) -> None:
    """Production order: Oracle creates the spike before council runs."""
    conn.execute(
        "INSERT INTO spikes(id, category, hook_thesis) VALUES (?, ?, ?)",
        (spike_id, "test", "test thesis"),
    )
    conn.commit()


def high(n: int) -> dict[str, list]:
    return {m: [scores(9.5, "pass")] * n for m in SLOTS.values()}


def test_obfuscate() -> None:
    text = "Written by Claude\nOur Qwen model showed that GPT-4 style prompts fail."
    out = obfuscate(text)
    assert "Claude" not in out and "Qwen" not in out and "GPT-4" not in out
    assert "Written by" not in out
    assert "fail" in out


def test_loop_pass_first_iteration() -> None:
    conn = connect(":memory:")
    tmp = tempfile.mkdtemp(prefix="cm_council_")
    insert_spike(conn, "s1")
    cfg = make_cfg()
    router = FakeRouter(high(1))
    d = run_council(spike_id="s1", draft="draft text", cfg=cfg, router=router,
                    conn=conn, project_dir=tmp)
    assert d.threshold_met and d.iteration == 1
    assert d.gate_basis == "raw"  # no normalization history yet
    assert abs(d.composite_raw - 9.5) < 1e-9
    assert len(router.judge_calls) == 4  # one pass, all slots
    assert (Path(tmp) / "iterations" / "draft_v1.md").exists()
    assert (Path(tmp) / "council_review.json").exists()
    n = conn.execute("SELECT COUNT(*) c FROM judge_score_history").fetchone()["c"]
    assert n == 16  # 4 judges x 4 dimensions
    conn.close()


def test_loop_revise_then_pass() -> None:
    conn = connect(":memory:")
    insert_spike(conn, "s2")
    cfg = make_cfg()
    outcomes = {m: [scores(6.0), scores(9.2, "pass")] for m in SLOTS.values()}
    router = FakeRouter(outcomes, writer_outcomes=["revised draft v2"])
    d = run_council(spike_id="s2", draft="draft v1", cfg=cfg, router=router, conn=conn)
    assert d.threshold_met and d.iteration == 2
    assert d.draft == "revised draft v2"
    assert len(router.writer_calls) == 1
    assert "tighten the hook" in router.writer_calls[0]
    conn.close()


def test_loop_breaks_at_max_iterations() -> None:
    conn = connect(":memory:")
    insert_spike(conn, "s3")
    cfg = make_cfg(council_max_iterations=2)
    outcomes = {m: [scores(5.0), scores(5.5)] for m in SLOTS.values()}
    router = FakeRouter(outcomes, writer_outcomes=["still weak"])
    d = run_council(spike_id="s3", draft="draft", cfg=cfg, router=router, conn=conn)
    assert not d.threshold_met
    assert d.iteration == 2  # best-scoring iteration kept
    assert abs(d.composite_raw - 5.5) < 1e-9
    assert any("broken after" in note for note in d.notes)
    assert d.required_actions
    conn.close()


def test_margin_band_resample() -> None:
    conn = connect(":memory:")
    insert_spike(conn, "s4")
    cfg = make_cfg(council_margin=0.3)  # gate 9.0 -> band [8.7, 9.0)
    outcomes = {m: [scores(8.8), scores(9.4, "pass")] for m in SLOTS.values()}
    router = FakeRouter(outcomes)
    d = run_council(spike_id="s4", draft="draft", cfg=cfg, router=router, conn=conn)
    assert d.resampled
    assert d.threshold_met  # (8.8 + 9.4) / 2 = 9.1
    assert len(router.judge_calls) == 8  # initial + resample
    conn.close()


def test_quorum_enforced() -> None:
    conn = connect(":memory:")
    cfg = make_cfg()
    outcomes = high(1)
    outcomes["jm3"] = [AllRoutesFailed([("jm3", "r", "down")])]
    outcomes["jm4"] = [AllRoutesFailed([("jm4", "r", "down")])]
    router = FakeRouter(outcomes)
    try:
        run_council(spike_id="s5", draft="draft", cfg=cfg, router=router, conn=conn)
    except CouncilError as e:
        assert "quorum" in str(e)
    else:
        raise AssertionError("expected CouncilError")
    conn.close()


def test_normalization_stats_threshold() -> None:
    conn = connect(":memory:")
    for i in range(30):
        for dim in ("narrative", "velocity", "depth", "slop_purity"):
            conn.execute(
                "INSERT INTO judge_score_history(judge_slot, model_config, dimension, raw_score)"
                " VALUES (?, ?, ?, ?)",
                ("perell", "jm1", dim, 7.0 + (i % 3) * 0.5),
            )
    conn.commit()
    assert normalization_stats(conn, "perell", "jm1", min_samples=30) is not None
    assert normalization_stats(conn, "perell", "jm1", min_samples=31) is None
    conn.close()


def test_critical_phase_models_configuration() -> None:
    """Verify that qwen3.8-max is configured for critical phases and council only uses qwen3.8-max and qwen3.8-flash."""
    from content_machine.config import load_config
    cfg = load_config()
    assert cfg.models.writer == "qwen3.8-max"
    assert cfg.models.council.get("perell") == "qwen3.8-max"
    assert cfg.models.council.get("housel") == "qwen3.8-max"
    assert cfg.models.council.get("puri") == "qwen3.8-flash"
    assert cfg.models.council.get("slop_allergist") == "qwen3.8-flash"
    assert set(cfg.models.council.values()).issubset({"qwen3.8-max", "qwen3.8-flash"})
    assert getattr(cfg.models, "video_long", None) == "qwen3.8-max"


def main() -> None:
    for fn in (test_obfuscate, test_loop_pass_first_iteration, test_loop_revise_then_pass,
               test_loop_breaks_at_max_iterations, test_margin_band_resample,
               test_quorum_enforced, test_normalization_stats_threshold,
               test_critical_phase_models_configuration):
        fn()
        print(f"PASS {fn.__name__}")
    print("ALL PASS")


if __name__ == "__main__":
    main()
