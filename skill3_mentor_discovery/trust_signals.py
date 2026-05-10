from __future__ import annotations

from skill3_mentor_discovery.graph_index import GraphIndex, get_edge_trust_weight

PROJECT_EVIDENCE_PATH = "student -> project_participation -> project -> project_leads -> mentor"
INTEREST_EVIDENCE_PATH = "student -> shared_interest -> student -> advising <- mentor"
COMPLEMENTARITY_EVIDENCE_PATH = (
    "student -> skill_complementarity -> student -> advising <- mentor"
)


def _default_signal() -> dict[str, object]:
    return {
        "personalized_proximity": 0.0,
        "meta_path_breakdown": {
            "interest_path_score": 0.0,
            "complementarity_path_score": 0.0,
            "project_path_score": 0.0,
            "advising_path_score": 0.0,
        },
        "top_evidence_paths": [],
    }


def _append_evidence(signal: dict[str, object], evidence_path: str) -> None:
    evidence_paths = signal["top_evidence_paths"]
    if evidence_path not in evidence_paths:
        evidence_paths.append(evidence_path)


def _related_students(
    graph_index: GraphIndex,
    student_key: tuple[str, str],
    edge_type: str,
) -> set[tuple[str, str]]:
    related_students = set()
    for related_node in graph_index.forward_neighbors.get(student_key, {}).get(edge_type, []):
        if related_node[0] == "student":
            related_students.add(related_node)
    for related_node in graph_index.reverse_neighbors.get(student_key, {}).get(edge_type, []):
        if related_node[0] == "student":
            related_students.add(related_node)
    return related_students


def compute_trust_signals_for_student(
    student_id: str,
    candidate_mentor_ids: list[str],
    graph_index: GraphIndex,
) -> dict[str, dict[str, object]]:
    signals = {mentor_id: _default_signal() for mentor_id in candidate_mentor_ids}
    if not student_id or not candidate_mentor_ids:
        return signals

    candidate_mentor_set = set(candidate_mentor_ids)
    project_weight = get_edge_trust_weight("project_participation")
    interest_weight = get_edge_trust_weight("shared_interest")
    complementarity_weight = get_edge_trust_weight("skill_complementarity")
    advising_weight = get_edge_trust_weight("advising")

    student_key = ("student", student_id)

    for project_key in graph_index.forward_neighbors.get(student_key, {}).get(
        "project_participation", []
    ):
        for mentor_type, mentor_id in graph_index.reverse_neighbors.get(project_key, {}).get(
            "project_leads", []
        ):
            if mentor_type != "mentor" or mentor_id not in candidate_mentor_set:
                continue
            signal = signals[mentor_id]
            signal["personalized_proximity"] += project_weight
            signal["meta_path_breakdown"]["project_path_score"] += project_weight
            _append_evidence(signal, PROJECT_EVIDENCE_PATH)

    for related_student_key in _related_students(graph_index, student_key, "shared_interest"):
        for mentor_type, mentor_id in graph_index.reverse_neighbors.get(
            related_student_key, {}
        ).get("advising", []):
            if mentor_type != "mentor" or mentor_id not in candidate_mentor_set:
                continue
            signal = signals[mentor_id]
            signal["personalized_proximity"] += interest_weight
            signal["meta_path_breakdown"]["interest_path_score"] += interest_weight
            signal["meta_path_breakdown"]["advising_path_score"] += advising_weight
            _append_evidence(signal, INTEREST_EVIDENCE_PATH)

    for related_student_key in _related_students(
        graph_index, student_key, "skill_complementarity"
    ):
        for mentor_type, mentor_id in graph_index.reverse_neighbors.get(
            related_student_key, {}
        ).get("advising", []):
            if mentor_type != "mentor" or mentor_id not in candidate_mentor_set:
                continue
            signal = signals[mentor_id]
            signal["personalized_proximity"] += complementarity_weight
            signal["meta_path_breakdown"]["complementarity_path_score"] += (
                complementarity_weight
            )
            signal["meta_path_breakdown"]["advising_path_score"] += advising_weight
            _append_evidence(signal, COMPLEMENTARITY_EVIDENCE_PATH)

    return signals
