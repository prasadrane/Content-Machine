"""Build immutable editorial input from one owned version and owned settings."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
import sqlite3
from urllib.parse import parse_qsl, urlsplit

from content_machine.workflow.errors import WorkflowError
from content_machine.workflow.items import get_item
from content_machine.workflow.preferences import list_preferences
from content_machine.workflow.schemas import Principal
from content_machine.workflow.settings import get_profile
from content_machine.workflow.versions import get_version


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    source_id: str
    url: str
    title: str
    excerpt: str
    fetched_at: str
    title_only: bool


@dataclass(frozen=True, slots=True)
class ItemContext:
    notes: str
    experience: str | None
    interpretation: str | None
    sources: tuple[SourceEvidence, ...]
    preference_snapshot_id: str | None


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    segments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CreatorProfile:
    name: str
    role: str
    bio: str
    revision: int


@dataclass(frozen=True, slots=True)
class ActivePreference:
    preference_id: str
    text: str
    revision: int


@dataclass(frozen=True, slots=True)
class EditorialSnapshot:
    """A detached immutable value. Serialization returns a fresh JSON object."""
    owner_id: str
    item_id: str
    version_id: str
    revision: int
    destination: str
    format: str
    context: ItemContext
    artifact: ArtifactSnapshot
    profile: CreatorProfile | None
    preferences: tuple[ActivePreference, ...]
    # Older saved snapshots have no title. Never reconstruct it from live state.
    title: str | None = None

    def as_dict(self) -> dict:
        return json.loads(self.to_json())

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _safe_source_url(url: str) -> bool:
    """Reject credential-bearing URLs without echoing sensitive material."""
    try:
        parsed = urlsplit(url)
        if (url != url.strip() or any(ord(char) < 32 or ord(char) == 127 for char in url)
                or parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None):
            return False
        # Accessing port also rejects malformed ports.
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return False
        for name, value in parse_qsl(parsed.query, keep_blank_values=True) + parse_qsl(parsed.fragment, keep_blank_values=True):
            normalized = re.sub(r'[^a-z0-9]', '', name.lower())
            if value and (normalized in {'key', 'auth', 'sig'} or any(
                    marker in normalized for marker in ('token', 'secret', 'password', 'passwd', 'apikey',
                        'authorization', 'signature', 'credential', 'session', 'oauth', 'bearer'))):
                return False
        return True
    except ValueError:
        return False


def build_editorial_snapshot(conn: sqlite3.Connection, principal: Principal,
                             item_id: str, version_id: str) -> EditorialSnapshot:
    """Read a consistent owned snapshot without mutating caller-owned transactions.

    The caller is responsible for recording ``to_json()`` with its operation
    before contacting a model. The workflow version, profile and active
    preferences are captured in one SQLite read snapshot.
    """
    conn.execute('SAVEPOINT workflow_editorial_context')
    try:
        version = get_version(conn, principal, version_id, item_id=item_id)
        item = get_item(conn, principal, item_id)
        if item.working_revision != version.revision:
            raise WorkflowError(409, 'revision_conflict', 'The content changed before the context was captured.',
                                current={'working_revision': item.working_revision, 'stage': item.stage.value,
                                         'updated_at': item.updated_at, 'active_approval_id': item.active_approval_id})
        profile = get_profile(conn, principal)
        preferences = list_preferences(conn, principal)
        sources = []
        for source in version.context.sources:
            if not _safe_source_url(source.url):
                raise WorkflowError(422, 'unsafe_source_url',
                                    'A source URL is invalid or contains credentials. Update it before drafting.')
            sources.append(SourceEvidence(source_id=source.source_id, url=source.url, title=source.title,
                                          excerpt=source.excerpt, fetched_at=source.fetched_at,
                                          title_only=not bool(source.excerpt.strip())))
        creator = None
        if any(profile[field].strip() for field in ('name', 'role', 'bio')):
            creator = CreatorProfile(name=profile['name'], role=profile['role'],
                                     bio=profile['bio'], revision=profile['revision'])
        result = EditorialSnapshot(
            owner_id=principal.owner_id, item_id=version.item_id, version_id=version.version_id,
            title=item.title,
            revision=version.revision, destination=version.destination, format=version.format,
            context=ItemContext(notes=version.context.notes, experience=version.context.experience,
                                interpretation=version.context.interpretation, sources=tuple(sources),
                                preference_snapshot_id=version.context.preference_snapshot_id),
            artifact=ArtifactSnapshot(segments=tuple(version.artifact.segments)), profile=creator,
            preferences=tuple(ActivePreference(preference_id=entry['preference_id'],
                                              text=entry['text'], revision=entry['revision'])
                              for entry in preferences if entry['status'] == 'active'),
        )
    except BaseException:
        conn.execute('ROLLBACK TO SAVEPOINT workflow_editorial_context')
        conn.execute('RELEASE SAVEPOINT workflow_editorial_context')
        raise
    conn.execute('RELEASE SAVEPOINT workflow_editorial_context')
    return result
