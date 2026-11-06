"""Exact export of a historically approved workflow version.

Exports read the immutable version and a matching immutable approval. They
recompute the canonical digest as an integrity check, then serialize the exact
stored strings: one UTF-8 segment for single-text artifacts, or ordered
segments joined by two LF bytes for thread formats. Nothing is appended,
stripped, normalized or revalidated against today's limits.

The router receives bytes, safe filename/digest metadata and the JSON segment
payload for clipboard copy. No HTTP or generation dependency belongs here.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.format_registry import is_thread_format
from content_machine.workflow.items import get_item
from content_machine.workflow.schemas import (
    Approval,
    Artifact,
    ContentItem,
    ContentVersion,
    Principal,
)
from content_machine.workflow.versions import artifact_digest, get_version

_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)
_APPROVAL_SELECT = (
    "SELECT approval_id, owner_id, item_id, version_id, artifact_digest,"
    " destination, format, approved_by, approved_at"
    " FROM workflow_approvals"
)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80].rstrip("-")


def _safe_item_id(item_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9-]+", "-", item_id).strip("-").lower()
    return safe or "item"


def safe_filename(title: str, item_id: str, revision: int) -> str:
    """Return the frozen-contract download name, never a raw path or header."""

    base = _slug(title)
    if not base or base.upper() in _RESERVED:
        base = f"content-{_safe_item_id(item_id)}"
    return f"{base}-r{revision}.txt"


def artifact_bytes(
    destination: str, format: str, artifact: Artifact
) -> bytes:
    """Serialize exact stored segments without normalizing or appending text."""

    if is_thread_format(format):
        return "\n\n".join(artifact.segments).encode("utf-8")
    if len(artifact.segments) != 1:
        raise ValueError(
            f"{destination}/{format} export requires exactly one segment"
        )
    return artifact.segments[0].encode("utf-8")


@dataclass(frozen=True)
class ExportResult:
    """A historical export plus the metadata the router needs."""

    version_id: str
    item_id: str
    revision: int
    destination: str
    format: str
    artifact_digest: str
    segments: list[str]
    content: bytes
    filename: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Disposition": f'attachment; filename="{self.filename}"',
            "X-Artifact-Digest": self.artifact_digest,
        }

    def as_json(self) -> dict[str, Any]:
        """Return the C10-ready segment payload for copy/thread download."""

        return {
            "version_id": self.version_id,
            "destination": self.destination,
            "format": self.format,
            "artifact_digest": self.artifact_digest,
            "segments": list(self.segments),
        }


def _acknowledged(item: ContentItem) -> dict[str, object]:
    return {
        "working_revision": item.working_revision,
        "stage": item.stage.value,
        "updated_at": item.updated_at,
        "active_approval_id": item.active_approval_id,
    }


def _approval_required(item: ContentItem, detail: str) -> WorkflowError:
    return WorkflowError(
        409,
        "approval_required",
        detail,
        current=_acknowledged(item),
    )


def _matching_approval(
    conn: sqlite3.Connection,
    item: ContentItem,
    version: ContentVersion,
    digest: str,
) -> Approval | None:
    row = conn.execute(
        f"{_APPROVAL_SELECT}"
        " WHERE owner_id = ? AND item_id = ? AND version_id = ?"
        " AND destination = ? AND format = ? AND artifact_digest = ?"
        " ORDER BY approved_at DESC, approval_id DESC LIMIT 1",
        (
            item.owner_id,
            item.item_id,
            version.version_id,
            version.destination,
            version.format,
            digest,
        ),
    ).fetchone()
    return Approval.model_validate(dict(row)) if row is not None else None


def export_version(
    conn: sqlite3.Connection,
    principal: Principal,
    item_id: str,
    version_id: str,
) -> ExportResult:
    """Export one owned version only when a matching historical approval exists."""

    version = get_version(conn, principal, version_id, item_id=item_id)
    item = get_item(conn, principal, item_id)
    recomputed = artifact_digest(
        version.destination, version.format, version.artifact
    )
    if version.artifact_digest != recomputed:
        raise _approval_required(
            item, "The approved snapshot failed its artifact integrity check"
        )
    approval = _matching_approval(conn, item, version, recomputed)
    if approval is None:
        raise _approval_required(
            item, "A matching approval for this exact version is required"
        )
    try:
        content = artifact_bytes(
            version.destination, version.format, version.artifact
        )
    except ValueError as exc:
        raise _approval_required(item, str(exc)) from exc
    return ExportResult(
        version_id=version.version_id,
        item_id=item.item_id,
        revision=version.revision,
        destination=version.destination,
        format=version.format,
        artifact_digest=recomputed,
        segments=list(version.artifact.segments),
        content=content,
        filename=safe_filename(item.title, item.item_id, version.revision),
    )


__all__ = [
    "ExportResult",
    "artifact_bytes",
    "export_version",
    "safe_filename",
]
