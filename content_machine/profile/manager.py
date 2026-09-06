"""ProfileManager subsystem: manages local author voice guide and grounding profile."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Optional

from content_machine.schemas import ProfileData, UpdateProfileRequest
from content_machine.storage import paths

DEFAULT_NAME = "Prasad Rane"
DEFAULT_HEADLINE = "Senior Software & AI Systems Engineer"
DEFAULT_FOCUS = (
    "Relentless hands-on builder. Actively diving deep, building, and evaluating "
    "Agentic AI systems, local multi-model orchestration, and modern software architectures."
)
DEFAULT_TECHNICAL_DOMAINS = [
    ".NET Core",
    "AWS Bedrock / ECS / Lambda",
    "Apache Kafka",
    "DynamoDB / SQL Server",
    "Distributed Tracing",
    "Agentic AI",
]

DEFAULT_HARD_INVARIANTS = [
    "**Zero Company Attribution**: NEVER cite previous company names (no Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.). Frame all insights as pure personal thoughts and architectural observations (e.g., \"When designing high-throughput event pipelines...\", \"In my experience managing distributed lock contention...\").",
    "**No False Corporate Employment**: NEVER generate statements implying current employment at an organization (e.g., NEVER write \"My company today...\", \"My team at work...\", \"At my current job...\").",
    "**Job-Status Agnostic Technical Tone**: Do not bring up layoffs or job searches in technical posts or comments unless explicitly prompted. Speak with senior authority, craftsmanship, and pragmatic technical conviction.",
    "**Zero Fluff or Generic Praise**: Banned phrases: \"Spot on!\", \"Thanks for sharing\", \"Great post!\", \"In today's fast-paced world\", \"Crucial to remember\". Jump straight into the technical crux.",
    "**No Emoji Overload**: Maximum 0–1 functional emoji; no bullet-point emoji spam.",
]

INVARIANT_KEYWORDS = [
    "Zero Company Attribution",
    "No False Corporate Employment",
    "Job-Status Agnostic Technical Tone",
    "Zero Fluff or Generic Praise",
    "No Emoji Overload",
]

CANONICAL_NON_NEGOTIABLE_SECTION = """## 2. Voice Invariants & Negative Constraints (NON-NEGOTIABLE)
1. **Zero Company Attribution**: NEVER cite previous company names (no Rocket Mortgage, London Computer Systems, EXFO, Tanish Infotech, etc.). Frame all insights as pure personal thoughts and architectural observations (e.g., "When designing high-throughput event pipelines...", "In my experience managing distributed lock contention...").
2. **No False Corporate Employment**: NEVER generate statements implying current employment at an organization (e.g., NEVER write "My company today...", "My team at work...", "At my current job...").
3. **Job-Status Agnostic Technical Tone**: Do not bring up layoffs or job searches in technical posts or comments unless explicitly prompted. Speak with senior authority, craftsmanship, and pragmatic technical conviction.
4. **Zero Fluff or Generic Praise**: Banned phrases: "Spot on!", "Thanks for sharing", "Great post!", "In today's fast-paced world", "Crucial to remember". Jump straight into the technical crux.
5. **No Emoji Overload**: Maximum 0–1 functional emoji; no bullet-point emoji spam."""


class ProfileManager:
    """Manages author profile and voice grounding stored in knowledge/02_voice-guide.md."""

    def __init__(
        self,
        home_root: Optional[Path] = None,
        seed_path: Optional[Path] = None,
        dev_mode: bool = False,
    ) -> None:
        self.home_root = Path(home_root) if home_root is not None else paths.home_root()
        self.seed_path = (
            Path(seed_path) if seed_path is not None else (paths.SEED_DIR / "02_voice-guide.md")
        )
        self.dev_mode = dev_mode or os.environ.get("CONTENT_MACHINE_DEV") in ("1", "true", "True")
        self.runtime_path = self.home_root / "knowledge" / "02_voice-guide.md"
        self._ensure_runtime_file()

    def _ensure_runtime_file(self) -> None:
        """Ensure the runtime voice guide file exists, copying from seed if necessary."""
        self.runtime_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.runtime_path.exists():
            if self.seed_path.exists():
                shutil.copyfile(self.seed_path, self.runtime_path)
            else:
                self._write_default_voice_guide()

    def _write_default_voice_guide(self) -> None:
        default_content = (
            f"# Voice & Persona Guide — {DEFAULT_NAME}\n\n"
            f"## 1. Core Identity & Stance\n"
            f"- **Persona**: {DEFAULT_HEADLINE} — The Bridge between Enterprise Systems and Modern AI.\n"
            f"- **Background**: 10+ years architecting high-throughput distributed systems, "
            f"event-driven backends, and cloud migrations (.NET Core, AWS, Kafka, DynamoDB, SQL Server).\n"
            f"- **Current Operational Reality**: {DEFAULT_FOCUS}\n"
            f"- **Perspective**: Pragmatic first-principles technical practitioner.\n\n"
            f"{CANONICAL_NON_NEGOTIABLE_SECTION}\n\n"
            f"## 3. Communication Cadence & Tone\n"
            f"- **Cadence**: Crisp, punchy, direct. Short, declarative sentences with high information density.\n\n"
            f"## 4. Technical Grounding & Architectural Beliefs\n"
            f"- **Architecture**: Modular monoliths until scale demands event-driven decoupling.\n"
        )
        self._atomic_write(self.runtime_path, default_content)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
        try:
            temp_file.write_text(content, encoding="utf-8")
            temp_file.replace(path)
        except Exception:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            path.write_text(content, encoding="utf-8")

    def get_voice_guide_text(self) -> str:
        """Return the complete raw text of the active voice guide."""
        self._ensure_runtime_file()
        return self.runtime_path.read_text(encoding="utf-8")

    def get_profile(self) -> ProfileData:
        """Parse the active voice guide markdown into a structured ProfileData model."""
        content = self.get_voice_guide_text()

        # Parse name
        name_match = re.search(r"^#\s*Voice\s*&\s*Persona\s*Guide\s*[—–-]\s*(.+)$", content, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else DEFAULT_NAME

        # Parse headline
        headline = DEFAULT_HEADLINE
        persona_match = re.search(r"^-\s*\*\*Persona\*\*:\s*(.+)$", content, re.MULTILINE)
        if persona_match:
            raw_persona = persona_match.group(1).strip()
            # Split before em dash / hyphen description if present
            candidate = re.split(r"\s*[—–-]\s*", raw_persona)[0].strip()
            if candidate:
                headline = candidate

        # Parse current focus
        focus_match = re.search(r"^-\s*\*\*Current Operational Reality\*\*:\s*(.+)$", content, re.MULTILINE)
        current_focus = focus_match.group(1).strip() if focus_match else DEFAULT_FOCUS

        # Parse technical domains
        domains_match = re.search(r"^-\s*\*\*Technical Domains\*\*:\s*(.+)$", content, re.MULTILINE)
        if domains_match:
            technical_domains = [d.strip() for d in domains_match.group(1).split(",") if d.strip()]
        else:
            technical_domains = list(DEFAULT_TECHNICAL_DOMAINS)

        # Parse hard invariants from Section 2
        hard_invariants: list[str] = []
        sec2_match = re.search(
            r"##\s*2\.\s*Voice Invariants & Negative Constraints.*?\n(.*?)(?=\n##|\Z)",
            content,
            re.DOTALL,
        )
        if sec2_match:
            for line in sec2_match.group(1).splitlines():
                m = re.match(r"^\d+\.\s*(.+)$", line.strip())
                if m:
                    hard_invariants.append(m.group(1).strip())

        if not hard_invariants or len(hard_invariants) < 5:
            hard_invariants = list(DEFAULT_HARD_INVARIANTS)

        return ProfileData(
            name=name,
            headline=headline,
            current_focus=current_focus,
            technical_domains=technical_domains,
            hard_invariants=hard_invariants,
            full_markdown=content,
        )

    def update_profile(self, req: UpdateProfileRequest) -> ProfileData:
        """Update mutable fields in the voice guide while strictly preserving invariants."""
        content = self.get_voice_guide_text()

        # 1. Update current_focus
        if req.current_focus is not None:
            new_focus_line = f"- **Current Operational Reality**: {req.current_focus.strip()}"
            if re.search(r"^-\s*\*\*Current Operational Reality\*\*:\s*.*$", content, re.MULTILINE):
                content = re.sub(
                    r"^-\s*\*\*Current Operational Reality\*\*:\s*.*$",
                    new_focus_line,
                    content,
                    flags=re.MULTILINE,
                )
            elif re.search(r"^##\s*1\.\s*Core Identity & Stance", content, re.MULTILINE):
                content = re.sub(
                    r"(^##\s*1\.\s*Core Identity & Stance.*?\n)",
                    rf"\1{new_focus_line}\n",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content = f"{new_focus_line}\n" + content

        # 2. Update technical_domains
        if req.technical_domains is not None:
            domains_str = ", ".join(req.technical_domains)
            new_domains_line = f"- **Technical Domains**: {domains_str}"
            if re.search(r"^-\s*\*\*Technical Domains\*\*:\s*.*$", content, re.MULTILINE):
                content = re.sub(
                    r"^-\s*\*\*Technical Domains\*\*:\s*.*$",
                    new_domains_line,
                    content,
                    flags=re.MULTILINE,
                )
            elif re.search(r"^-\s*\*\*Background\*\*:\s*.*$", content, re.MULTILINE):
                content = re.sub(
                    r"(^-\s*\*\*Background\*\*:\s*.*$)",
                    rf"\1\n{new_domains_line}",
                    content,
                    flags=re.MULTILINE,
                )
            elif re.search(r"^-\s*\*\*Current Operational Reality\*\*:\s*.*$", content, re.MULTILINE):
                content = re.sub(
                    r"(^-\s*\*\*Current Operational Reality\*\*:\s*.*$)",
                    rf"{new_domains_line}\n\1",
                    content,
                    flags=re.MULTILINE,
                )
            else:
                content += f"\n{new_domains_line}\n"

        # 3. Update custom_notes
        if req.custom_notes is not None:
            notes_str = req.custom_notes.strip()
            notes_section = f"## 5. Custom Editorial Notes\n{notes_str}"
            if re.search(r"^##\s*(?:5\.\s*)?Custom Editorial Notes.*$", content, re.MULTILINE):
                content = re.sub(
                    r"##\s*(?:5\.\s*)?Custom Editorial Notes.*?(?=\n##|\Z)",
                    notes_section,
                    content,
                    flags=re.MULTILINE | re.DOTALL,
                )
            else:
                content = content.rstrip() + f"\n\n{notes_section}\n"

        # 4. Strict invariant check: NEVER mutate or strip the 5 hard invariants
        missing_invariants = [kw for kw in INVARIANT_KEYWORDS if kw not in content]
        if missing_invariants:
            # Re-inject the canonical non-negotiable invariants section
            if re.search(r"##\s*2\.\s*Voice Invariants & Negative Constraints.*?(?=\n##|\Z)", content, re.DOTALL):
                content = re.sub(
                    r"##\s*2\.\s*Voice Invariants & Negative Constraints.*?(?=\n##|\Z)",
                    CANONICAL_NON_NEGOTIABLE_SECTION,
                    content,
                    flags=re.DOTALL,
                )
            else:
                # Insert between section 1 and 3, or prepend
                sec3_match = re.search(r"(^##\s*3\.)", content, re.MULTILINE)
                if sec3_match:
                    content = re.sub(
                        r"(^##\s*3\.)",
                        rf"{CANONICAL_NON_NEGOTIABLE_SECTION}\n\n\1",
                        content,
                        flags=re.MULTILINE,
                    )
                else:
                    content += f"\n\n{CANONICAL_NON_NEGOTIABLE_SECTION}\n"

        # 5. Atomic persistence to runtime path (and seed mirror if dev_mode)
        self._atomic_write(self.runtime_path, content)
        if self.dev_mode and self.seed_path.exists():
            try:
                if self.seed_path.resolve() != self.runtime_path.resolve():
                    self._atomic_write(self.seed_path, content)
            except Exception:
                pass

        return self.get_profile()
