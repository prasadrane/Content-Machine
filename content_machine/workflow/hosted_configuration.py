"""Parse explicit server configuration without reading secrets or connecting.

This contract describes configuration readiness only. It never mounts a
repository, opens a socket, mutates the environment, or claims database access.
The caller selects a connection mode after reviewing the actual provider's
connection details; hostnames and ports do not establish a mode automatically.
"""
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
import re
from urllib.parse import parse_qsl, unquote, urlsplit


class HostedConfigurationError(ValueError):
    """A typed, value-redacted server setup problem."""

    def __init__(self, code: str, variable: str):
        self.code = code
        self.variable = variable
        super().__init__(f'{code}: check {variable}')


class DatabaseConnectionMode(str, Enum):
    DIRECT = 'direct'
    SESSION_POOLER = 'session_pooler'
    TRANSACTION_POOLER = 'transaction_pooler'


@dataclass(frozen=True)
class HostedConfiguration:
    supabase_url: str
    database_mode: DatabaseConnectionMode
    database_url: str = field(repr=False)

    def readiness(self) -> dict:
        """Safe status for setup reporting; excludes credentials and addresses."""
        return {'configuration_ready': True, 'database_mode': self.database_mode.value,
                'live_database_verified': False, 'hosted_storage_enabled': False}


def _fail(code, variable):
    raise HostedConfigurationError(code, variable) from None


def _required(values, name):
    value = values.get(name)
    if value is None or isinstance(value, str) and not value.strip():
        _fail('hosted_configuration_missing', name)
    return value


def _hostname(host):
    # DNS names only: no URI escapes, Unix sockets, multiple hosts or backslashes.
    return isinstance(host, str) and len(host) <= 253 and all(
        re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
        for label in host.split('.'))


def _clean_text(value):
    return isinstance(value, str) and bool(value) and not any(
        char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)


def _origin(value):
    variable = 'SUPABASE_URL'
    code = 'hosted_supabase_url_invalid'
    if not _clean_text(value) or '\\' in value or re.search(r'%(?![0-9A-Fa-f]{2})', value):
        _fail(code, variable)
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == 'https' and _hostname(parts.hostname)
                 and parts.username is None and parts.password is None
                 and parts.port in (None, 443) and parts.path in ('', '/')
                 and not parts.query and not parts.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        _fail(code, variable)
    return value.rstrip('/')


def _database_url(value):
    variable = 'CONTENT_MACHINE_DATABASE_URL'
    code = 'hosted_database_url_invalid'
    if not _clean_text(value) or '\\' in value or re.search(r'%(?![0-9A-Fa-f]{2})', value):
        _fail(code, variable)
    try:
        parts = urlsplit(value)
        port = parts.port
        entries = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        options = dict(entries)
        database = unquote(parts.path[1:]) if parts.path.startswith('/') else ''
        # No query parameter may redirect credentials, relax verification,
        # choose a service file or inject connection/session options.
        valid = (parts.scheme in ('postgres', 'postgresql') and _hostname(parts.hostname)
                 and (port is None or 1 <= port <= 65535)
                 and bool(parts.username) and bool(parts.password)
                 and bool(database) and '/' not in database and '\\' not in database
                 and not parts.fragment and len(options) == len(entries)
                 and set(options) <= {'sslmode', 'sslrootcert'}
                 and options.get('sslmode') == 'verify-full'
                 and all(_clean_text(entry) for entry in options.values())
                 and all(ord(char) >= 32 and ord(char) != 127
                         for char in unquote(parts.username) + unquote(parts.password) + database))
    except (ValueError, TypeError):
        valid = False
    if not valid:
        _fail(code, variable)
    return value


def parse_hosted_configuration(values: Mapping[str, str]) -> HostedConfiguration:
    """Validate an explicitly supplied mapping; no implicit environment lookup.

    Require a fixed HTTPS origin, one TLS-verified PostgreSQL URL and an explicit
    direct/session_pooler/transaction_pooler decision. DNS reachability, CA file
    access, provider compatibility, credentials and migrations remain unverified.
    Use ``readiness()`` for reports, never serialize the configuration dataclass:
    ``database_url`` contains the server credential even though repr hides it.
    """
    if not isinstance(values, Mapping):
        _fail('hosted_configuration_invalid', 'server_configuration')
    origin = _origin(_required(values, 'SUPABASE_URL'))
    database = _required(values, 'CONTENT_MACHINE_DATABASE_URL')
    mode = _required(values, 'CONTENT_MACHINE_DATABASE_MODE')
    try:
        mode = DatabaseConnectionMode(mode)
    except (ValueError, TypeError):
        _fail('hosted_database_mode_invalid', 'CONTENT_MACHINE_DATABASE_MODE')
    return HostedConfiguration(origin, mode, _database_url(database))
