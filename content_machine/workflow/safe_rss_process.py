"""Bound an opt-in RSS fetch inside a separate, credential-free process."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import requests

from content_machine.connectors.base import ConnectorItem
from content_machine.workflow.safe_rss import FetchError, RSSFetchResult

TOTAL_TIMEOUT = 20.0
MAX_INPUT_BYTES = 8192
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
_PROCESS_SLOTS = threading.BoundedSemaphore(4)


def _child_command():
    root = str(Path(__file__).resolve().parents[2])
    dependencies = str(Path(requests.__file__).resolve().parent.parent)
    code = ("import sys;sys.path.insert(0,sys.argv[2]);sys.path.insert(0,sys.argv[1]);"
            "from content_machine.workflow.safe_rss_process import child_main;child_main()")
    return [sys.executable, '-I', '-c', code, root, dependencies]


def _environment():
    # The child needs only OS loader and temporary-directory paths. It receives
    # no credentials, proxy variables, user profile, or Python configuration.
    allow = ('SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP')
    return {name: os.environ[name] for name in allow if name in os.environ}


def _request(source):
    if not isinstance(source, dict):
        raise FetchError('Invalid feed source')
    request = {key: source.get(key) for key in ('source_id', 'name', 'kind', 'url')}
    if not all(isinstance(value, str) and value for value in request.values()):
        raise FetchError('Invalid feed source')
    cache = source.get('cache')
    if isinstance(cache, dict):
        request['cache'] = {key: cache.get(key) for key in ('url', 'etag', 'last_modified')}
    try:
        encoded = json.dumps(request, ensure_ascii=True).encode('ascii')
    except (TypeError, ValueError) as exc:
        raise FetchError('Invalid feed source') from exc
    if len(encoded) > MAX_INPUT_BYTES:
        raise FetchError('Feed request exceeds the size limit')
    return encoded


def _remaining(deadline):
    return max(0.0, deadline - time.monotonic())


def _terminate(child):
    try:
        child.kill()
    except (OSError, ProcessLookupError):
        pass


def _run(payload, deadline, slots):
    """Keep the slot until any late-launched process is terminated and reaped."""
    done = threading.Event()
    cancelled = threading.Event()
    lock = threading.Lock()
    state = {'child': None, 'output': None, 'error': None}

    def worker():
        child = None
        try:
            child = subprocess.Popen(
                _child_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=_environment(), close_fds=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            with lock:
                state['child'] = child
                if cancelled.is_set():
                    _terminate(child)
            if cancelled.is_set():
                child.wait()
                return

            chunks = []
            overflow = threading.Event()
            def read_output():
                size = 0
                while True:
                    chunk = child.stdout.read(min(65536, MAX_OUTPUT_BYTES + 1 - size))
                    if not chunk:
                        return
                    size += len(chunk)
                    if size > MAX_OUTPUT_BYTES:
                        overflow.set()
                        _terminate(child)
                        return
                    chunks.append(chunk)

            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()
            child.stdin.write(payload)
            child.stdin.close()
            child.wait()
            reader.join()
            if overflow.is_set() or child.returncode != 0:
                raise FetchError('Feed process failed')
            state['output'] = _decode(b''.join(chunks))
        except Exception as exc:
            state['error'] = exc
            if child is not None:
                _terminate(child)
                try:
                    child.wait()
                except OSError:
                    pass
        finally:
            if child is not None:
                for pipe in (getattr(child, 'stdin', None), getattr(child, 'stdout', None)):
                    if pipe is not None:
                        try:
                            pipe.close()
                        except OSError:
                            pass
            slots.release()
            done.set()

    try:
        threading.Thread(target=worker, daemon=True).start()
    except Exception:
        slots.release()
        raise FetchError('Feed process could not start') from None
    if not done.wait(_remaining(deadline)):
        cancelled.set()
        with lock:
            if state['child'] is not None:
                _terminate(state['child'])
                launched = True
            else:
                launched = False
        # Reaping normally completes immediately. A stuck OS call retains its
        # concurrency slot until the worker actually finishes cleanup.
        if launched:
            done.wait(0.2)
        raise FetchError('Feed request timed out')
    if state['error'] is not None or state['output'] is None:
        raise FetchError('Feed process failed')
    return state['output']


def _decode(output):
    try:
        response = json.loads(output)
        if response.get('ok') is not True or not isinstance(response.get('result'), dict):
            raise ValueError('invalid response')
        result = response['result']
        if len(result['items']) > 25:
            raise ValueError('too many items')
        entries = []
        for entry in result['items']:
            entries.append(ConnectorItem(
                title=entry['title'], url=entry['url'], body=entry['body'],
                source=entry['source'], guid=entry['guid'],
                fetched_at=datetime.fromisoformat(entry['fetched_at']),
                published_at=datetime.fromisoformat(entry['published_at']) if entry['published_at'] else None,
            ))
        return RSSFetchResult(
            source=result['source'], items=entries, not_modified=result['not_modified'],
            etag=result['etag'], last_modified=result['last_modified'], cache_url=result['cache_url'],
        )
    except (ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise FetchError('Invalid feed process response') from exc


def fetch(source):
    deadline = time.monotonic() + TOTAL_TIMEOUT
    payload = _request(source)
    slots = _PROCESS_SLOTS
    if not slots.acquire(timeout=_remaining(deadline)):
        raise FetchError('Feed request timed out')
    return _run(payload, deadline, slots)


def child_main():
    """Read a bounded request and emit one JSON result with no sensitive errors."""
    try:
        request = json.loads(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        from content_machine.workflow.safe_rss import _fetch_in_process
        result = asdict(_fetch_in_process(request))
        for item in result['items']:
            for key in ('fetched_at', 'published_at'):
                if item[key] is not None:
                    item[key] = item[key].isoformat()
        output = json.dumps({'ok': True, 'result': result}, ensure_ascii=True).encode('ascii')
        if len(output) > MAX_OUTPUT_BYTES:
            raise FetchError('Feed result exceeds the size limit')
        sys.stdout.buffer.write(output)
    except Exception:
        sys.stdout.buffer.write(b'{"ok":false}')
    sys.stdout.buffer.flush()
