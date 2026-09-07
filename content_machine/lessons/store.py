"""LessonsStore: governed append-only lessons file (plan v2 §6).

Governance requirements (P2-F7):
1. Provenance per rule: project_id, created_at (via SQLite default).
2. Decay: status field; periodic passes flag untouched rules.
3. Conflict detection: cosine similarity against active-rule embeddings.
4. Cap/merge: hard cap (default 150) → merge_required signal.
5. Never auto-append: propose() → pending; human must call approve().

Embedding model: all-MiniLM-L6-v2 class (~90MB, CPU-fine).
Loaded lazily on first propose so tests/CLI start without model download.
Cosine similarity threshold: 0.8 (plan v2 §6 item 3).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Result type returned by propose()
# ---------------------------------------------------------------------------

@dataclass
class ProposeResult:
    """Outcome of proposing a new lesson rule."""

    rule_id: Optional[int] = None  # DB id of the inserted row (None if blocked)
    is_conflict: bool = False       # True → similar rule exists; merge candidate
    conflict_rule_id: Optional[int] = None  # ID of the conflicting rule
    merge_required: bool = False    # True → active-rule cap reached
    inserted: bool = False          # True when row was written to DB


# ---------------------------------------------------------------------------
# Similarity helpers (no external deps beyond numpy)
# ---------------------------------------------------------------------------

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class DefaultEmbedder:
    """Fast deterministic token-hash embedding (pure NumPy, zero network, zero blocking)."""
    DIM = 128

    def encode(self, text: str, normalize_embeddings: bool = True) -> np.ndarray:
        vec = np.zeros(self.DIM, dtype=np.float32)
        for word in text.lower().split():
            idx = abs(hash(word)) % self.DIM
            vec[idx] += 1.0
        if normalize_embeddings:
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
        return vec


def _embed(text: str, model) -> np.ndarray:
    """Embed text using the model."""
    return model.encode(text, normalize_embeddings=True)


# ---------------------------------------------------------------------------
# LessonsStore
# ---------------------------------------------------------------------------

CONFLICT_THRESHOLD = 0.80   # cosine similarity → merge candidate
DEFAULT_CAP = 150            # hard rule cap before merge pass required


class LessonsStore:
    """CRUD interface for the lessons table with governance enforced.

    Args:
        db_conn:    Open SQLite connection (with the content_machine schema).
        cap:        Hard cap on active rule count. Defaults to 150.
        embed_model: Pre-loaded model or DefaultEmbedder.
    """

    def __init__(
        self,
        db_conn: sqlite3.Connection,
        cap: int = DEFAULT_CAP,
        embed_model=None,
    ):
        self.db_conn = db_conn
        self.cap = cap
        self._embed_model = embed_model if embed_model is not None else DefaultEmbedder()

    def _model(self):
        return self._embed_model


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _active_count(self) -> int:
        row = self.db_conn.execute(
            "SELECT COUNT(*) FROM lessons WHERE status='active'"
        ).fetchone()
        return row[0]

    def _find_conflict(self, embedding: np.ndarray) -> Optional[int]:
        """Return the id of the most similar active rule if cos ≥ threshold."""
        rows = self.db_conn.execute(
            "SELECT id, embedding FROM lessons WHERE status='active' AND embedding IS NOT NULL"
        ).fetchall()
        best_sim = 0.0
        best_id = None
        for row in rows:
            stored = np.frombuffer(row["embedding"], dtype=np.float32)
            sim = _cosine(embedding, stored)
            if sim > best_sim:
                best_sim = sim
                best_id = row["id"]
        if best_sim >= CONFLICT_THRESHOLD:
            return best_id
        return None

    def _find_conflict_text(self, rule_text: str) -> Optional[int]:
        """Fast token-based similarity fallback when neural embeddings are unavailable."""
        rows = self.db_conn.execute(
            "SELECT id, rule_text FROM lessons WHERE status='active'"
        ).fetchall()
        words_new = set(rule_text.lower().split())
        if not words_new:
            return None
        for row in rows:
            words_existing = set(row["rule_text"].lower().split())
            if not words_existing:
                continue
            sim = len(words_new & words_existing) / len(words_new | words_existing)
            if sim >= 0.70:
                return row["id"]
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propose(self, rule: str, project_id: str) -> ProposeResult:
        """Insert a rule as status='pending' after conflict and cap checks.

        Args:
            rule:       The declarative rule text.
            project_id: Source project slug (provenance).

        Returns:
            ProposeResult with conflict/cap flags set when applicable.
            Even on conflict, the row is inserted as 'pending' so the
            operator can review and decide whether to merge.
        """
        # Hard-cap check (active rules only)
        if self._active_count() >= self.cap:
            return ProposeResult(merge_required=True)

        emb_bytes = None
        conflict_id = None

        try:
            model = self._model()
            if model is not None:
                emb = _embed(rule, model)
                emb_bytes = emb.astype(np.float32).tobytes()
                if self._active_count() > 0:
                    conflict_id = self._find_conflict(emb)
        except Exception:
            pass

        if conflict_id is None and self._active_count() > 0:
            conflict_id = self._find_conflict_text(rule)


        # Insert as pending regardless of conflict (operator decides)
        cur = self.db_conn.execute(
            """
            INSERT INTO lessons(rule_text, provenance_project, embedding, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (rule, project_id, emb_bytes),
        )
        self.db_conn.commit()
        rule_id = cur.lastrowid

        return ProposeResult(
            rule_id=rule_id,
            is_conflict=conflict_id is not None,
            conflict_rule_id=conflict_id,
            merge_required=False,
            inserted=True,
        )

    def approve(self, rule_id: int) -> None:
        """Human approval: set status='active'."""
        self.db_conn.execute(
            "UPDATE lessons SET status='active' WHERE id=?", (rule_id,)
        )
        self.db_conn.commit()

    def reject(self, rule_id: int) -> None:
        """Human rejection: set status='rejected'."""
        self.db_conn.execute(
            "UPDATE lessons SET status='rejected' WHERE id=?", (rule_id,)
        )
        self.db_conn.commit()

    def active_rules(self) -> list[sqlite3.Row]:
        """Return all active rules ordered by created_at."""
        return self.db_conn.execute(
            "SELECT * FROM lessons WHERE status='active' ORDER BY created_at"
        ).fetchall()

    def pending_rules(self) -> list[sqlite3.Row]:
        """Return all pending rules awaiting human review."""
        return self.db_conn.execute(
            "SELECT * FROM lessons WHERE status='pending' ORDER BY created_at"
        ).fetchall()
