"""Doc-drift guard: pin documentation claims to code/config truth.

Session audit (2026-09-09) found 5 doc-vs-code conflicts that were fixed by
hand. These tests make any recurrence a test failure instead of a silent
regression. All checks are offline: stdlib + repo imports only.

Check 6 (content_machine/editorial/rules.py) is expected-RED until task-1
lands that module; it is read as TEXT (regex) on purpose so this file never
imports a half-merged package.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from content_machine.lessons.store import DEFAULT_CAP  # noqa: E402

# ---------------------------------------------------------------- fixtures --

AGENTS_MD = ROOT / "AGENTS.md"
README_MD = ROOT / "README.md"
CONFIG_JSON = ROOT / "config.json"
REQUIREMENTS_TXT = ROOT / "requirements.txt"
EDITORIAL_RULES = ROOT / "content_machine" / "editorial" / "rules.py"

KNOWLEDGE_DOCS = [
    ROOT / "knowledge" / "01_style-guide.md",
    ROOT / "knowledge" / "02_voice-guide.md",
    ROOT / "knowledge" / "03_content-lessons.md",
]

# Files that must never resurrect the stale "120-250" word-count range.
RANGE_SCAN_FILES = KNOWLEDGE_DOCS + [
    ROOT / "content_machine" / "interview" / "engine.py",
    ROOT / "content_machine" / "council" / "loop.py",
    ROOT / "content_machine" / "distribution" / "engine.py",
    ROOT / "content_machine" / "humanize" / "constants.py",
]

FORBIDDEN_RANGE_PATTERNS = ["120-250", "120–250", "120 and 250"]

# README display name -> config.json models.council key
COUNCIL_JUDGE_KEYS = {
    "David Perell": "perell",
    "Sahil Puri": "puri",
    "Morgan Housel": "housel",
    "Slop Allergist": "slop_allergist",
}


# ------------------------------------------------------------------ readers --

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _load_config() -> dict:
    return json.loads(_read(CONFIG_JSON))


# ------------------------------------------------------------ parse helpers --
# Pure functions over text so failure logic can be proven against inline
# mutated fixtures (see "failure-logic" tests) without touching disk.

def parse_rule_cap(text: str):
    """Extract N from AGENTS.md 'Hard cap of active rules (default: N)'."""
    m = re.search(r"Hard cap of active rules \(default:\s*(\d+)", text)
    return int(m.group(1)) if m else None


def parse_judge_model(text: str, display_name: str):
    """Extract backticked model id from a README '**<name>** (`model`)' line."""
    m = re.search(
        r"\*\*" + re.escape(display_name) + r"\*\*\s*\(`([^`]+)`\)", text
    )
    return m.group(1) if m else None


def agents_allowlist_text(text: str) -> str:
    """Slice of AGENTS.md listing allowed (routable) models only — excludes
    the 'Do NOT route to' blacklist so a blacklisted id cannot pass check 3."""
    m = re.search(
        r"Allowed Models(.*?)Do NOT route to", text, re.DOTALL
    )
    return m.group(1) if m else text


def forbidden_range_hits(text: str):
    """Which stale word-range spellings occur in text."""
    return [pat for pat in FORBIDDEN_RANGE_PATTERNS if pat in text]


def openai_pins(text: str):
    """Non-comment requirements lines pinning openai==."""
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("openai==")
    ]


def parse_word_const(text: str, name: str):
    """Extract int value of WORD_COUNT_MIN / WORD_COUNT_MAX from source text."""
    m = re.search(rf"^{name}\s*=\s*(\d+)", text, re.MULTILINE)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------ checks --

def test_check1_agents_hard_cap_matches_default_cap():
    """AGENTS.md 'Hard cap of active rules (default: N)' == store.DEFAULT_CAP."""
    cap = parse_rule_cap(_read(AGENTS_MD))
    assert cap is not None, (
        f"AGENTS.md: claim 'Hard cap of active rules (default: N)' not found; "
        f"expected it to equal DEFAULT_CAP={DEFAULT_CAP}"
    )
    assert cap == DEFAULT_CAP, (
        f"AGENTS.md says active-rules cap is {cap}, but "
        f"content_machine.lessons.store.DEFAULT_CAP == {DEFAULT_CAP} "
        f"(expected: {DEFAULT_CAP})"
    )


def test_check2_readme_council_judges_match_config():
    """README judge lines (backticked model ids) == config.json models.council."""
    council = _load_config()["models"]["council"]
    readme = _read(README_MD)
    for display_name, key in COUNCIL_JUDGE_KEYS.items():
        assert key in council, (
            f"config.json models.council missing key {key!r} "
            f"(required for README judge '{display_name}')"
        )
        actual = parse_judge_model(readme, display_name)
        expected = council[key]
        assert actual is not None, (
            f"README.md: no '**{display_name}** (`model`)' line found; "
            f"expected model {expected!r} per config.json"
        )
        assert actual == expected, (
            f"README.md judge '{display_name}' says {actual!r}, but "
            f"config.json models.council.{key} == {expected!r} "
            f"(expected: {expected!r})"
        )


def test_check3_council_models_in_agents_allowlist():
    """Every config.json models.council model id appears in AGENTS.md allowlist."""
    council = _load_config()["models"]["council"]
    allowlist = agents_allowlist_text(_read(AGENTS_MD))
    for key, model_id in sorted(council.items()):
        assert model_id in allowlist, (
            f"config.json models.council.{key} == {model_id!r} does not "
            f"appear in the AGENTS.md allowed-models list "
            f"(expected: every council model id is allowlisted)"
        )


def test_check4_word_limit_280_pinned_and_no_stale_range():
    """Knowledge docs pin '280'; no doc/code file resurrects '120-250'."""
    for doc in KNOWLEDGE_DOCS:
        text = _read(doc)
        assert "280" in text, (
            f"{doc.relative_to(ROOT)}: expected the word-limit truth '280' "
            f"(the fixed upper bound) to appear, it does not"
        )
    for path in RANGE_SCAN_FILES:
        assert path.exists(), (
            f"{path.relative_to(ROOT)}: expected file to exist for the "
            f"stale-range scan"
        )
        hits = forbidden_range_hits(_read(path))
        assert hits == [], (
            f"{path.relative_to(ROOT)}: contains stale word-range "
            f"{hits}; expected none of {FORBIDDEN_RANGE_PATTERNS} "
            f"(truth is 120-280)"
        )


def test_check5_requirements_has_no_openai_pin():
    """requirements.txt must not pin openai (gateway has no OpenAI protocol)."""
    pins = openai_pins(_read(REQUIREMENTS_TXT))
    assert pins == [], (
        f"requirements.txt: found openai== pin(s) {pins}; expected none "
        f"(relay is Anthropic-Messages-protocol only)"
    )


def test_check6_editorial_rules_word_bounds():
    """content_machine/editorial/rules.py defines WORD_COUNT_MIN=120 / MAX=280.

    Read as TEXT, not import (task-1 lands this module concurrently).
    EXPECTED-RED until task-1 merges — a loud failure while the file is
    absent is the intended integration signal.
    """
    assert EDITORIAL_RULES.exists(), (
        f"content_machine/editorial/rules.py: expected file defining "
        f"WORD_COUNT_MIN=120 and WORD_COUNT_MAX=280 (task-1); not found yet"
    )
    text = _read(EDITORIAL_RULES)
    lo = parse_word_const(text, "WORD_COUNT_MIN")
    hi = parse_word_const(text, "WORD_COUNT_MAX")
    assert lo == 120, (
        f"content_machine/editorial/rules.py: WORD_COUNT_MIN is {lo!r}, "
        f"expected 120"
    )
    assert hi == 280, (
        f"content_machine/editorial/rules.py: WORD_COUNT_MAX is {hi!r}, "
        f"expected 280"
    )


# ------------------------------------------------- failure-logic (red) proof --
# Each guard must fail for the right reason when the truth is violated.
# Proven with inline mutated fixtures — nothing on disk is changed.

def test_failure_logic_cap_drift_detected():
    assert parse_rule_cap("- Hard cap of active rules (default: 120, x)") == 120
    assert parse_rule_cap("- Hard cap of active rules (default: 120)") != DEFAULT_CAP
    assert parse_rule_cap("no claim here") is None  # missing claim -> check1 fails


def test_failure_logic_judge_model_drift_detected():
    bad = "  - **David Perell** (`gpt-4o`): Narrative arc.\n"
    assert parse_judge_model(bad, "David Perell") == "gpt-4o"
    assert parse_judge_model(bad, "David Perell") != "qwen3.8-max"
    assert parse_judge_model("nothing", "Sahil Puri") is None


def test_failure_logic_allowlist_excludes_blacklist():
    doc = (
        "- Allowed Models:\n  - Writer: `qwen3.8-max`\n"
        "  - *Do NOT route to*: `qwen3.6-plus`, `qwen3.6-flash`.\n"
    )
    sliced = agents_allowlist_text(doc)
    assert "qwen3.8-max" in sliced
    assert "qwen3.6-flash" not in sliced  # blacklisted id cannot pass check3


def test_failure_logic_stale_range_detected():
    for spelling in FORBIDDEN_RANGE_PATTERNS:
        assert forbidden_range_hits(f"keep it {spelling} words") == [spelling]
    assert forbidden_range_hits("keep it 120-280 words") == []


def test_failure_logic_openai_pin_detected():
    text = "# comment: openai pin dropped\nopenai==1.40.0\nfastapi==0.115.0\n"
    assert openai_pins(text) == ["openai==1.40.0"]
    assert openai_pins("# openai== mention in comment only\nfastapi==0.1.0\n") == []


def test_failure_logic_word_const_parse():
    text = "WORD_COUNT_MIN = 120\nWORD_COUNT_MAX = 280\n"
    assert parse_word_const(text, "WORD_COUNT_MIN") == 120
    assert parse_word_const(text, "WORD_COUNT_MAX") == 280
    assert parse_word_const("WORD_COUNT_MAX = 250", "WORD_COUNT_MAX") == 250
    assert parse_word_const("absent", "WORD_COUNT_MIN") is None
