"""Wiring for workflow AI, with request-time configuration.

CONTENT_MACHINE_WORKFLOW_AI: '0' = off; '1' = legacy configured router (relay);
'auto' = free-provider router (Cloudflare/Gemini, whichever has credentials);
unset/blank = 'auto' on a hosted deployment, otherwise off.
Injected providers take precedence, including an explicit None disablement.
No router or credential is retained across requests or creator identities.
"""
import os

from content_machine.bootstrap import make_router
from content_machine.config import load_config
from content_machine.council.loop import DEFAULT_RUBRIC
from content_machine.router.free_providers import build_free_router, free_ai_available
from content_machine.workflow.access import _hosted_deployment
from content_machine.workflow.reviews import review_snapshot, validate_review_advice
from content_machine.workflow.writing_adapters import cleanup_wording, generate_proposal, suggest_wording


def ai_mode():
    """Return 'off', 'legacy' or 'auto'."""
    raw = os.environ.get('CONTENT_MACHINE_WORKFLOW_AI')
    value = (raw or '').strip().lower()
    if value == '1':
        return 'legacy'
    if value == 'auto':
        return 'auto'
    if value == '':
        return 'auto' if _hosted_deployment() else 'off'
    return 'off'


def get_provider(app, kind):
    if kind not in ('generate', 'review'):
        raise ValueError('Unknown workflow provider kind')
    attribute = 'workflow_generator' if kind == 'generate' else 'workflow_reviewer'
    if hasattr(app.state, attribute):
        provider = getattr(app.state, attribute)
        return provider if callable(provider) else None
    mode = ai_mode()
    if mode == 'off' or (mode == 'auto' and not free_ai_available()):
        return None
    return generate if kind == 'generate' else review


def _router_and_config():
    if ai_mode() == 'auto':
        return build_free_router()  # never falls back to the legacy relay router
    cfg = load_config()
    return make_router(cfg), cfg


def generate(snapshot, *, execution=None):
    router, cfg = _router_and_config()
    if execution is not None:
        router = execution.wrap_router(router)
    return generate_proposal(snapshot, router, [cfg.models.writer])


def review(snapshot, *, execution=None):
    router, cfg = _router_and_config()
    if execution is not None:
        router = execution.wrap_router(router)
    advice = review_snapshot(snapshot, router, cfg, DEFAULT_RUBRIC.read_text(encoding='utf-8'))
    try:
        advice['proposals'] = suggest_wording(snapshot, router, [cfg.models.writer])
    except Exception:
        try:
            advice['proposals'] = cleanup_wording(snapshot)
        except Exception:
            advice['proposals'] = []
        advice['actions']['notes'].append(
            'Local cleanup suggested because model wording assistance was unavailable. Review before saving.'
            if advice['proposals'] else 'Wording suggestion unavailable. Your Council advice is preserved.')
    return validate_review_advice(advice, snapshot)
