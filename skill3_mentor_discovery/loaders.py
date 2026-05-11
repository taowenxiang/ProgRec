from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any


@dataclass
class ResourcePaths:
    mentor_profiles_path: Path
    student_profiles_path: Path
    graph_candidates: tuple[Path, ...]
    needs_graph_rebuild: bool
    resource_mode: str  # "default" | "explicit"

    @property
    def outputs_graph_path(self) -> Path:
        """First graph candidate (legacy name: outputs academic_graph in default mode)."""
        return self.graph_candidates[0] if self.graph_candidates else self.mentor_profiles_path

    @property
    def graph_path(self) -> Path:
        """Last graph candidate (legacy name: regenerate processed graph in default mode)."""
        return self.graph_candidates[-1] if self.graph_candidates else self.mentor_profiles_path


@dataclass
class StandardizedResources:
    mentors: list[dict[str, Any]]
    students: list[dict[str, Any]]
    graph: dict[str, Any] | None
    paths: ResourcePaths
    graph_source_path: Path | None = None


def _load_first_valid_graph(processed_dir: Path) -> dict[str, Any] | None:
    candidates = sorted(processed_dir.glob("academic_graph*.json"))
    for candidate in candidates:
        try:
            return _load_json(candidate)
        except JSONDecodeError:
            continue
    return None


def resolve_resource_paths(
    repo_root: Path,
    skill2_graph: Path | None = None,
    skill2_students: Path | None = None,
    skill2_mentors: Path | None = None,
) -> ResourcePaths:
    """
    Resolve Skill 2 JSON paths for Skill 3.

    When ``skill2_students`` / ``skill2_mentors`` / ``skill2_graph`` are passed, those paths
    are required to exist (``FileNotFoundError`` if missing). Explicit graph mode does **not**
    fall back to ``outputs/`` when the given file is missing or invalid JSON.
    """
    outputs = repo_root / "skill2_handoff" / "outputs"
    default_mentor = outputs / "mentor_profiles_standard.json"
    default_student = outputs / "student_profiles_standard.json"
    default_outputs_graph = outputs / "academic_graph.json"
    default_regen_graph = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "academic_graph.json"

    mentor_path = Path(skill2_mentors).resolve() if skill2_mentors is not None else default_mentor
    student_path = Path(skill2_students).resolve() if skill2_students is not None else default_student

    if skill2_mentors is not None and not mentor_path.is_file():
        raise FileNotFoundError(f"Mentor profiles not found: {mentor_path}")
    if skill2_students is not None and not student_path.is_file():
        raise FileNotFoundError(f"Student profiles not found: {student_path}")

    has_explicit = any(x is not None for x in (skill2_graph, skill2_students, skill2_mentors))

    if skill2_graph is not None:
        gp = Path(skill2_graph).resolve()
        if not gp.is_file():
            raise FileNotFoundError(f"Academic graph not found: {gp}")
        graph_candidates = (gp,)
    else:
        graph_candidates = (default_outputs_graph, default_regen_graph)

    resource_mode = "explicit" if has_explicit else "default"

    needs_graph_rebuild = (
        resource_mode == "default" and not any(p.is_file() for p in graph_candidates)
    )

    return ResourcePaths(
        mentor_profiles_path=mentor_path,
        student_profiles_path=student_path,
        graph_candidates=graph_candidates,
        needs_graph_rebuild=needs_graph_rebuild,
        resource_mode=resource_mode,
    )


def ensure_graph_available(repo_root: Path, resources: ResourcePaths) -> Path:
    kit_graph = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "academic_graph.json"
    if kit_graph.is_file():
        return kit_graph
    kit_root = repo_root / "skill2_handoff" / "regenerate_kit"
    kit_graph.parent.mkdir(parents=True, exist_ok=True)
    for command in rebuild_commands(kit_root):
        subprocess.run(
            command,
            cwd=kit_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    return kit_graph


def rebuild_commands(kit_root: Path) -> list[list[str]]:
    commands: list[list[str]] = []
    seeds_dir = kit_root / "data" / "seeds"
    if not seeds_dir.is_dir():
        commands.append(["python3", "scripts/generate_mentor_pool.py"])
    commands.append(["python3", "scripts/build_graph.py"])
    return commands


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_standardized_resources(
    repo_root: Path,
    *,
    rebuild_graph_if_missing: bool = False,
    skill2_graph: Path | None = None,
    skill2_students: Path | None = None,
    skill2_mentors: Path | None = None,
) -> StandardizedResources:
    paths = resolve_resource_paths(
        repo_root,
        skill2_graph=skill2_graph,
        skill2_students=skill2_students,
        skill2_mentors=skill2_mentors,
    )
    mentors_bundle = _load_json(paths.mentor_profiles_path)
    students_bundle = _load_json(paths.student_profiles_path)

    graph: dict[str, Any] | None = None
    graph_source_path: Path | None = None

    if paths.resource_mode == "explicit" and len(paths.graph_candidates) == 1:
        cand = paths.graph_candidates[0]
        try:
            graph = _load_json(cand)
            graph_source_path = cand
        except JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in explicit academic graph {cand}: {exc}") from exc
    else:
        for i, candidate in enumerate(paths.graph_candidates):
            if not candidate.is_file():
                continue
            try:
                graph = _load_json(candidate)
                graph_source_path = candidate
                break
            except JSONDecodeError:
                alt = _load_first_valid_graph(candidate.parent)
                if alt is not None:
                    graph = alt
                    graph_source_path = candidate
                    break
                if i + 1 < len(paths.graph_candidates):
                    continue
        if graph is None and rebuild_graph_if_missing and paths.resource_mode == "default":
            graph_path = ensure_graph_available(repo_root, paths)
            if graph_path.is_file():
                try:
                    graph = _load_json(graph_path)
                    graph_source_path = graph_path
                except JSONDecodeError:
                    graph = _load_first_valid_graph(graph_path.parent)
                    if graph is not None:
                        graph_source_path = graph_path

    return StandardizedResources(
        mentors=list(mentors_bundle.get("mentors") or []),
        students=list(students_bundle.get("students") or []),
        graph=graph,
        paths=paths,
        graph_source_path=graph_source_path,
    )
