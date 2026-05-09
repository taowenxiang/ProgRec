"""Resolve bundle root (folder containing ``scripts/`` + ``skills/``) vs course repo root."""

from __future__ import annotations

from pathlib import Path


def bundle_root_from_script(script_file: Path) -> Path:
    """Parent of ``scripts/`` (mini layout or full repo)."""
    return script_file.resolve().parents[1]


def course_repo_root(bundle_root: Path) -> Path:
    """Ancestor that contains ``skill1_handoff/`` (full team repo); else ``bundle_root``."""
    for anc in [bundle_root, *bundle_root.parents]:
        if (anc / "skill1_handoff").is_dir():
            return anc
    return bundle_root
