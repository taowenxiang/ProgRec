from __future__ import annotations

import json
from pathlib import Path

from skill3_mentor_discovery.graph_features import prepare_graph_for_ranking
from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.profile_utils import mentor_topic_terms, student_interest_skill_terms
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


def evaluate_recall_at_k(repo_root: Path, top_k: int = 5, sample_size: int = 20) -> dict[str, float | int]:
    resources = load_standardized_resources(repo_root)
    prepared_graph, _, _ = prepare_graph_for_ranking(resources.graph)
    students = resources.students[:sample_size]
    if not students:
        return {"recall_at_k": 0.0, "evaluated_students": 0, "students_with_hits": 0}

    total_hits = 0
    students_with_hits = 0
    for student in students:
        student_terms = student_interest_skill_terms(student)
        ranked = rank_mentors_for_student(student, resources.mentors, graph=prepared_graph, top_k=top_k)
        has_hit = False
        for candidate in ranked:
            mentor = next(
                mentor
                for mentor in resources.mentors
                if mentor.get("mentor_id") == candidate.mentor_id
            )
            if student_terms & mentor_topic_terms(mentor):
                has_hit = True
                break
        if has_hit:
            students_with_hits += 1
            total_hits += 1
    recall = total_hits / len(students)
    return {
        "recall_at_k": recall,
        "evaluated_students": len(students),
        "students_with_hits": students_with_hits,
    }


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    print(json.dumps(evaluate_recall_at_k(repo_root), indent=2))
