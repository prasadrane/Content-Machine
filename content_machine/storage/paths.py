"""Runtime directory tree under ~/.content_machine (plan v2 §1).

CONTENT_MACHINE_HOME overrides the root (used by tests).

Seed knowledge files (``knowledge/*.md`` in the repo) are authoritative:
``ensure_tree`` refreshes the runtime copies whenever their content differs
from the seeds, saving the outgoing copy as ``<name>.bak`` first. The runtime
markdown is a materialized copy — edit the repo seeds, never the runtime
files; governed rules themselves live in the SQLite lessons table (DB is the
source of truth once seeded).
"""

from __future__ import annotations

import hashlib
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
            sync_seed(seed, dirs["knowledge"] / seed.name)
    return dirs


def sync_seed(seed_file: Path, runtime_file: Path) -> None:
    """Copy ``seed_file`` over ``runtime_file`` when contents differ.

    The outgoing runtime copy is kept as ``<name>.bak``. The old size-half
    heuristic silently kept stale copies forever — a repo knowledge edit
    never reached the prompts that read the runtime copy.
    """
    if not seed_file.is_file():
        return
    if not runtime_file.is_file():
        runtime_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(seed_file, runtime_file)
    elif _sha256(seed_file) != _sha256(runtime_file):
        shutil.copyfile(runtime_file, runtime_file.with_name(runtime_file.name + ".bak"))
        shutil.copyfile(seed_file, runtime_file)


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def project_dir(slug: str, create: bool = True) -> Path:
    """projects/{slug}/ with iterations/ and distribution/ subdirs."""
    if not slug or "/" in slug or "\\" in slug or slug.startswith("."):
        raise ValueError(f"unsafe project slug: {slug!r}")
    d = home_root() / "projects" / slug
    if create:
        (d / "iterations").mkdir(parents=True, exist_ok=True)
        (d / "distribution").mkdir(parents=True, exist_ok=True)
    return d
