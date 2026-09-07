"""OracleOrchestrator: connector pull → dedup → scoring → persistence.

Implements the §10 cadence:
  08:00  connector pull from all registered sources
  08:30  scored ideas returned to operator for spike selection

Usage:
    orch = OracleOrchestrator(connectors=[rss, github], scorer=scorer, db_conn=conn)
    candidates = orch.run()       # list[ScoredIdea], sorted by median desc
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from content_machine.connectors.base import BaseConnector, ConnectorItem
from content_machine.oracle.scorer import IdeaScorer, ScoredIdea
from content_machine.schemas import IdeaScore
from content_machine.storage.db import log_event


class OracleOrchestrator:
    """Pull ideas from all connectors, deduplicate, score, and persist.

    Args:
        connectors: List of connector instances to pull from.
        scorer:     IdeaScorer to use for scoring each item.
        db_conn:    Optional SQLite connection for persistence; if None,
                    results are returned in-memory only.
    """

    def __init__(
        self,
        connectors: list[BaseConnector],
        scorer: IdeaScorer,
        db_conn: Optional[sqlite3.Connection] = None,
    ):
        self.connectors = connectors
        self.scorer = scorer
        self.db_conn = db_conn

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pull_all(self, max_workers: int = 5) -> list[ConnectorItem]:
        """Fetch from all connectors concurrently and merge, deduplicating by URL."""
        if not self.connectors:
            return []

        def fetch_one(connector: BaseConnector) -> list[ConnectorItem]:
            try:
                res = connector.fetch()
                return res.items
            except Exception as e:
                if self.db_conn:
                    log_event(self.db_conn, "connector_error", f"{type(connector).__name__}: {e}")
                return []

        seen_urls: set[str] = set()
        items: list[ConnectorItem] = []
        workers = min(max_workers, len(self.connectors))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for connector_items in pool.map(fetch_one, self.connectors):
                for item in connector_items:
                    if item.url in seen_urls:
                        continue
                    seen_urls.add(item.url)
                    items.append(item)
        return items


    def _find_cached_spike(self, item: ConnectorItem) -> Optional[ScoredIdea]:
        """Find an existing scored spike by URL or title and rehydrate without LLM calls."""
        if self.db_conn is None:
            return None
        row = None
        if item.url:
            row = self.db_conn.execute(
                "SELECT hook_thesis, category, scores_json, status, topic_tag, source_url FROM spikes WHERE source_url = ? ORDER BY created_at DESC LIMIT 1",
                (item.url,),
            ).fetchone()
        if not row and item.title:
            row = self.db_conn.execute(
                "SELECT hook_thesis, category, scores_json, status, topic_tag, source_url FROM spikes WHERE hook_thesis = ? ORDER BY created_at DESC LIMIT 1",
                (item.title,),
            ).fetchone()
        if not row:
            return None

        try:
            payload = json.loads(row["scores_json"])
            samples_data = payload.get("samples", [])
            samples = [IdeaScore(**s) for s in samples_data]
            median_comp = float(payload.get("median_composite", 0.0))
            verdict = payload.get("verdict", row["status"] or "reject")
            topic = row["topic_tag"] or "General Engineering"
            return ScoredIdea(
                item=item,
                samples=samples,
                median_composite=median_comp,
                verdict=verdict,
                topic_tag=topic,
            )
        except Exception:
            return None

    def _persist(self, scored: ScoredIdea) -> None:
        """Insert one scored idea into the spikes table."""
        if self.db_conn is None:
            return
        spike_id = str(uuid.uuid4())
        scores_payload = {
            "samples": [s.model_dump() for s in scored.samples],
            "median_composite": scored.median_composite,
            "verdict": scored.verdict,
        }
        self.db_conn.execute(
            """
            INSERT INTO spikes(id, category, hook_thesis, scores_json, status, topic_tag, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spike_id,
                scored.item.source,
                scored.item.title,
                json.dumps(scores_payload),
                scored.verdict,
                scored.topic_tag,
                scored.item.url,
            ),
        )
        self.db_conn.commit()
        log_event(
            self.db_conn,
            "idea_scored",
            f"spike={spike_id} verdict={scored.verdict} "
            f"median={scored.median_composite:.2f} topic={scored.topic_tag} title={scored.item.title!r}",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def iter_run(
        self,
        include_rejected: bool = False,
        max_items: Optional[int] = None,
        force_rescore: bool = False,
        rehydrate_cached: bool = True,
    ):
        """Yield (scored_idea, is_cached) dynamically as each item is evaluated.

        Allows real-time streaming of candidates and dedup progress.
        """
        items = self._pull_all()
        if max_items is not None and max_items > 0:
            items = items[:max_items]

        for item in items:
            if not force_rescore and self.db_conn is not None:
                cached = self._find_cached_spike(item)
                if cached is not None:
                    log_event(
                        self.db_conn,
                        "item_skipped_already_scored",
                        f"title={item.title!r} url={item.url!r}",
                    )
                    if rehydrate_cached:
                        if include_rejected or cached.verdict != "reject":
                            yield cached, True
                    continue

            scored = self.scorer.score_item(item)
            self._persist(scored)
            if include_rejected or scored.verdict != "reject":
                yield scored, False

    def run(
        self,
        include_rejected: bool = False,
        max_items: Optional[int] = None,
        force_rescore: bool = False,
        rehydrate_cached: bool = True,
    ) -> list[ScoredIdea]:
        """Pull → deduplicate → score → persist → return sorted candidates."""
        results = [
            scored
            for scored, _ in self.iter_run(
                include_rejected=include_rejected,
                max_items=max_items,
                force_rescore=force_rescore,
                rehydrate_cached=rehydrate_cached,
            )
        ]
        results.sort(key=lambda s: s.median_composite, reverse=True)
        return results
