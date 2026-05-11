"""Central path and mode configuration for the StuRec Agent layer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ResourceConfig:
    """Resolved filesystem resources for one pipeline mode (demo or graph)."""

    mode: str
    skill2_graph: Path | None
    skill2_students: Path
    skill2_mentors: Path
    skill1_profiles: Path | None
    mock_graph: Path | None
    default_student_id: str | None = None


def resolve_repo_root(repo_root: str | Path | None = None) -> Path:
    """Repository root (directory containing ``skill1_handoff/``)."""
    if repo_root is not None:
        root = Path(repo_root).resolve()
        if not (root / "skill1_handoff").is_dir():
            raise FileNotFoundError(f"Not a StuRec repo root (missing skill1_handoff/): {root}")
        return root
    here = Path(__file__).resolve().parent
    for anc in [here.parent, *here.parents]:
        if (anc / "skill1_handoff").is_dir():
            return anc
    raise FileNotFoundError("Could not locate repository root (no ancestor with skill1_handoff/).")


def _first_student_id(students_path: Path) -> str | None:
    if not students_path.is_file():
        return None
    try:
        data = json.loads(students_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    rows = data.get("students") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        return None
    sid = rows[0].get("student_id") if isinstance(rows[0], dict) else None
    return str(sid).strip() if sid else None


def _validate_graph_bundle_strict(graph_path: Path) -> None:
    """Graph mode only: fail fast with a clear message (no silent demo fallback)."""
    if not graph_path.is_file():
        raise FileNotFoundError(
            f"Graph mode requires academic_graph.json at {graph_path}. "
            "Build it with skill2_handoff/regenerate_kit/scripts/generate_mentor_pool.py "
            "then scripts/build_graph.py (see skill2_handoff/SKILL2_README.md)."
        )
    try:
        raw: dict[str, Any] = json.loads(graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Graph mode: invalid JSON in {graph_path}: {exc}") from exc
    nodes = raw.get("nodes")
    if not isinstance(nodes, dict):
        raise ValueError(f"Graph mode: {graph_path} missing dict 'nodes'.")
    projects = nodes.get("project")
    if not isinstance(projects, list) or len(projects) == 0:
        raise ValueError(
            f"Graph mode: {graph_path} has no nodes.project entries (got {type(projects).__name__!r})."
        )
    edges = raw.get("edges")
    if not isinstance(edges, list):
        raise ValueError(f"Graph mode: {graph_path} missing list 'edges'.")
    n_leads = 0
    for e in edges:
        if not isinstance(e, dict):
            continue
        et = str(e.get("type") or e.get("edge_type") or "")
        if et == "project_leads":
            n_leads += 1
    if n_leads == 0:
        raise ValueError(
            f"Graph mode: {graph_path} has zero edges with type 'project_leads' "
            "(Skill 4 needs mentor–project links in the graph)."
        )


def resolve_resource_config(mode: str, repo_root: Path, *, validate_graph: bool = True) -> ResourceConfig:
    """
    Resolve default paths for ``demo`` or ``graph`` mode.

    * **demo** — outputs student/mentor bundles + Skill 4 mock graph + Skill 1 JSONL.
    * **graph** — regenerate ``data/processed`` bundle + Skill 1 JSONL; validates graph when ``validate_graph`` is True.
    """
    mode_l = (mode or "").strip().lower()
    if mode_l not in ("demo", "graph"):
        raise ValueError(f"Unknown mode {mode!r}; expected 'demo' or 'graph'.")

    skill1 = repo_root / "skill1_handoff" / "student_profiles_normalized.jsonl"

    if mode_l == "demo":
        students = repo_root / "skill2_handoff" / "outputs" / "student_profiles_standard.json"
        mentors = repo_root / "skill2_handoff" / "outputs" / "mentor_profiles_standard.json"
        mock = repo_root / "skill4_handoff" / "data" / "mock_academic_graph.json"
        if not students.is_file():
            raise FileNotFoundError(f"Demo mode: missing student bundle: {students}")
        if not mentors.is_file():
            raise FileNotFoundError(f"Demo mode: missing mentor bundle: {mentors}")
        if not mock.is_file():
            raise FileNotFoundError(f"Demo mode: missing mock academic graph: {mock}")
        default_sid = _first_student_id(students)
        return ResourceConfig(
            mode="demo",
            skill2_graph=mock,
            skill2_students=students,
            skill2_mentors=mentors,
            skill1_profiles=skill1 if skill1.is_file() else None,
            mock_graph=mock,
            default_student_id=default_sid,
        )

    # graph mode
    graph = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "academic_graph.json"
    students = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "student_profiles_standard.json"
    mentors = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "mentor_profiles_standard.json"
    if not students.is_file():
        raise FileNotFoundError(f"Graph mode: missing student bundle: {students}")
    if not mentors.is_file():
        raise FileNotFoundError(f"Graph mode: missing mentor bundle: {mentors}")
    if validate_graph:
        _validate_graph_bundle_strict(graph)
    default_sid = _first_student_id(students)
    return ResourceConfig(
        mode="graph",
        skill2_graph=graph,
        skill2_students=students,
        skill2_mentors=mentors,
        skill1_profiles=skill1 if skill1.is_file() else None,
        mock_graph=None,
        default_student_id=default_sid,
    )
