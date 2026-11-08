"""Vercel entry with an explicit hosted privacy boundary.

Vercel python runtime imports `app` (ASGI) from this module.
"""

import os

os.environ['CONTENT_MACHINE_DEPLOYMENT_MODE'] = 'hosted'

from content_machine.api.app import app  # noqa: E402
from content_machine.api.rate_limit import RateLimitMiddleware  # noqa: E402
from content_machine.workflow.hosted_bootstrap import configure_hosted_workflow  # noqa: E402

configure_hosted_workflow(app, os.environ)

app.add_middleware(RateLimitMiddleware, limit_per_min=10)
