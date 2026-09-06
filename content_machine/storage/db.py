"""SQLite persistence: spikes, transcripts, iterations, judge scores, lessons, audit log.

Lessons table carries governance fields required by plan v2 §6:
provenance, created/last-touched timestamps, embedding blob for conflict
detection, status for decay passes.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from .paths import home_root

DB_NAME = "content_machine.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS spikes(
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  category TEXT NOT NULL,
  hook_thesis TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '[]',
  scores_json TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'candidate',
  topic_tag TEXT NOT NULL DEFAULT 'General Engineering',
  source_url TEXT
);

CREATE TABLE IF NOT EXISTS transcripts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spike_id TEXT NOT NULL REFERENCES spikes(id),
  path TEXT NOT NULL,
  word_count INTEGER,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS iterations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spike_id TEXT NOT NULL REFERENCES spikes(id),
  iteration INTEGER NOT NULL,
  draft_path TEXT NOT NULL,
  council_review_json TEXT NOT NULL DEFAULT '{}',
  composite_raw REAL,
  composite_normalized REAL,
  threshold_met INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  draft_content TEXT
);

CREATE TABLE IF NOT EXISTS judge_score_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  judge_slot TEXT NOT NULL,
  model_config TEXT NOT NULL,
  spike_id TEXT,
  iteration INTEGER,
  dimension TEXT NOT NULL,
  raw_score REAL NOT NULL,
  normalized_score REAL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS lessons(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  rule_text TEXT NOT NULL UNIQUE,
  category TEXT NOT NULL DEFAULT 'negative_constraint',
  provenance_project TEXT,
  embedding BLOB,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  last_touched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  event TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS feed_cache(
  feed_url TEXT PRIMARY KEY,
  etag TEXT,
  last_modified TEXT,
  last_fetched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS seen_feed_items(
  guid TEXT PRIMARY KEY,
  feed_url TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    post_content TEXT NOT NULL,
    angle TEXT NOT NULL,
    perspective_text TEXT,
    initial_draft TEXT NOT NULL,
    final_comment TEXT NOT NULL,
    iteration_count INTEGER NOT NULL,
    peak_score REAL NOT NULL,
    verdict TEXT NOT NULL,
    judge_critiques TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_seen_feed_items_feed ON seen_feed_items(feed_url);
CREATE INDEX IF NOT EXISTS idx_history_judge
  ON judge_score_history(judge_slot, model_config, created_at);
CREATE INDEX IF NOT EXISTS idx_iterations_spike ON iterations(spike_id, iteration);
CREATE INDEX IF NOT EXISTS idx_transcripts_spike ON transcripts(spike_id);
"""


def get_feed_cache(conn: sqlite3.Connection, feed_url: str) -> tuple[str | None, str | None]:
    row = conn.execute(
        "SELECT etag, last_modified FROM feed_cache WHERE feed_url = ?", (feed_url,)
    ).fetchone()
    if row:
        return row["etag"], row["last_modified"]
    return None, None


def update_feed_cache(
    conn: sqlite3.Connection,
    feed_url: str,
    etag: str | None,
    last_modified: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO feed_cache(feed_url, etag, last_modified, last_fetched_at)
        VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        ON CONFLICT(feed_url) DO UPDATE SET
          etag = excluded.etag,
          last_modified = excluded.last_modified,
          last_fetched_at = excluded.last_fetched_at
        """,
        (feed_url, etag, last_modified),
    )
    conn.commit()


def get_seen_guids_for_feed(conn: sqlite3.Connection, feed_url: str) -> set[str]:
    rows = conn.execute(
        "SELECT guid FROM seen_feed_items WHERE feed_url = ?", (feed_url,)
    ).fetchall()
    return {row["guid"] for row in rows}


def record_seen_guids(
    conn: sqlite3.Connection, feed_url: str, guids: list[str] | set[str]
) -> None:
    if not guids:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO seen_feed_items(guid, feed_url) VALUES (?, ?)",
        [(g, feed_url) for g in guids],
    )
    conn.commit()



def db_path() -> Path:
    return home_root() / DB_NAME


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    cols = [c[1] for c in conn.execute("PRAGMA table_info(iterations)").fetchall()]
    if "draft_content" not in cols:
        conn.execute("ALTER TABLE iterations ADD COLUMN draft_content TEXT")
    spike_cols = [c[1] for c in conn.execute("PRAGMA table_info(spikes)").fetchall()]
    if "topic_tag" not in spike_cols:
        conn.execute("ALTER TABLE spikes ADD COLUMN topic_tag TEXT NOT NULL DEFAULT 'General Engineering'")
    if "source_url" not in spike_cols:
        conn.execute("ALTER TABLE spikes ADD COLUMN source_url TEXT")

    rows_to_backfill = conn.execute(
        "SELECT id, hook_thesis FROM spikes WHERE topic_tag = 'General Engineering' OR topic_tag IS NULL"
    ).fetchall()
    if rows_to_backfill:
        from content_machine.oracle.classifier import classify_content_topic
        for row in rows_to_backfill:
            hook_thesis = row["hook_thesis"] if isinstance(row, sqlite3.Row) else row[1]
            row_id = row["id"] if isinstance(row, sqlite3.Row) else row[0]
            topic = classify_content_topic(hook_thesis)
            if topic != "General Engineering":
                conn.execute("UPDATE spikes SET topic_tag = ? WHERE id = ?", (topic, row_id))
    conn.commit()


def connect(path: str | Path | None = None, init: bool = True) -> sqlite3.Connection:
    if str(path) == ":memory:":
        conn = sqlite3.connect(":memory:", check_same_thread=False)
    else:
        p = Path(path) if path else db_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(p, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if init:
        init_db(conn)
    return conn


def log_event(conn: sqlite3.Connection, event: str, detail: str = "") -> None:
    conn.execute("INSERT INTO audit_log(event, detail) VALUES (?, ?)", (event, detail))
    conn.commit()


def main() -> None:
    ap = argparse.ArgumentParser(description="Content Machine storage")
    ap.add_argument("--init", action="store_true", help="create tree + database schema")
    args = ap.parse_args()
    if args.init:
        from .paths import ensure_tree

        dirs = ensure_tree()
        conn = connect()
        log_event(conn, "storage_init", str(dirs["root"]))
        conn.close()
        print(f"initialized: {dirs['root']} ({DB_NAME})")


if __name__ == "__main__":
    main()
