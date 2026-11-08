"""Explicit opt-in wiring for workflow AI, with request-time configuration.

Injected providers take precedence, including an explicit None disablement.
No router or credential is retained across requests or creator identities.
"""
import os

from content_machine.bootstrap import make_router
from content_machine.config import load_config
from content_machine.council.loop import DEFAULT_RUBRIC
from content_machine.workflow.reviews import review_snapshot, validate_review_advice
from content_machine.workflow.writing_adapters import cleanup_wording, generate_proposal, suggest_wording


def get_provider(app, kind):
    if kind not in ('generate', 'review'):
        raise ValueError('Unknown workflow provider kind')
    attribute = 'workflow_generator' if kind == 'generate' else 'workflow_reviewer'
    if hasattr(app.state, attribute):
        provider = getattr(app.state, attribute)
        return provider if callable(provider) else None
    if os.environ.get('CONTENT_MACHINE_WORKFLOW_AI') != '1':
        return None
    return generate if kind == 'generate' else review


def generate(snapshot, *, execution=None):
    cfg = load_config()
    router = make_router(cfg)
    if execution is not None:
        router = execution.wrap_router(router)
    return generate_proposal(snapshot, router, [cfg.models.writer])


def review(snapshot, *, execution=None):
    cfg = load_config()
    router = make_router(cfg)
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
