from __future__ import annotations

from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


def run_skill3(repo_root: Path, student_profile: dict[str, object], top_k: int) -> dict[str, object]:
    resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=False)
    mentor_candidates = rank_mentors_for_student(
        student_profile,
        resources.mentors,
        graph=resources.graph,
        top_k=top_k,
    )
    return {
        "student_id": str(student_profile.get("student_id", "")),
        "mentor_candidates": [candidate.to_dict() for candidate in mentor_candidates],
    }
