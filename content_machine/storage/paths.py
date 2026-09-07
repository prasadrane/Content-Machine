"""Runtime directory tree under ~/.content_machine (plan v2 §1).

CONTENT_MACHINE_HOME overrides the root (used by tests).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_DIR = REPO_ROOT / "knowledge"
SUBDIRS = ("knowledge", "archive", "projects")


def home_root() -> Path:
    env = os.environ.get("CONTENT_MACHINE_HOME")
    return Path(env) if env else Path.home() / ".content_machine"


def ensure_tree(copy_seeds: bool = True) -> dict[str, Path]:
    root = home_root()
    root.mkdir(parents=True, exist_ok=True)
    dirs = {"root": root}
    for name in SUBDIRS:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        dirs[name] = d
    if copy_seeds and SEED_DIR.is_dir():
        for seed in sorted(SEED_DIR.glob("*.md")):
            dest = dirs["knowledge"] / seed.name
            if not dest.exists():
                shutil.copyfile(seed, dest)
    return dirs


def project_dir(slug: str, create: bool = True) -> Path:
    """projects/{slug}/ with iterations/ and distribution/ subdirs."""
    if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        raise ValueError(f"unsafe project slug: {slug!r}")
    d = home_root() / "projects" / slug
    if create:
        (d / "iterations").mkdir(parents=True, exist_ok=True)
        (d / "distribution").mkdir(parents=True, exist_ok=True)
    return d
