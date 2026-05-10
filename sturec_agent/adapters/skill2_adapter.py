from __future__ import annotations

from pathlib import Path


def resolve_skill2_resources(repo_root: Path) -> dict[str, object]:
    candidates = [
        (
            "outputs_bundle",
            repo_root / "skill2_handoff/outputs/student_profiles_standard.json",
            repo_root / "skill2_handoff/outputs/mentor_profiles_standard.json",
            repo_root / "skill2_handoff/outputs/academic_graph.json",
        ),
        (
            "regenerate_bundle",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/student_profiles_standard.json",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/mentor_profiles_standard.json",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json",
        ),
        (
            "processed_bundle",
            repo_root / "data/processed/student_profiles_standard.json",
            repo_root / "data/processed/mentor_profiles_standard.json",
            repo_root / "data/processed/academic_graph.json",
        ),
    ]
    for mode, students_path, mentors_path, graph_path in candidates:
        if students_path.is_file() and mentors_path.is_file():
            return {
                "resource_mode": mode,
                "students_path": students_path,
                "mentors_path": mentors_path,
                "graph_path": graph_path if graph_path.is_file() else None,
            }
    raise FileNotFoundError("Could not resolve Skill 2 resource bundle")
