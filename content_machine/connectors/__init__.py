"""Oracle connectors — ingestion layer (plan v2 §2.1).

Available connectors
--------------------
RSSConnector    — RSS and Atom feeds with ETag/304 caching
GitHubConnector — GitHub closed issues + PRs via PAT REST auth

Blocked (need tokens/credentials):
    SlackConnector  — requires bookmarks:read token
    GmailConnector  — requires GCP OAuth client (see spikes/RESULTS.md §6)
"""

from content_machine.connectors.base import BaseConnector, ConnectorItem, ConnectorResult
from content_machine.connectors.github import GitHubConnector
from content_machine.connectors.idea_bank import IdeaBankConnector
from content_machine.connectors.linkedin import LinkedInConnector
from content_machine.connectors.rss import RSSConnector

__all__ = [
    "BaseConnector",
    "ConnectorItem",
    "ConnectorResult",
    "RSSConnector",
    "GitHubConnector",
    "LinkedInConnector",
    "IdeaBankConnector",
]
