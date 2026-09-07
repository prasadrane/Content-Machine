"""Council evaluation + revision loop (plan v2 §5.2, §5.3).

Design points:
- Independent parallel scoring; no debate (P2-F6). Judges never see each
  other's scores or their own prior scores on the same draft.
- Gate basis: raw composite until per-judge normalization stats exist for
  every judge (thresholds.normalization_min_samples); normalized composites
  are recorded for monitoring meanwhile.
- Margin band: composites within ±thresholds.council_margin of the gate
  trigger one resample (fresh judge pass) averaged with the first, instead
  of an immediate pass/fail (mirrors the idea-gate fix, P2-F8).
- Break behavior: after thresholds.council_max_iterations without reaching
  the gate, return the best-scoring draft with blocking issues.
"""

from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..config import AppConfig
from ..router.base import AllRoutesFailed
from ..schemas import CouncilScores
from .normalize import DIMENSIONS, normalization_stats, z_normalize
from .obfuscate import obfuscate

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RUBRIC = REPO_ROOT / "council" / "rubric_v1.md"
MIN_QUORUM = 3

JUDGE_SYSTEM = (
    "You are {slot}, one independent judge on a content editorial council. "
    "Score only from the anonymous draft provided. Follow the rubric exactly."
)
REVISE_PROMPT = """You are the master drafter revising a draft after council review.

RUBRIC (evaluation criteria, for reference):
{rubric}
{rules_section}
CURRENT DRAFT:
{draft}

COUNCIL CRITIQUES (consolidated, address every item):
{critiques}

Return the complete revised draft as plain text. No preamble, no commentary, no code fences."""


class CouncilError(Exception):
    pass


@dataclass
class CouncilDecision:
    iteration: int
    threshold_met: bool
    gate_basis: str  # "raw" | "normalized"
    composite_raw: float
    composite_normalized: float | None
    judge_scores: dict[str, CouncilScores]
    required_actions: list[str]
    draft: str
    resampled: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        return "pass" if self.threshold_met else "revise"



def _composite(scores: CouncilScores) -> float:
    return sum(getattr(scores, d) for d in DIMENSIONS) / len(DIMENSIONS)


def _evaluate_once(
    *, cfg: AppConfig, router, rubric_text: str, draft: str
) -> tuple[dict[str, CouncilScores], list[str]]:
    """Parallel independent scoring by all configured judge slots."""
    anon = obfuscate(draft)
    slots = cfg.models.council
    if not slots:
        raise CouncilError("config.models.council is empty")
    results: dict[str, CouncilScores] = {}
    notes: list[str] = []

    def score_one(slot: str, model: str) -> tuple[str, CouncilScores | None, str]:
        prompt = f"{rubric_text}\n\n## Draft under review (anonymous)\n\n{anon}"
        try:
            out = router.complete(
                [model], prompt, system=JUDGE_SYSTEM.format(slot=slot), schema=CouncilScores
            )
            return slot, out, ""
        except AllRoutesFailed as e:
            return slot, None, str(e)

    with ThreadPoolExecutor(max_workers=len(slots)) as pool:
        for slot, scores, err in pool.map(
            lambda kv: score_one(kv[0], kv[1]), slots.items()
        ):
            if scores is not None:
                results[slot] = scores
            else:
                notes.append(f"judge {slot} failed: {err[:200]}")

    if len(results) < MIN_QUORUM:
        raise CouncilError(
            f"quorum not met: {len(results)}/{len(slots)} judges succeeded. " + "; ".join(notes)
        )
    return results, notes


def _composites(judge_scores: dict[str, CouncilScores]) -> float:
    vals = [_composite(s) for s in judge_scores.values()]
    return sum(vals) / len(vals)


def _normalized_composite(
    judge_scores: dict[str, CouncilScores], cfg: AppConfig, conn: sqlite3.Connection
) -> float | None:
    """Mean z-score across judges, or None until every judge has stats."""
    zs: list[float] = []
    for slot, scores in judge_scores.items():
        model = cfg.models.council.get(slot, "")
        stats = normalization_stats(conn, slot, model, cfg.thresholds.normalization_min_samples)
        if stats is None:
            return None
        z = z_normalize({d: getattr(scores, d) for d in DIMENSIONS}, stats)
        zs.extend(z.values())
    return sum(zs) / len(zs) if zs else None


def _consolidated_actions(judge_scores: dict[str, CouncilScores]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for slot, scores in sorted(judge_scores.items()):
        for a in scores.required_actions:
            key = a.strip().lower()
            if key and key not in seen:
                seen.add(key)
                actions.append(f"[{slot}] {a}")
    return actions


def revise(
    *,
    cfg: AppConfig,
    router,
    rubric_text: str,
    draft: str,
    critiques: list[str],
    rules: list[str] | None = None,
) -> str:
    rules_section = ""
    if rules:
        rules_section = "\nGOVERNED EDITORIAL RULES (must obey every rule):\n" + "\n".join(f"- {r}" for r in rules) + "\n"

    prompt = REVISE_PROMPT.format(
        rubric=rubric_text,
        rules_section=rules_section,
        draft=draft,
        critiques="\n".join(f"- {c}" for c in critiques),
    )
    out = router.complete([cfg.models.writer], prompt)
    if not isinstance(out, str):
        raise CouncilError("writer route returned non-text for revision")
    out = out.strip()
    if out.startswith("```"):
        lines = out.splitlines()
        if lines and lines[-1].strip() == "```":
            out = "\n".join(lines[1:-1]).strip()
    return out if out else draft



def _persist(
    *, conn, spike_id, iteration, draft, decision, project_dir, notes
) -> None:
    review = {
        "iteration": iteration,
        "draft": draft,
        "threshold_met": decision["threshold_met"],
        "gate_basis": decision["gate_basis"],
        "composite_raw": decision["composite_raw"],
        "composite_normalized": decision["composite_normalized"],
        "resampled": decision["resampled"],
        "notes": notes,
        "scores": {slot: s.model_dump() for slot, s in decision["judge_scores"].items()},
        "required_actions": decision["required_actions"],
    }
    if project_dir is not None:
        draft_path = Path(project_dir) / "iterations" / f"draft_v{iteration}.md"
        draft_path.parent.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(draft, encoding="utf-8")
        (Path(project_dir) / "council_review.json").write_text(
            json.dumps(review, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        draft_path_str = str(draft_path)
    else:
        draft_path_str = f"(unsaved) iteration {iteration}"

    # Ensure spike exists in spikes table to satisfy foreign key constraints
    existing = conn.execute("SELECT id FROM spikes WHERE id=?", (spike_id,)).fetchone()
    if not existing:
        conn.execute(
            """
            INSERT INTO spikes(id, category, hook_thesis, scores_json, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (spike_id, "council_draft", spike_id, "{}", "in_council"),
        )

    for slot, s in decision["judge_scores"].items():
        model = decision.get("models", {}).get(slot, "")
        for dim in DIMENSIONS:
            conn.execute(
                "INSERT INTO judge_score_history"
                "(judge_slot, model_config, spike_id, iteration, dimension, raw_score)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (slot, model, spike_id, iteration, dim, getattr(s, dim)),
            )
    conn.execute(
        "INSERT INTO iterations"
        "(spike_id, iteration, draft_path, council_review_json, composite_raw,"
        " composite_normalized, threshold_met, draft_content) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            spike_id, iteration, draft_path_str,
            json.dumps(review, ensure_ascii=False),
            decision["composite_raw"], decision["composite_normalized"],
            int(decision["threshold_met"]),
            draft,
        ),
    )
    conn.execute(
        "INSERT INTO audit_log(event, detail) VALUES (?, ?)",
        ("council_iteration", f"spike={spike_id} iter={iteration} met={decision['threshold_met']}"),
    )
    conn.commit()


def run_council(
    *,
    spike_id: str,
    draft: str,
    cfg: AppConfig,
    router,
    conn: sqlite3.Connection | None = None,
    db_conn: sqlite3.Connection | None = None,
    project_dir: str | Path | None = None,
    rubric_path: str | Path | None = None,
    max_iterations: int | None = None,
) -> CouncilDecision:
    conn = conn if conn is not None else db_conn
    rubric_text = Path(rubric_path or DEFAULT_RUBRIC).read_text(encoding="utf-8")
    th = cfg.thresholds
    gate = th.council_min_score_raw
    margin = getattr(th, "council_margin", 0.3)
    max_iter = max_iterations or th.council_max_iterations

    best: dict | None = None
    decision_obj: CouncilDecision | None = None

    for iteration in range(1, max_iter + 1):
        judge_scores, notes = _evaluate_once(cfg=cfg, router=router, rubric_text=rubric_text, draft=draft)
        composite = _composites(judge_scores)
        resampled = False

        if gate - margin <= composite < gate:
            # margin band: one fresh resample, average composites
            resample_scores, rnotes = _evaluate_once(
                cfg=cfg, router=router, rubric_text=rubric_text, draft=draft
            )
            notes += rnotes
            composite = (composite + _composites(resample_scores)) / 2
            judge_scores = resample_scores
            resampled = True

        comp_norm = _normalized_composite(judge_scores, cfg, conn)
        threshold_met = composite >= gate
        required_actions = _consolidated_actions(judge_scores)

        decision: dict = {
            "threshold_met": threshold_met,
            "gate_basis": "raw" if comp_norm is None else "normalized",
            "composite_raw": composite,
            "composite_normalized": comp_norm,
            "resampled": resampled,
            "judge_scores": judge_scores,
            "required_actions": required_actions,
            "models": dict(cfg.models.council),
        }
        _persist(
            conn=conn, spike_id=spike_id, iteration=iteration, draft=draft,
            decision=decision, project_dir=project_dir, notes=notes,
        )

        decision_obj = CouncilDecision(
            iteration=iteration, threshold_met=threshold_met,
            gate_basis=decision["gate_basis"], composite_raw=composite,
            composite_normalized=comp_norm, judge_scores=judge_scores,
            required_actions=required_actions, draft=draft,
            resampled=resampled, notes=notes,
        )
        if best is None or composite > best[0]:
            best = (composite, decision_obj)

        if threshold_met:
            return decision_obj
        if iteration < max_iter:
            if not required_actions:
                required_actions = ["no concrete actions returned; re-evaluate rubric compliance"]
            
            active_rules: list[str] = []
            if conn:
                try:
                    rule_rows = conn.execute(
                        "SELECT rule_text FROM lessons WHERE status='active' ORDER BY created_at"
                    ).fetchall()
                    active_rules = [r[0] for r in rule_rows]
                except Exception:
                    active_rules = []

            draft = revise(
                cfg=cfg, router=router, rubric_text=rubric_text,
                draft=draft, critiques=required_actions, rules=active_rules,
            )

    # max iterations exhausted: break with best draft + blocking issues
    best_comp, best_dec = best
    final = CouncilDecision(
        iteration=best_dec.iteration, threshold_met=False,
        gate_basis=best_dec.gate_basis, composite_raw=best_comp,
        composite_normalized=best_dec.composite_normalized,
        judge_scores=best_dec.judge_scores,
        required_actions=best_dec.required_actions,
        draft=best_dec.draft, resampled=best_dec.resampled,
        notes=best_dec.notes + [f"loop broken after {max_iter} iterations; best composite {best_comp:.2f}"],
    )
    return final
