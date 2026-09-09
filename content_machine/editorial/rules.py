"""Single source of truth for the editorial constraints shared by every
generation prompt (interview synthesis, council revision, distribution,
humanize).

These rules were previously copy-pasted into each prompt individually, which
let them drift (120-250 vs 120-280 word-count incident). Prompts must import
from this module instead of restating the constraints. Pure constants,
stdlib-free, ASCII-only for Windows safety.
"""

# Plain (unannotated) assignments for the two bounds: tests/test_doc_drift.py
# parses this file as text with `^WORD_COUNT_(MIN|MAX)\s*=\s*(\d+)`.
WORD_COUNT_MIN = 120  # int
WORD_COUNT_MAX = 280  # int

WORD_COUNT_RULE = (  # str
    f"Strictly between {WORD_COUNT_MIN} and {WORD_COUNT_MAX} words total. "
    "Never write long essays or walls of text."
)

VOICE_RULE: str = (
    "Conversational practitioner voice: write in first person from direct "
    "experience (\"I've started treating...\", \"What works better for me:\"). "
    "Keep it slightly messier and practical rather than an immaculate, "
    "sanitized lecture."
)

ANTI_FINGERPRINT_RULES: str = "\n".join(
    [
        "- Aphorism density cap: limit to at most ONE takeaway or summary "
        "line; NEVER string consecutive quotable epigrams or soundbites "
        "together.",
        "- Ban rhetorical contrast formulas: do NOT use \"X feels fast until "
        "Y...\", \"You aren't saving X, you're just Y...\", or \"The problem "
        "isn't X, it's how we Y...\". State observations directly.",
        "- Ban manufactured metaphors and drama: NEVER use dramatic phrases "
        "like \"the workflow that stops the bleeding\" or \"pure velocity\".",
        "- Natural paragraph grouping (NO broetry): group related premise, "
        "mechanics, and friction into cohesive mini-paragraphs (2-3 "
        "sentences). Avoid 1-sentence staccato lines unless presenting an "
        "operational action list.",
        "- Zero engagement bait or formulaic closers: do NOT use the \"X "
        "isn't Y, it's Z\" fortune-cookie mic-drop template. NEVER end with "
        "cheesy questions (\"What do you think?\", \"Agree?\", \"Comment "
        "below\"). Close on an unvarnished statement of technical reality.",
    ]
)

RULES_BLOCK: str = "\n".join(
    [
        "SHARED EDITORIAL RULES (single source of truth, content_machine.editorial):",
        f"- Length: {WORD_COUNT_RULE}",
        f"- Voice: {VOICE_RULE}",
        "- Anti-fingerprint:",
        ANTI_FINGERPRINT_RULES,
    ]
)
