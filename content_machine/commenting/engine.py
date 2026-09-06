"""LinkedIn commenting engine (spec: §3.3).

Synthesizes high-signal, 2-3 sentence comments using writer models,
governed negative constraints from LessonsStore, and Writer's Council review.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional
from uuid import uuid4

from ..config import AppConfig
from ..council.loop import run_council
from ..lessons.store import LessonsStore
from ..profile.manager import ProfileManager
from ..schemas import (
    CommentAngle,
    CommentHistoryItem,
    CommentRunResponse,
)


SYSTEM_PROMPT = (
    "You are an expert LinkedIn editorial contributor. Craft sharp, senior-level comments "
    "grounded in real-world engineering experiences. Never write empty praise, generic platitudes, "
    "or fluff."
)

ANGLE_DIRECTIVES: dict[str, str] = {
    "insightful": "Add a concrete, real-world observation or metric extending the author's point. Avoid platitudes.",
    "contrarian": "Respectfully challenge an unstated assumption or introduce a critical counter-intuitive edge case from experience.",
    "question": "Pose a sharp, senior-level question that advances the conversation beyond superficial agreement.",
}


def _sanitize_sentences(text: str, max_sentences: int = 3) -> str:
    import re
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) > max_sentences:
        return " ".join(sentences[:max_sentences]).strip()
    return text.strip()


class CommentingEngine:
    """Core editorial engine for synthesizing and vetting LinkedIn comments."""

    def __init__(
        self,
        router,
        cfg: AppConfig,
        db_conn: sqlite3.Connection | None = None,
    ):
        self.router = router
        self.cfg = cfg
        self.db_conn = db_conn

    def _build_synthesis_prompt(
        self,
        post_content: str,
        angle: str | CommentAngle = CommentAngle.INSIGHTFUL,
        perspective_text: Optional[str] = None,
    ) -> str:
        angle_key = (angle.value if hasattr(angle, "value") else str(angle)).lower()
        directive = ANGLE_DIRECTIVES.get(angle_key, ANGLE_DIRECTIVES["insightful"])

        sections = [
            "You are an expert editorial writer crafting a high-signal comment on a LinkedIn post.",
            f"TARGET POST CONTENT:\n{post_content.strip()}",
            f"COMMENT ANGLE: {angle_key.upper()}\n{directive}",
        ]

        if perspective_text and perspective_text.strip():
            sections.append(
                f"OPERATOR'S PERSPECTIVE / LIVED ANGLE (primary grounding):\n{perspective_text.strip()}"
            )

        try:
            prof_manager = ProfileManager()
            voice_guide_text = prof_manager.get_voice_guide_text()
        except Exception:
            voice_guide_text = ""

        if voice_guide_text:
            sections.append(f"AUTHOR VOICE & PERSONA GUIDE (must follow):\n{voice_guide_text.strip()}")

        rules: list[str] = []
        if self.db_conn:
            try:
                store = LessonsStore(self.db_conn)
                for r in store.active_rules():
                    if isinstance(r, sqlite3.Row):
                        rules.append(r["rule_text"])
                    elif isinstance(r, (list, tuple)) and len(r) > 1:
                        rules.append(r[1])
                    elif hasattr(r, "rule_text"):
                        rules.append(r.rule_text)
                    else:
                        rules.append(str(r))
            except Exception:
                pass

        if rules:
            rules_section = "\n".join(f"- {r}" for r in rules)
            sections.append(f"GOVERNED EDITORIAL RULES (must obey):\n{rules_section}")

        sections.append(
            "CONSTRAINTS:\n"
            "- Strictly 2 to 3 sentences. Never exceed 3 sentences.\n"
            "- High signal density with concrete substance.\n"
            "- Zero empty praise (e.g. 'Great post', 'Spot on', 'Thanks for sharing').\n"
            "- Zero emoji inflation (no emojis).\n"
            "- No hashtags, no bullet points, no markdown headers.\n"
            "- CRITICAL: Strictly adhere to the voice guide invariants: NEVER mention prior company names (no Rocket Mortgage, London Computer Systems, EXFO, etc.), NEVER claim current corporate employment, and express thoughts as pure personal technical convictions.\n"
            "- Output ONLY the comment text itself. No preamble or meta commentary."
        )

        return "\n\n".join(sections)

    def synthesize_initial_draft(
        self,
        post_content: str,
        angle: str | CommentAngle = CommentAngle.INSIGHTFUL,
        perspective_text: Optional[str] = None,
    ) -> str:
        prompt = self._build_synthesis_prompt(post_content, angle, perspective_text)
        writer_models = (
            [self.cfg.models.writer]
            if isinstance(self.cfg.models.writer, str)
            else list(self.cfg.models.writer)
        )
        out = self.router.complete(writer_models, prompt, system=SYSTEM_PROMPT)
        draft = str(out).strip() if out is not None else ""
        if draft.startswith("```"):
            lines = draft.splitlines()
            if len(lines) >= 2 and lines[-1].strip() == "```":
                draft = "\n".join(lines[1:-1]).strip()
            elif lines:
                draft = "\n".join(lines[1:]).strip()
        return draft

    def generate_comment(
        self,
        post_content: str,
        angle: str | CommentAngle = CommentAngle.INSIGHTFUL,
        perspective_text: Optional[str] = None,
    ) -> CommentRunResponse:
        angle_str = angle.value if hasattr(angle, "value") else str(angle)
        initial_draft = self.synthesize_initial_draft(
            post_content=post_content,
            angle=angle,
            perspective_text=perspective_text,
        )

        comment_id = f"comment_{uuid4().hex[:8]}"
        council_res = run_council(
            spike_id=comment_id,
            draft=initial_draft,
            cfg=self.cfg,
            router=self.router,
            conn=self.db_conn,
            max_iterations=2,
        )

        final_comment = getattr(council_res, "draft", initial_draft)
        final_comment = _sanitize_sentences(final_comment, max_sentences=3)
        iteration = getattr(council_res, "iteration", 1)

        # Extract peak score
        if getattr(council_res, "composite_normalized", None) is not None:
            peak_score = round(float(council_res.composite_normalized), 2)
        elif getattr(council_res, "composite_raw", None) is not None:
            peak_score = round(float(council_res.composite_raw), 2)
        elif getattr(council_res, "peak_score", None) is not None:
            peak_score = round(float(council_res.peak_score), 2)
        else:
            peak_score = 0.0

        # Extract verdict
        if hasattr(council_res, "verdict") and isinstance(council_res.verdict, str):
            verdict = council_res.verdict.upper()
        elif getattr(council_res, "threshold_met", False):
            verdict = "PASS"
        else:
            verdict = "REVISE"

        actions = list(getattr(council_res, "required_actions", []))

        # Extract judge scores
        judge_scores: dict[str, float] = {}
        for slot, s in getattr(council_res, "judge_scores", {}).items():
            if hasattr(s, "composite") and s.composite is not None:
                judge_scores[slot] = round(float(s.composite), 2)
            else:
                dims = [
                    getattr(s, d)
                    for d in ("narrative", "velocity", "depth", "slop_purity")
                    if hasattr(s, d) and getattr(s, d) is not None
                ]
                if dims:
                    judge_scores[slot] = round(sum(dims) / len(dims), 2)
                elif isinstance(s, (int, float)):
                    judge_scores[slot] = round(float(s), 2)
                else:
                    judge_scores[slot] = 0.0

        # Extract judge critiques
        judge_critiques: dict[str, str] = {}
        for slot, s in getattr(council_res, "judge_scores", {}).items():
            if hasattr(s, "critique") and s.critique is not None:
                judge_critiques[slot] = str(s.critique)
            elif hasattr(s, "required_actions") and s.required_actions:
                judge_critiques[slot] = "; ".join(s.required_actions)

        # Save to DB
        if self.db_conn:
            self.db_conn.execute(
                """
                INSERT INTO comments (
                    id, post_content, angle, perspective_text, initial_draft,
                    final_comment, iteration_count, peak_score, verdict, judge_critiques
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comment_id,
                    post_content,
                    angle_str,
                    perspective_text,
                    initial_draft,
                    final_comment,
                    iteration,
                    peak_score,
                    verdict,
                    json.dumps(judge_critiques),
                ),
            )
            self.db_conn.commit()

        return CommentRunResponse(
            comment_id=comment_id,
            initial_draft=initial_draft,
            final_comment=final_comment,
            iteration=iteration,
            peak_score=peak_score,
            verdict=verdict,
            actions=actions,
            judge_scores=judge_scores,
            judge_critiques=judge_critiques,
        )

    def get_history(self, limit: int = 50) -> list[CommentHistoryItem]:
        if not self.db_conn:
            return []
        cursor = self.db_conn.execute(
            """
            SELECT id, post_content, angle, perspective_text, final_comment,
                   iteration_count, peak_score, verdict, created_at
            FROM comments
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        items: list[CommentHistoryItem] = []
        for r in rows:
            items.append(
                CommentHistoryItem(
                    id=r["id"] if isinstance(r, sqlite3.Row) else r[0],
                    post_content=r["post_content"] if isinstance(r, sqlite3.Row) else r[1],
                    angle=r["angle"] if isinstance(r, sqlite3.Row) else r[2],
                    perspective_text=r["perspective_text"] if isinstance(r, sqlite3.Row) else r[3],
                    final_comment=r["final_comment"] if isinstance(r, sqlite3.Row) else r[4],
                    iteration_count=r["iteration_count"] if isinstance(r, sqlite3.Row) else r[5],
                    peak_score=float(r["peak_score"] if isinstance(r, sqlite3.Row) else r[6]),
                    verdict=r["verdict"] if isinstance(r, sqlite3.Row) else r[7],
                    created_at=str(r["created_at"] if isinstance(r, sqlite3.Row) else r[8]),
                )
            )
        return items
