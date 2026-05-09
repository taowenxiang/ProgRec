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
    outputs_graph_path: Path
    graph_path: Path
    needs_graph_rebuild: bool


@dataclass
class StandardizedResources:
    mentors: list[dict[str, Any]]
    students: list[dict[str, Any]]
    graph: dict[str, Any] | None
    paths: ResourcePaths


def _load_first_valid_graph(processed_dir: Path) -> dict[str, Any] | None:
    candidates = sorted(processed_dir.glob("academic_graph*.json"))
    for candidate in candidates:
        try:
            return _load_json(candidate)
        except JSONDecodeError:
            continue
    return None


def resolve_resource_paths(repo_root: Path) -> ResourcePaths:
    outputs = repo_root / "skill2_handoff" / "outputs"
    outputs_graph_path = outputs / "academic_graph.json"
    graph_path = repo_root / "skill2_handoff" / "regenerate_kit" / "data" / "processed" / "academic_graph.json"
    return ResourcePaths(
        mentor_profiles_path=outputs / "mentor_profiles_standard.json",
        student_profiles_path=outputs / "student_profiles_standard.json",
        outputs_graph_path=outputs_graph_path,
        graph_path=graph_path,
        needs_graph_rebuild=not outputs_graph_path.is_file() and not graph_path.is_file(),
    )


def ensure_graph_available(repo_root: Path, resources: ResourcePaths) -> Path:
    if resources.graph_path.is_file():
        return resources.graph_path
    kit_root = repo_root / "skill2_handoff" / "regenerate_kit"
    resources.graph_path.parent.mkdir(parents=True, exist_ok=True)
    for command in rebuild_commands(kit_root):
        subprocess.run(
            command,
            cwd=kit_root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    return resources.graph_path


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


def load_standardized_resources(repo_root: Path, *, rebuild_graph_if_missing: bool = False) -> StandardizedResources:
    paths = resolve_resource_paths(repo_root)
    mentors_bundle = _load_json(paths.mentor_profiles_path)
    students_bundle = _load_json(paths.student_profiles_path)
    graph: dict[str, Any] | None = None
    graph_path = paths.outputs_graph_path if paths.outputs_graph_path.is_file() else paths.graph_path
    if graph_path.is_file():
        try:
            graph = _load_json(graph_path)
        except JSONDecodeError:
            graph = _load_first_valid_graph(graph_path.parent)
            if graph is None and graph_path.parent != paths.graph_path.parent:
                graph = _load_first_valid_graph(paths.graph_path.parent)
    elif rebuild_graph_if_missing:
        graph_path = ensure_graph_available(repo_root, paths)
        if graph_path.is_file():
            try:
                graph = _load_json(graph_path)
            except JSONDecodeError:
                graph = _load_first_valid_graph(graph_path.parent)
    return StandardizedResources(
        mentors=list(mentors_bundle.get("mentors") or []),
        students=list(students_bundle.get("students") or []),
        graph=graph,
        paths=paths,
    )
