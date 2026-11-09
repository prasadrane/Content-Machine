"""Opt-in RSS transport with a pinned public address and bounded resources.

No global feed cache is kept. A trusted caller may pass owner-scoped validators
as ``source['cache']`` with a matching ``url``. The returned result exposes
validators for that same URL. The caller owns persistence and authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import http.client
import ipaddress
import queue
import socket
import ssl
import threading
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote, urljoin, urlsplit

from content_machine.connectors.base import ConnectorItem, ConnectorResult
from content_machine.connectors.rss import _parse_feed, clean_html_content

TOTAL_TIMEOUT = 15.0
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
MAX_ITEMS = 25
_NETWORK_SLOTS = threading.BoundedSemaphore(4)
_DNS_SLOTS = threading.BoundedSemaphore(4)
_PARSE_SLOTS = threading.BoundedSemaphore(4)
_TRANSITION = tuple(ipaddress.ip_network(value) for value in (
    '64:ff9b::/96', '64:ff9b:1::/48', '2002::/16', '2001::/32',
))
class FetchError(Exception):
    """A feed could not be safely retrieved or parsed."""
@dataclass
class RSSFetchResult(ConnectorResult):
    etag: str | None = None
    last_modified: str | None = None
    cache_url: str | None = None
def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise FetchError('Feed request timed out')
    return remaining


def _bounded_call(operation, deadline: float, slots: threading.BoundedSemaphore):
    """Limit outstanding daemon jobs even when DNS or a parser does not return."""
    if not slots.acquire(timeout=_remaining(deadline)):
        raise FetchError('Feed request timed out')
    outcome = queue.Queue(maxsize=1)

    def run():
        try:
            outcome.put((True, operation()))
        except Exception as exc:
            outcome.put((False, exc))
        finally:
            slots.release()

    try:
        threading.Thread(target=run, daemon=True).start()
    except Exception:
        slots.release()
        raise
    try:
        success, value = outcome.get(timeout=_remaining(deadline))
    except queue.Empty as exc:
        raise FetchError('Feed request timed out') from exc
    if not success:
        raise FetchError('Feed operation failed') from value
    return value


_ALLOWED_PORTS = frozenset({80, 443})


def _parse_url(value: str):
    if not isinstance(value, str) or value != value.strip() or '\\' in value:
        raise FetchError('Invalid feed URL')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise FetchError('Invalid feed URL')
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        configured_port = parsed.port
        port = configured_port if configured_port is not None else (443 if parsed.scheme == 'https' else 80)
        if (parsed.scheme not in {'http', 'https'} or not host or parsed.username is not None
                or parsed.password is not None or parsed.fragment or port not in _ALLOWED_PORTS
                or '%' in host or any(char.isspace() for char in host)):
            raise ValueError('invalid URL')
        host = host.encode('idna').decode('ascii')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            if not _public_address(host):
                raise ValueError('non-public address')
    except (ValueError, UnicodeError) as exc:
        raise FetchError('Invalid feed URL') from exc
    return parsed, host, port


def _public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if (not address.is_global or address.is_multicast or address.is_reserved
            or address.is_loopback or address.is_link_local or address.is_unspecified):
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped or any(address in network for network in _TRANSITION):
            return False
    return True


def _resolve(host: str, port: int, deadline: float):
    records = _bounded_call(
        lambda: socket.getaddrinfo(host, port, type=socket.SOCK_STREAM), deadline, _DNS_SLOTS,
    )
    if not records:
        raise FetchError('Feed host has no public address')
    addresses = []
    for family, socktype, protocol, _, sockaddr in records:
        if (family not in (socket.AF_INET, socket.AF_INET6) or socktype != socket.SOCK_STREAM
                or protocol not in (0, socket.IPPROTO_TCP) or not _public_address(sockaddr[0])):
            raise FetchError('Feed host contains a non-public address')
        if family == socket.AF_INET6:
            if len(sockaddr) > 3 and sockaddr[3]:
                raise FetchError('Scoped IPv6 feed addresses are not supported')
            target = (sockaddr[0], port, 0, 0)
        else:
            target = (sockaddr[0], port)
        addresses.append((family, socktype, protocol, target))
    return addresses[0]
def _validator(value):
    if not isinstance(value, str) or not value or len(value) > 512:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    return value


def _headers(source: dict, url: str, host: str, port: int, scheme: str) -> dict:
    authority = f'[{host}]' if ':' in host else host
    default_port = 443 if scheme == 'https' else 80
    if port != default_port:
        authority += f':{port}'
    headers = {'Host': authority, 'User-Agent': 'ContentMachine/3.0',
               'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
               'Accept-Encoding': 'identity', 'Connection': 'close'}
    cache = source.get('cache')
    if isinstance(cache, dict) and cache.get('url') == url:
        etag = _validator(cache.get('etag'))
        modified = _validator(cache.get('last_modified'))
        if etag:
            headers['If-None-Match'] = etag
        if modified:
            headers['If-Modified-Since'] = modified
    return headers


def _request(url: str, source: dict, deadline: float, active: dict, lock: threading.Lock):
    parsed, host, port = _parse_url(url)
    family, socktype, protocol, target = _resolve(host, port, deadline)
    sock = socket.socket(family, socktype, protocol)
    with lock:
        active['socket'] = sock
    response = None
    try:
        sock.settimeout(_remaining(deadline))
        sock.connect(target)
        if parsed.scheme == 'https':
            context = ssl.create_default_context()
            if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
                raise FetchError('TLS certificate verification is unavailable')
            wrapped = context.wrap_socket(sock, server_hostname=host, do_handshake_on_connect=False)
            with lock:
                active['socket'] = wrapped
            sock = wrapped
            sock.settimeout(_remaining(deadline))
            sock.do_handshake()
        path = quote(parsed.path or '/', safe="/%:@!$&'()*+,;=-._~%")
        if parsed.query:
            path += '?' + quote(parsed.query, safe="=&/?%:@!$'()*+,;~-._")
        conn = http.client.HTTPConnection(host, port, timeout=_remaining(deadline))
        conn.sock = sock
        conn.request('GET', path, headers=_headers(source, url, host, port, parsed.scheme))
        response = conn.getresponse()
        _remaining(deadline)
        if response.status in (301, 302, 303, 307, 308):
            return response.status, response.getheader('Location'), None, None, None
        if response.status == 304:
            return 304, None, b'', response.getheader('ETag'), response.getheader('Last-Modified')
        if response.status != 200:
            raise FetchError('Feed server returned an error')
        encoding = response.getheader('Content-Encoding')
        if encoding and encoding.lower() != 'identity':
            raise FetchError('Compressed feed responses are not supported')
        length = response.getheader('Content-Length')
        if length is not None and (not length.isdigit() or int(length) > MAX_BYTES):
            raise FetchError('Feed exceeds the size limit')
        body = bytearray()
        while True:
            _remaining(deadline)
            chunk = response.read(min(65536, MAX_BYTES + 1 - len(body)))
            if not chunk:
                break
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                raise FetchError('Feed exceeds the size limit')
        return 200, None, bytes(body), response.getheader('ETag'), response.getheader('Last-Modified')
    finally:
        with lock:
            active['socket'] = None
        if response is not None:
            response.close()
        sock.close()
def _parse_items(body: bytes, source_name: str) -> list[ConnectorItem]:
    class FeedTree(ET.TreeBuilder):
        def doctype(self, name, pubid, system):
            raise FetchError('Feed document types are not supported')

    # Validate before the shared connector parser: a login page is unavailable,
    # not an empty feed. Parser callbacks catch DTDs in every XML encoding.
    root = ET.fromstring(body, parser=ET.XMLParser(target=FeedTree()))
    if root.tag not in {'rss', '{http://www.w3.org/2005/Atom}feed'}:
        raise FetchError('Unsupported feed document')
    # The shared legacy parser chooses the first link. Discovery references
    # must point at an article, never an Atom API self link or media enclosure.
    atom = '{http://www.w3.org/2005/Atom}'
    for entry in root.findall(atom + 'entry'):
        for link in list(entry.findall(atom + 'link')):
            if link.get('rel', 'alternate') != 'alternate':
                entry.remove(link)
    raw_items = _parse_feed(ET.tostring(root, encoding='utf-8'))
    now = datetime.now(timezone.utc)
    return [ConnectorItem(title=entry['title'], url=entry['url'],
                          body=clean_html_content(entry['body']), source=source_name,
                          fetched_at=now, guid=entry['guid'], published_at=entry['published_at'])
            for entry in raw_items[:MAX_ITEMS]]


def _fetch_in_process(source: dict) -> RSSFetchResult:
    """Fetch one configured RSS feed without using proxies or shared cache."""
    if source.get('kind') != 'rss':
        raise FetchError('Unsupported source type')
    initial_url = source.get('url')
    _parse_url(initial_url)
    deadline = time.monotonic() + TOTAL_TIMEOUT
    if not _NETWORK_SLOTS.acquire(timeout=_remaining(deadline)):
        raise FetchError('Feed request timed out')
    active = {'socket': None}
    lock = threading.Lock()

    def expire():
        with lock:
            sock = active['socket']
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                sock.close()

    timer = None
    try:
        timer = threading.Timer(_remaining(deadline), expire)
        timer.daemon = True
        timer.start()
        current = initial_url
        for redirect_count in range(MAX_REDIRECTS + 1):
            status, location, body, etag, modified = _request(
                current, source if redirect_count == 0 else {}, deadline, active, lock,
            )
            if status not in (301, 302, 303, 307, 308):
                break
            if not location or redirect_count == MAX_REDIRECTS:
                raise FetchError('Feed redirect limit exceeded')
            destination = urljoin(current, location)
            if urlsplit(current).scheme == 'https' and urlsplit(destination).scheme != 'https':
                raise FetchError('Feed redirect downgraded HTTPS')
            _parse_url(destination)
            current = destination
        _remaining(deadline)
        cache_url = initial_url if current == initial_url else None
        if status == 304:
            cache = source.get('cache') if cache_url else None
            if isinstance(cache, dict) and cache.get('url') == cache_url:
                etag = etag or cache.get('etag')
                modified = modified or cache.get('last_modified')
            return RSSFetchResult(source=source['name'], not_modified=True,
                                  etag=_validator(etag), last_modified=_validator(modified), cache_url=cache_url)
        items = _bounded_call(lambda: _parse_items(body, source['name']), deadline, _PARSE_SLOTS)
        _remaining(deadline)
        return RSSFetchResult(source=source['name'], items=items,
                              etag=_validator(etag) if cache_url else None,
                              last_modified=_validator(modified) if cache_url else None, cache_url=cache_url)
    except FetchError:
        raise
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise FetchError('Feed request failed') from exc
    finally:
        if timer is not None:
            timer.cancel()
        _NETWORK_SLOTS.release()


def fetch(source: dict) -> RSSFetchResult:
    """Run the transport under a bounded child-process supervisor."""
    from content_machine.workflow.safe_rss_process import fetch as isolated_fetch
    return isolated_fetch(source)
