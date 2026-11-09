"""Creator-scoped source discovery through an explicitly trusted fetcher.

The existing RSS connector does not enforce an outbound network boundary.
Production must supply a fetcher that pins public DNS results to the connected
address, revalidates each redirect, avoids ambient proxy credentials, rejects
private/reserved destinations, and enforces response and time limits. No
network fetcher is installed by default.
"""
from __future__ import annotations

from collections.abc import Callable
from email.utils import format_datetime, parsedate_to_datetime
import re
import sqlite3
import time
from urllib.parse import urlsplit

from pydantic import ValidationError

from content_machine.connectors.base import ConnectorResult
from content_machine.workflow.persistence import atomic_write
from content_machine.workflow.schemas import Principal, SourceRef, utc_timestamp
from content_machine.workflow.settings import list_sources

Fetcher = Callable[[dict], ConnectorResult]


REFRESH_DEADLINE_SECONDS = 45.0


def refresh(conn: sqlite3.Connection, principal: Principal, fetch: Fetcher | None, *,
            deadline_seconds: float = REFRESH_DEADLINE_SECONDS,
            clock: Callable[[], float] = time.monotonic) -> dict:
    """Fetch enabled, owned sources without inventing results or mutating items.

    Once ``deadline_seconds`` have elapsed no further source is fetched; the
    partial results are returned with ``incomplete`` set and one error per
    skipped source.
    """
    sources = list_sources(conn, principal, enabled_only=True)
    result = {
        "status": "no_sources", "items": [], "errors": [],
        "history_available": False, "unchanged_sources": [],
    }
    if not sources:
        return result
    if not callable(fetch):
        result["status"] = "unavailable"
        return result

    seen = set()
    started = clock()
    for index, source in enumerate(sources):
        if clock() - started >= deadline_seconds:
            result["incomplete"] = True
            for skipped in sources[index:]:
                result["errors"].append(_error(skipped, "Skipped: the refresh time limit was reached."))
            break
        if source.get("kind") != "rss":
            result["errors"].append(_error(source, "This source type is unavailable."))
            continue
        try:
            batch = fetch(_cached_source(conn, principal, source, result))
            if not isinstance(batch, ConnectorResult):
                raise TypeError("fetcher must return ConnectorResult")
            _remember_validators(conn, principal, source, batch, result)
            if batch.not_modified:
                result["unchanged_sources"].append({
                    "source_id": source["source_id"], "source_name": source["name"],
                })
            for entry in batch.items:
                try:
                    if not _web_url(entry.url) or not entry.title.strip():
                        raise ValueError("source entry has incomplete metadata")
                    reference = SourceRef(
                        source_id=source["source_id"], url=entry.url, title=entry.title,
                        excerpt=entry.body, fetched_at=utc_timestamp(entry.fetched_at),
                    )
                except (ValueError, TypeError, AttributeError, ValidationError):
                    result["errors"].append(_error(source, "Some source entries have incomplete or unsupported metadata."))
                    continue
                key = (reference.source_id, reference.url)
                if key not in seen:
                    seen.add(key)
                    result["items"].append({**reference.model_dump(mode="json"), "source_name": source["name"]})
        except Exception:
            result["errors"].append(_error(source, "Could not retrieve this source."))

    if result["errors"]:
        result["status"] = "partial" if result["items"] else "failed"
    elif result["items"]:
        result["status"] = "ok"
    elif result["unchanged_sources"]:
        result["status"] = "history_unavailable"
    else:
        result["status"] = "empty"
    return result


def _validators(etag, modified):
    # Store only conditional GET headers, never cookies/authentication metadata.
    # ETag's opaque quoted value is public server metadata, not an auth token.
    if not isinstance(etag, str) or len(etag) > 512 or not re.fullmatch(r'(?:W/)?"[\x21\x23-\x7e]*"', etag):
        etag = None
    try:
        if (not isinstance(modified, str) or len(modified) > 128
                or format_datetime(parsedate_to_datetime(modified), usegmt=True) != modified):
            modified = None
    except (ValueError, TypeError, OverflowError):
        modified = None
    return etag, modified


def _cache_warning(result, source):
    result.setdefault('cache_warnings', []).append(
        _error(source, 'Conditional feed metadata could not be saved or loaded; source results are preserved.'))


def _cached_source(conn, principal, source, result):
    if conn is None:
        return source
    try:
        row = conn.execute(
            'SELECT etag, last_modified FROM workflow_discovery_cache '
            'WHERE owner_id=? AND source_id=? AND url=? AND source_revision=?',
            (principal.owner_id, source['source_id'], source['url'], source['revision']),
        ).fetchone()
        if row:
            etag, modified = _validators(*row)
            if etag or modified:
                return {**source, 'cache': {'url': source['url'], 'etag': etag, 'last_modified': modified}}
    except sqlite3.Error:
        _cache_warning(result, source)
    return source


def _remember_validators(conn, principal, source, batch, result):
    if conn is None or not hasattr(batch, 'cache_url'):
        return
    etag, modified = _validators(getattr(batch, 'etag', None), getattr(batch, 'last_modified', None))
    if batch.cache_url != source['url']:
        etag, modified = None, None
    try:
        with atomic_write(conn):
            # An in-flight source edit must not populate a new URL/revision with
            # an older request's validators, or alter the settings CAS revision.
            current = conn.execute('SELECT 1 FROM workflow_sources WHERE owner_id=? '
                'AND source_id=? AND url=? AND revision=? AND enabled=1',
                (principal.owner_id, source['source_id'], source['url'], source['revision'])).fetchone()
            if not current:
                return
            if etag or modified:
                conn.execute('INSERT INTO workflow_discovery_cache '
                    '(owner_id, source_id, url, source_revision, etag, last_modified) VALUES (?, ?, ?, ?, ?, ?) '
                    'ON CONFLICT(owner_id, source_id) DO UPDATE SET url=excluded.url, '
                    'source_revision=excluded.source_revision, etag=excluded.etag, last_modified=excluded.last_modified',
                    (principal.owner_id, source['source_id'], source['url'], source['revision'], etag, modified))
            else:
                conn.execute('DELETE FROM workflow_discovery_cache WHERE owner_id=? AND source_id=?',
                    (principal.owner_id, source['source_id']))
    except sqlite3.Error:
        _cache_warning(result, source)


def _error(source: dict, message: str) -> dict:
    return {"source_id": source["source_id"], "source_name": source["name"], "message": message}


def _web_url(value: str) -> bool:
    if not isinstance(value, str) or value != value.strip() or "\\" in value:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return bool(parsed.scheme.lower() in {"http", "https"} and parsed.hostname
                    and not any(char.isspace() for char in parsed.hostname)
                    and (port is None or 1 <= port <= 65535)
                    and parsed.username is None and parsed.password is None)
    except ValueError:
        return False
