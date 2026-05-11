from __future__ import annotations

from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


def _data_sources(resources) -> dict[str, object]:
    paths = resources.paths
    return {
        "student_profiles": str(paths.student_profiles_path.resolve()),
        "mentor_profiles": str(paths.mentor_profiles_path.resolve()),
        "academic_graph": str(resources.graph_source_path.resolve())
        if resources.graph_source_path
        else None,
        "resource_mode": paths.resource_mode,
    }


def run_skill3(
    repo_root: Path,
    student_profile: dict[str, object],
    top_k: int,
    *,
    skill2_graph: Path | None = None,
    skill2_students: Path | None = None,
    skill2_mentors: Path | None = None,
) -> dict[str, object]:
    resources = load_standardized_resources(
        repo_root,
        rebuild_graph_if_missing=False,
        skill2_graph=skill2_graph,
        skill2_students=skill2_students,
        skill2_mentors=skill2_mentors,
    )
    mentor_candidates = rank_mentors_for_student(
        student_profile,
        resources.mentors,
        graph=resources.graph,
        top_k=top_k,
    )
    return {
        "student_id": str(student_profile.get("student_id", "")),
        "mentor_candidates": [candidate.to_dict() for candidate in mentor_candidates],
        "data_sources": _data_sources(resources),
    }
