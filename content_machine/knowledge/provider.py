"""Centralized editorial context provider for drafters and council writing agents."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from content_machine.storage import paths

logger = logging.getLogger(__name__)

RULE_PATTERN = re.compile(r"^\s*(?:\d+\.|\-|\*)\s*\*\*(Rule\s+\d+[^:*]+)(?::|\*\*:?)\s*(.+)$", re.MULTILINE)


def _resolve_file(filename: str, home_root: Path | None = None) -> Path:
    """Resolve knowledge file, refreshing the runtime copy from the seed on content drift."""
    root = home_root or paths.home_root()
    runtime_dir = root / "knowledge"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_file = runtime_dir / filename
    seed_file = paths.SEED_DIR / filename

    if seed_file.is_file():
        try:
            paths.sync_seed(seed_file, runtime_file)
        except Exception as e:
            logger.warning("Failed to sync %s from seed: %s", filename, e)

    if runtime_file.is_file():
        return runtime_file
    return seed_file


def get_style_guide(home_root: Path | None = None) -> str:
    """Return the full content of 01_style-guide.md."""
    path = _resolve_file("01_style-guide.md", home_root)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def get_voice_guide(home_root: Path | None = None) -> str:
    """Return the full content of 02_voice-guide.md."""
    path = _resolve_file("02_voice-guide.md", home_root)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return ""


def get_governed_rules(
    conn: sqlite3.Connection | None = None, home_root: Path | None = None
) -> list[str]:
    """Return list of active governed editorial rules from 03_content-lessons.md and SQLite."""
    rules: list[str] = []
    seen: set[str] = set()

    # 1. Read from 03_content-lessons.md
    path = _resolve_file("03_content-lessons.md", home_root)
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        for match in RULE_PATTERN.finditer(text):
            prefix = match.group(1).strip()
            body = match.group(2).strip()
            rule_str = f"{prefix}: {body}"
            clean_key = body.lower()
            if clean_key not in seen:
                seen.add(clean_key)
                rules.append(rule_str)

    # 2. Sync to and load from SQLite lessons table if connection provided
    if conn is not None:
        try:
            # Sync rules from markdown to DB if not present
            for r in rules:
                try:
                    conn.execute(
                        """
                        INSERT INTO lessons (rule_text, category, provenance_project, status)
                        VALUES (?, 'negative_constraint', 'seed-knowledge', 'active')
                        ON CONFLICT(rule_text) DO UPDATE SET status='active'
                        """,
                        (r,),
                    )
                except Exception:
                    pass
            conn.commit()

            # Load active rules from DB
            db_rows = conn.execute(
                "SELECT rule_text FROM lessons WHERE status='active' ORDER BY id"
            ).fetchall()
            for row in db_rows:
                r_text = row[0] if isinstance(row, (tuple, list)) else row["rule_text"]
                clean_key = r_text.strip().lower()
                if clean_key not in seen:
                    seen.add(clean_key)
                    rules.append(r_text.strip())
        except Exception as e:
            logger.warning("Failed to sync/query SQLite lessons: %s", e)

    return rules


def get_editorial_context(
    conn: sqlite3.Connection | None = None, home_root: Path | None = None
) -> dict[str, Any]:
    """Assemble full editorial context containing styles, voice guide, and governed rules."""
    style_guide = get_style_guide(home_root)
    voice_guide = get_voice_guide(home_root)
    active_rules = get_governed_rules(conn, home_root)

    style_section = f"\n# Author Style Guide\n{style_guide}\n" if style_guide else ""
    voice_section = f"\n# Author Voice & Persona Guide\n{voice_guide}\n" if voice_guide else ""
    rules_section = ""
    if active_rules:
        rules_section = "\nGOVERNED EDITORIAL RULES (must obey every rule):\n" + "\n".join(
            f"- {r}" for r in active_rules
        ) + "\n"

    full_context_prompt = f"{style_section}\n{voice_section}\n{rules_section}".strip()

    return {
        "style_guide": style_guide,
        "voice_guide": voice_guide,
        "active_rules": active_rules,
        "style_section": style_section,
        "voice_section": voice_section,
        "rules_section": rules_section,
        "full_context_prompt": full_context_prompt,
    }
