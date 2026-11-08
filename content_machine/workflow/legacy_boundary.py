"""Keep unscoped legacy APIs out of hosted creator workspaces."""
import os

from starlette.responses import JSONResponse
from starlette.routing import Match


class LegacyBoundaryMiddleware:
    """Reject legacy API paths before executing their route or dependencies."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            path = scope.get('path', '')
            hosted = 'VERCEL' in os.environ or os.environ.get(
                'CONTENT_MACHINE_DEPLOYMENT_MODE', ''
            ).strip().lower() == 'hosted'
            api = path == '/api' or path.startswith('/api/')
            workflow = path == '/api/workflow' or path.startswith('/api/workflow/')
            public = path in {'/api/health', '/api/meta'} and scope.get('method') in {'GET', 'HEAD'}
            if hosted and api and not workflow and not public:
                # Match registrations, not the SPA catch-all. Method mismatches
                # still identify a private legacy route and must fail before
                # body parsing, dependencies, storage or provider invocation.
                registered = any(
                    route.path.startswith('/api/')
                    and route.matches(scope)[0] != Match.NONE
                    for route in getattr(scope.get('app'), 'routes', ())
                )
                response = JSONResponse(
                    status_code=410 if registered else 404,
                    content={'code': 'legacy_unavailable',
                             'detail': 'This legacy feature is unavailable in hosted workspaces.'}
                    if registered else {'detail': 'Not Found'},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
