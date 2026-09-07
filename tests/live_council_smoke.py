"""Live council smoke: one evaluation pass through the real relay.

Validates that every configured judge model name is served and returns
schema-valid scores. Cost: 4 judge calls (max_iterations=1, no revision).

Run: CONTENT_MACHINE_LIVE=1 python tests/live_council_smoke.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_machine.config import load_config  # noqa: E402
from content_machine.council.loop import run_council  # noqa: E402
from content_machine.router import router_from_config  # noqa: E402
from content_machine.storage.db import connect  # noqa: E402

DRAFT = """Last quarter we killed our most popular feature. The dashboard had 40,000 weekly
users and our churn survey said people loved it. But support tickets told a different story:
61 percent of onboarding failures traced back to the dashboard's setup flow. We removed it on
a Tuesday. By Friday, onboarding completion was up 22 percent and support load dropped by a
third. The lesson was not that data lies. It is that the data you collect depends on who
survives long enough to be surveyed."""


def main() -> None:
    cfg = load_config()
    router = router_from_config(cfg)
    conn = connect(":memory:")
    conn.execute(
        "INSERT INTO spikes(id, category, hook_thesis) VALUES ('live-smoke', 'internal', 'killed top feature')"
    )
    conn.commit()

    decision = run_council(
        spike_id="live-smoke", draft=DRAFT, cfg=cfg, router=router, conn=conn,
        max_iterations=1,
    )
    print(f"iteration={decision.iteration} met={decision.threshold_met} "
          f"composite={decision.composite_raw:.2f} gate_basis={decision.gate_basis} "
          f"resampled={decision.resampled}")
    for slot, s in sorted(decision.judge_scores.items()):
        print(f"  {slot:15s} model={cfg.models.council[slot]:20s} "
              f"n={s.narrative} v={s.velocity} d={s.depth} p={s.slop_purity} verdict={s.verdict}")
    for n in decision.notes:
        print("note:", n[:200])
    print("LIVE COUNCIL OK")


if __name__ == "__main__":
    main()
