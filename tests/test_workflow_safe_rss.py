"""No-network verification of the opt-in, pinned-address RSS transport."""
from io import BytesIO
import socket
import ssl
import threading
import time
from unittest import TestCase
from unittest.mock import patch

from content_machine.workflow import safe_rss


RSS = b'''<?xml version="1.0"?><rss><channel>
<item><title>Engineering update</title><link>https://site.example/post</link>
<description>Real &amp; useful</description><guid>one</guid></item></channel></rss>'''
ATOM = b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom entry</title><link href="https://site.example/atom"/>
<summary>Source excerpt</summary><id>two</id></entry></feed>'''


def reply(body=RSS, status="200 OK", headers=None):
    header_text = ''.join(f'{key}: {value}\r\n' for key, value in (headers or {}).items())
    return f'HTTP/1.1 {status}\r\n{header_text}Content-Length: {len(body)}\r\n\r\n'.encode() + body


def addresses(*values):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (value, 443)) for value in values]


class FakeSocket:
    def __init__(self, response):
        self.response = response
        self.sent = b''
        self.connected = None
        self.closed = False

    def settimeout(self, value):
        self.timeout = value

    def connect(self, address):
        self.connected = address

    def sendall(self, value):
        self.sent += value

    def makefile(self, *args, **kwargs):
        return BytesIO(self.response)

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


class FakeContext:
    check_hostname = True
    verify_mode = ssl.CERT_REQUIRED

    def __init__(self):
        self.names = []

    def wrap_socket(self, sock, *, server_hostname, do_handshake_on_connect):
        self.names.append(server_hostname)
        sock.do_handshake = lambda: None
        return sock


class SafeRSSTest(TestCase):
    def source(self, **changes):
        return {'source_id': 'one', 'name': 'Feed', 'kind': 'rss', 'url': 'https://feed.example/rss', **changes}

    def run_fetch(self, source, payload=RSS, headers=None):
        sock = FakeSocket(reply(payload, headers=headers))
        context = FakeContext()
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')) as dns, \
             patch.object(socket, 'socket', return_value=sock) as constructor, \
             patch.object(ssl, 'create_default_context', return_value=context):
            result = safe_rss._fetch_in_process(source)
        return result, sock, context, dns, constructor

    def test_direct_connection_is_pinned_to_checked_ip_and_tls_hostname(self):
        result, sock, context, dns, constructor = self.run_fetch(self.source())
        self.assertEqual(dns.call_count, 1)
        self.assertEqual(sock.connected[0], '8.8.8.8')
        self.assertEqual(context.names, ['feed.example'])
        self.assertTrue(constructor.called)
        self.assertIn(b'Host: feed.example', sock.sent)
        self.assertEqual(result.items[0].title, 'Engineering update')
        self.assertEqual(result.items[0].url, 'https://site.example/post')
        self.assertEqual(result.items[0].body, 'Real & useful')
        self.assertEqual(result.items[0].source, 'Feed')
        self.assertIsNotNone(result.items[0].fetched_at)
        self.assertTrue(sock.closed)

    def test_atom_entries_keep_the_real_link_and_summary(self):
        result, *_ = self.run_fetch(self.source(), ATOM)
        self.assertEqual((result.items[0].title, result.items[0].url, result.items[0].body),
                         ('Atom entry', 'https://site.example/atom', 'Source excerpt'))

    def test_non_feed_xml_and_dtd_are_failures_not_empty_successes(self):
        payloads = [b'<html><body>Login required</body></html>',
                    b'<!DOCTYPE rss [<!ENTITY word "expanded">]><rss><channel/></rss>',
                    '<!DOCTYPE rss [<!ENTITY word "expanded">]><rss><channel/></rss>'.encode('utf-16')]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(safe_rss.FetchError):
                self.run_fetch(self.source(), payload)

    def test_atom_self_and_enclosure_links_do_not_replace_article_url(self):
        payload = ATOM.replace(b'<link href=', b'<link rel="self" href="https://api.example/entry"/>'
            b'<link rel="enclosure" href="https://site.example/audio.mp3"/><link href=')
        result, *_ = self.run_fetch(self.source(), payload)
        self.assertEqual(result.items[0].url, 'https://site.example/atom')

    def test_rejects_credentials_private_reserved_multicast_and_mixed_dns(self):
        urls = ['https://user:pass@feed.example/rss', 'file:///etc/passwd',
                'https://127.0.0.1/rss', 'https://feed.example:bad/rss',
                'https://feed.example:0/rss', 'https://feed.example:65536/rss']
        for url in urls:
            with self.subTest(url=url), patch.object(socket, 'socket') as constructor, \
                 patch.object(socket, 'getaddrinfo') as dns:
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss._fetch_in_process(self.source(url=url))
                constructor.assert_not_called()
                dns.assert_not_called()

    def test_ipv6_private_mapped_and_transition_addresses_are_rejected(self):
        for ip in ['::1', 'fc00::1', 'fe80::1', 'ff02::1', '::ffff:127.0.0.1',
                   '2002:7f00:1::1', '64:ff9b::7f00:1']:
            records = [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', (ip, 443, 0, 0))]
            with self.subTest(ip=ip), patch.object(socket, 'getaddrinfo', return_value=records), \
                 patch.object(socket, 'socket') as constructor:
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss._fetch_in_process(self.source())
                constructor.assert_not_called()

    def test_non_stream_dns_records_are_rejected(self):
        records = [(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP, '', ('8.8.8.8', 443))]
        with patch.object(socket, 'getaddrinfo', return_value=records), \
             patch.object(socket, 'socket') as constructor:
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
            constructor.assert_not_called()
        for answer in [addresses('127.0.0.1'), addresses('10.0.0.1'), addresses('169.254.169.254'),
                       addresses('224.0.0.1'), addresses('240.0.0.1'), addresses('8.8.8.8', '127.0.0.1')]:
            with self.subTest(answer=answer), patch.object(socket, 'getaddrinfo', return_value=answer), \
                 patch.object(socket, 'socket') as constructor:
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss._fetch_in_process(self.source())
                constructor.assert_not_called()

    def test_redirect_to_private_ip_is_checked_before_connect(self):
        first = FakeSocket(reply(b'', '302 Found', {'Location': 'https://private.example/next'}))
        def lookup(host, *args, **kwargs):
            return addresses('8.8.8.8' if host == 'feed.example' else '127.0.0.1')
        with patch.object(socket, 'getaddrinfo', side_effect=lookup), \
             patch.object(socket, 'socket', return_value=first) as constructor, \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
        self.assertEqual(constructor.call_count, 1)

    def test_redirect_limit_and_https_downgrade_are_rejected(self):
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', side_effect=lambda *args: FakeSocket(
                 reply(b'', '302 Found', {'Location': 'https://feed.example/again'}))) as constructor, \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
        self.assertEqual(constructor.call_count, safe_rss.MAX_REDIRECTS + 1)
        first = FakeSocket(reply(b'', '301 Moved Permanently', {'Location': 'http://site.example/next'}))
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', return_value=first), \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())

    def test_cross_host_redirect_does_not_forward_conditional_validator(self):
        first = FakeSocket(reply(b'', '302 Found', {'Location': 'https://other.example/rss'}))
        second = FakeSocket(reply(RSS, headers={'ETag': '"other"'}))
        source = self.source(cache={'url': 'https://feed.example/rss', 'etag': '"one"'})
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', side_effect=[first, second]), \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            result = safe_rss._fetch_in_process(source)
        self.assertIn(b'If-None-Match: "one"', first.sent)
        self.assertNotIn(b'If-None-Match:', second.sent)
        self.assertIsNone(result.cache_url)
        self.assertIsNone(result.etag)

    def test_304_retains_owned_validators_when_server_omits_them(self):
        sock = FakeSocket(reply(b'', '304 Not Modified'))
        source = self.source(cache={'url': 'https://feed.example/rss', 'etag': '"existing"',
                                    'last_modified': 'Fri, 06 Nov 2026 12:00:00 GMT'})
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', return_value=sock), \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            result = safe_rss._fetch_in_process(source)
        self.assertTrue(result.not_modified)
        self.assertEqual(result.etag, '"existing"')
        self.assertEqual(result.last_modified, 'Fri, 06 Nov 2026 12:00:00 GMT')

    def test_network_watchdog_interrupts_a_slow_read(self):
        gate = threading.Event()
        class SlowFile(BytesIO):
            def read(self, size=-1):
                gate.wait(1)
                raise OSError('closed')
        class SlowSocket(FakeSocket):
            def makefile(self, *args, **kwargs):
                return SlowFile(b'HTTP/1.1 200 OK\r\nContent-Length: 20\r\n\r\n')
            def shutdown(self, how):
                gate.set()
        sock = SlowSocket(b'')
        with patch.object(safe_rss, 'TOTAL_TIMEOUT', 0.05), \
             patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', return_value=sock), \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            started = time.monotonic()
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
            self.assertLess(time.monotonic() - started, 0.5)

    def test_rejects_unverified_tls_context_and_oversized_body(self):
        context = FakeContext()
        context.check_hostname = False
        with patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', return_value=FakeSocket(reply())), \
             patch.object(ssl, 'create_default_context', return_value=context):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
        with patch.object(safe_rss, 'MAX_BYTES', 10):
            with self.assertRaises(safe_rss.FetchError):
                self.run_fetch(self.source())

    def test_conditional_headers_are_explicit_url_scoped_and_never_shared(self):
        cached = self.source(cache={'url': 'https://feed.example/rss', 'etag': '"owner-a"'})
        first, first_socket, *_ = self.run_fetch(cached, headers={'ETag': '"new"'})
        self.assertIn(b'If-None-Match: "owner-a"', first_socket.sent)
        self.assertEqual((first.etag, first.cache_url), ('"new"', 'https://feed.example/rss'))
        _, second_socket, *_ = self.run_fetch(self.source(source_id='two'))
        self.assertNotIn(b'If-None-Match:', second_socket.sent)
        _, wrong_socket, *_ = self.run_fetch(self.source(cache={'url': 'https://different.example/rss', 'etag': '"secret"'}))
        self.assertNotIn(b'If-None-Match:', wrong_socket.sent)

    def test_dns_time_is_bounded_even_if_resolver_blocks(self):
        gate = threading.Event()
        def stalled(*args, **kwargs):
            gate.wait(0.5)
            return addresses('8.8.8.8')
        try:
            with patch.object(safe_rss, 'TOTAL_TIMEOUT', 0.05), \
                 patch.object(socket, 'getaddrinfo', side_effect=stalled), \
                 patch.object(socket, 'socket') as constructor:
                started = time.monotonic()
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss._fetch_in_process(self.source())
                self.assertLess(time.monotonic() - started, 0.3)
                constructor.assert_not_called()
        finally:
            gate.set()

    def test_parser_time_is_bounded_and_no_extra_workers_start(self):
        gate = threading.Event()
        def stalled(*args, **kwargs):
            gate.wait(0.5)
            return []
        try:
            with patch.object(safe_rss, 'TOTAL_TIMEOUT', 0.05), \
                 patch.object(safe_rss, '_parse_feed', side_effect=stalled):
                started = time.monotonic()
                with self.assertRaises(safe_rss.FetchError):
                    self.run_fetch(self.source())
                self.assertLess(time.monotonic() - started, 0.3)
        finally:
            gate.set()

    def test_concurrency_slot_is_released_if_the_deadline_expires_after_acquisition(self):
        slots = threading.BoundedSemaphore(1)
        with patch.object(safe_rss, '_NETWORK_SLOTS', slots), \
             patch.object(safe_rss, '_remaining', side_effect=[1.0, safe_rss.FetchError('expired')]):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())
        self.assertTrue(slots.acquire(blocking=False))
        slots.release()

    def test_network_concurrency_wait_is_bounded(self):
        slots = threading.BoundedSemaphore(1)
        slots.acquire()
        try:
            with patch.object(safe_rss, '_NETWORK_SLOTS', slots), \
                 patch.object(safe_rss, 'TOTAL_TIMEOUT', 0.05), \
                 patch.object(socket, 'socket') as constructor:
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss._fetch_in_process(self.source())
                constructor.assert_not_called()
        finally:
            slots.release()

    def test_oversized_body_without_content_length_is_rejected(self):
        sock = FakeSocket(b'HTTP/1.1 200 OK\r\nConnection: close\r\n\r\n' + b'x' * 11)
        with patch.object(safe_rss, 'MAX_BYTES', 10), \
             patch.object(socket, 'getaddrinfo', return_value=addresses('8.8.8.8')), \
             patch.object(socket, 'socket', return_value=sock), \
             patch.object(ssl, 'create_default_context', return_value=FakeContext()):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss._fetch_in_process(self.source())

    def test_malformed_conditional_validator_never_reaches_headers(self):
        source = self.source(cache={'url': 'https://feed.example/rss', 'etag': 'bad\r\nInjected: yes'})
        _, sock, *_ = self.run_fetch(source)
        self.assertNotIn(b'Injected:', sock.sent)
        self.assertNotIn(b'If-None-Match:', sock.sent)
