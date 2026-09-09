"""Vercel python function entry: cold-start seed + demo middleware.

Vercel python runtime imports `app` (ASGI) from this module.
"""

import os

os.environ.setdefault("CONTENT_MACHINE_HOME", "/tmp/cm")
os.environ.setdefault("DEMO_MODE", "1")

from content_machine.api.app import app  # noqa: E402
from content_machine.api.rate_limit import RateLimitMiddleware  # noqa: E402


def _cold_start() -> None:
    from content_machine.demo_seed import seed_demo
    from content_machine.storage import db, paths

    paths.ensure_tree()
    conn = db.connect()
    try:
        seed_demo(conn)
    finally:
        conn.close()


_cold_start()
app.add_middleware(RateLimitMiddleware, limit_per_min=10)
