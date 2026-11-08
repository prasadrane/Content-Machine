"""Offline process-supervisor tests; no DNS or HTTP requests are made."""
import json
import os
import subprocess
import sys
import threading
import time
from unittest import TestCase
from unittest.mock import patch

from content_machine.workflow import safe_rss, safe_rss_process


SOURCE = {'source_id': 'one', 'name': 'Feed', 'kind': 'rss', 'url': 'https://feed.example/rss'}
RESULT = {
    'ok': True,
    'result': {
        'source': 'Feed', 'not_modified': False, 'etag': '"fresh"',
        'last_modified': None, 'cache_url': 'https://feed.example/rss',
        'items': [{
            'title': 'Real source title', 'url': 'https://site.example/post',
            'body': 'Exact source text', 'source': 'Feed', 'guid': 'one',
            'fetched_at': '2026-11-06T12:00:00+00:00', 'published_at': None,
        }],
    },
}


def command(script):
    return [sys.executable, '-I', '-c', script]


class ProcessSupervisorTest(TestCase):
    def test_packaged_child_loads_transport_and_rejects_private_ip_without_dns(self):
        environment = safe_rss_process._environment()
        result = subprocess.run(
            safe_rss_process._child_command(), input=json.dumps({**SOURCE, 'url': 'http://127.0.0.1/feed'}).encode(),
            env=environment, capture_output=True, timeout=10, check=True,
        )
        self.assertEqual(json.loads(result.stdout), {'ok': False})

    def test_real_child_has_no_ambient_secrets_or_proxy_and_preserves_result(self):
        script = (
            "import json,os,sys; request=json.loads(sys.stdin.buffer.read()); "
            "assert request['url']=='https://feed.example/rss'; "
            "assert 'CM_TEST_SECRET' not in os.environ; "
            "assert not any(k.lower().endswith('_proxy') for k in os.environ); "
            f"print({json.dumps(json.dumps(RESULT))})"
        )
        with patch.dict(os.environ, {'CM_TEST_SECRET': 'do-not-inherit',
                                    'HTTPS_PROXY': 'http://proxy.invalid'}), \
             patch.object(safe_rss_process, '_child_command', return_value=command(script)):
            result = safe_rss.fetch(SOURCE)
        self.assertEqual(result.items[0].body, 'Exact source text')
        self.assertEqual(result.items[0].fetched_at.isoformat(), '2026-11-06T12:00:00+00:00')
        self.assertEqual(result.etag, '"fresh"')

    def test_child_only_receives_allowlisted_source_fields(self):
        script = (
            "import json,sys; request=json.loads(sys.stdin.buffer.read()); "
            "assert 'secret' not in request; "
            "assert 'secret' not in request.get('cache', {}); "
            f"print({json.dumps(json.dumps(RESULT))})"
        )
        source = {**SOURCE, 'secret': 'private', 'cache': {'url': SOURCE['url'], 'secret': 'private'}}
        with patch.object(safe_rss_process, '_child_command', return_value=command(script)):
            self.assertEqual(safe_rss.fetch(source).items[0].title, 'Real source title')

    def test_child_is_killed_and_reaped_at_deadline(self):
        processes = []
        slots = threading.BoundedSemaphore(1)
        real = subprocess.Popen
        def launch(*args, **kwargs):
            child = real(*args, **kwargs)
            processes.append(child)
            return child
        with patch.object(safe_rss_process, '_PROCESS_SLOTS', slots), \
             patch.object(safe_rss_process, 'TOTAL_TIMEOUT', 0.4), \
             patch.object(safe_rss_process, '_child_command', return_value=command('while True: pass')), \
             patch.object(safe_rss_process.subprocess, 'Popen', side_effect=launch):
            started = time.monotonic()
            with self.assertRaises(safe_rss.FetchError):
                safe_rss.fetch(SOURCE)
            self.assertLess(time.monotonic() - started, 2.0)
            # Popen itself can complete after the deadline on a loaded Windows
            # host. Slot release proves the late child has been killed/reaped.
            self.assertTrue(slots.acquire(timeout=10), 'Child cleanup did not finish')
            slots.release()
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_child_output_is_bounded_and_child_is_killed(self):
        processes = []
        real = subprocess.Popen
        def launch(*args, **kwargs):
            child = real(*args, **kwargs)
            processes.append(child)
            return child
        script = "import sys,time; sys.stdout.buffer.write(b'x'*1000000); sys.stdout.flush(); time.sleep(5)"
        with patch.object(safe_rss_process, 'MAX_OUTPUT_BYTES', 4096), \
             patch.object(safe_rss_process, '_child_command', return_value=command(script)), \
             patch.object(safe_rss_process.subprocess, 'Popen', side_effect=launch):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss.fetch(SOURCE)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_busy_process_slot_times_out_before_launch(self):
        slots = threading.BoundedSemaphore(1)
        slots.acquire()
        try:
            with patch.object(safe_rss_process, '_PROCESS_SLOTS', slots), \
                 patch.object(safe_rss_process, 'TOTAL_TIMEOUT', 0.05), \
                 patch.object(safe_rss_process.subprocess, 'Popen') as start:
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss.fetch(SOURCE)
                start.assert_not_called()
        finally:
            slots.release()

    def test_slow_process_creation_is_bounded_and_late_child_is_terminated(self):
        slots = threading.BoundedSemaphore(1)
        gate = threading.Event()
        killed = threading.Event()
        class LateProcess:
            def kill(self):
                killed.set()
            def wait(self, timeout=None):
                return -1
        def slow_launch(*args, **kwargs):
            gate.wait(1)
            return LateProcess()
        try:
            with patch.object(safe_rss_process, '_PROCESS_SLOTS', slots), \
                 patch.object(safe_rss_process, 'TOTAL_TIMEOUT', 0.05), \
                 patch.object(safe_rss_process.subprocess, 'Popen', side_effect=slow_launch):
                started = time.monotonic()
                with self.assertRaises(safe_rss.FetchError):
                    safe_rss.fetch(SOURCE)
                self.assertLess(time.monotonic() - started, 0.4)
                self.assertFalse(slots.acquire(blocking=False))
                gate.set()
                self.assertTrue(killed.wait(1))
                self.assertTrue(slots.acquire(timeout=1))
                slots.release()
        finally:
            gate.set()

    def test_untrusted_child_output_and_large_input_fail_closed(self):
        with patch.object(safe_rss_process, '_child_command', return_value=command("print('not json')")):
            with self.assertRaises(safe_rss.FetchError):
                safe_rss.fetch(SOURCE)
        with patch.object(safe_rss_process.subprocess, 'Popen') as start:
            with self.assertRaises(safe_rss.FetchError):
                safe_rss.fetch({**SOURCE, 'url': 'https://feed.example/' + 'x' * 20000})
            start.assert_not_called()
