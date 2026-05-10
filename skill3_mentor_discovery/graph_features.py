from __future__ import annotations

from collections import defaultdict, deque

from skill3_mentor_discovery.graph_index import build_graph_index
from skill3_mentor_discovery.profile_utils import mentor_topic_terms
from skill3_mentor_discovery.trust_signals import compute_trust_signals_for_student

LIGHTWEIGHT_EDGE_TYPES = {"collaboration", "topic_similarity", "authored", "project_leads"}
STUDENT_LOCAL_TRUST_EDGE_TYPES = {
    "project_participation",
    "shared_interest",
    "skill_complementarity",
}


def _default_trust_signal_payload() -> dict[str, object]:
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


def prepare_graph_for_ranking(
    graph: dict[str, object] | None,
    *,
    max_full_graph_edges: int = 250_000,
    student_id: str | None = None,
) -> tuple[dict[str, object] | None, str, str | None]:
    if not graph:
        return None, "invalid_or_missing_graph_fallback_to_derived_mentor_graph", (
            "Graph data was unavailable, so Skill 3 switched to a derived mentor-only graph."
        )
    edges = list(graph.get("edges") or [])
    if len(edges) <= max_full_graph_edges:
        return graph, "loaded", None

    def edge_key(edge: dict[str, object]) -> tuple[str, str, str, str, str]:
        source = edge.get("source") or {}
        target = edge.get("target") or {}
        return (
            str(edge.get("type", "")),
            str(source.get("type", "")),
            str(source.get("id", "")),
            str(target.get("type", "")),
            str(target.get("id", "")),
        )

    slim_edges: list[dict[str, object]] = []
    seen_edges: set[tuple[str, str, str, str, str]] = set()
    peer_student_ids: set[str] = set()
    project_ids: set[str] = set()

    def append_unique(edge: dict[str, object]) -> None:
        key = edge_key(edge)
        if key in seen_edges:
            return
        seen_edges.add(key)
        slim_edges.append(edge)

    for edge in edges:
        edge_type = str(edge.get("type", ""))
        source = edge.get("source") or {}
        target = edge.get("target") or {}
        source_type = str(source.get("type", ""))
        source_id = str(source.get("id", ""))
        target_type = str(target.get("type", ""))
        target_id = str(target.get("id", ""))

        if edge_type in LIGHTWEIGHT_EDGE_TYPES:
            append_unique(edge)
            continue

        if not student_id or edge_type not in STUDENT_LOCAL_TRUST_EDGE_TYPES:
            continue

        if source_type == "student" and source_id == student_id:
            append_unique(edge)
            if edge_type in {"shared_interest", "skill_complementarity"} and target_type == "student":
                peer_student_ids.add(target_id)
            if edge_type == "project_participation" and target_type == "project":
                project_ids.add(target_id)
        elif target_type == "student" and target_id == student_id:
            append_unique(edge)
            if edge_type in {"shared_interest", "skill_complementarity"} and source_type == "student":
                peer_student_ids.add(source_id)

    if student_id:
        for edge in edges:
            edge_type = str(edge.get("type", ""))
            source = edge.get("source") or {}
            target = edge.get("target") or {}
            target_type = str(target.get("type", ""))
            target_id = str(target.get("id", ""))

            if (
                edge_type == "advising"
                and target_type == "student"
                and (target_id == student_id or target_id in peer_student_ids)
            ):
                append_unique(edge)
            elif edge_type == "project_leads" and target_type == "project" and target_id in project_ids:
                append_unique(edge)

    slim_graph = {
        "nodes": graph.get("nodes") or {},
        "edges": slim_edges,
    }
    notice = (
        f"Skill 3 switched to a lightweight mentor subgraph because the full graph "
        f"had {len(edges)} edges."
    )
    if student_id:
        notice = (
            f"{notice} Student-local trust evidence was preserved for ranking student {student_id}."
        )
    return (
        slim_graph,
        "loaded_lightweight_mentor_subgraph",
        notice,
    )

def build_mentor_graph(graph: dict[str, object] | None) -> dict[str, dict[str, float]]:
    adjacency: dict[str, dict[str, float]] = defaultdict(dict)
    if not graph:
        return adjacency
    for edge in graph.get("edges") or []:
        if edge.get("source", {}).get("type") != "mentor":
            continue
        if edge.get("target", {}).get("type") != "mentor":
            continue
        if edge.get("type") not in {"collaboration", "topic_similarity"}:
            continue
        source_id = edge["source"]["id"]
        target_id = edge["target"]["id"]
        weight = float(edge.get("weight", 1.0))
        adjacency[source_id][target_id] = max(adjacency[source_id].get(target_id, 0.0), weight)
        adjacency[target_id][source_id] = max(adjacency[target_id].get(source_id, 0.0), weight)
    return adjacency


def build_fallback_mentor_graph(mentors: list[dict[str, object]]) -> dict[str, dict[str, float]]:
    adjacency: dict[str, dict[str, float]] = defaultdict(dict)
    for index, mentor_a in enumerate(mentors):
        mentor_a_id = str(mentor_a.get("mentor_id", ""))
        terms_a = mentor_topic_terms(mentor_a)
        department_a = str(mentor_a.get("department", ""))
        for mentor_b in mentors[index + 1 :]:
            mentor_b_id = str(mentor_b.get("mentor_id", ""))
            terms_b = mentor_topic_terms(mentor_b)
            overlap = terms_a & terms_b
            shared_department = department_a and department_a == str(mentor_b.get("department", ""))
            if not overlap and not shared_department:
                continue
            weight = min(len(overlap) / 5.0, 1.0)
            if shared_department:
                weight = max(weight, 0.2)
            adjacency[mentor_a_id][mentor_b_id] = weight
            adjacency[mentor_b_id][mentor_a_id] = weight
    return adjacency


def _ensure_all_mentor_nodes(
    adjacency: dict[str, dict[str, float]],
    mentors: list[dict[str, object]],
) -> dict[str, dict[str, float]]:
    for mentor in mentors:
        mentor_id = str(mentor.get("mentor_id", ""))
        adjacency.setdefault(mentor_id, {})
    return adjacency


def compute_community_ids(adjacency: dict[str, dict[str, float]]) -> dict[str, str]:
    community_ids: dict[str, str] = {}
    community_index = 0
    for mentor_id in sorted(adjacency):
        if mentor_id in community_ids:
            continue
        queue: deque[str] = deque([mentor_id])
        while queue:
            current = queue.popleft()
            if current in community_ids:
                continue
            community_ids[current] = f"community_{community_index}"
            for neighbor in adjacency.get(current, {}):
                if neighbor not in community_ids:
                    queue.append(neighbor)
        community_index += 1
    return community_ids


def compute_degree_centrality(adjacency: dict[str, dict[str, float]]) -> dict[str, float]:
    if not adjacency:
        return {}
    denom = max(len(adjacency) - 1, 1)
    return {mentor_id: len(neighbors) / denom for mentor_id, neighbors in adjacency.items()}


def compute_mentor_authority(adjacency: dict[str, dict[str, float]]) -> dict[str, float]:
    if not adjacency:
        return {}

    weighted_totals = {
        mentor_id: sum(max(float(weight), 0.0) for weight in neighbors.values())
        for mentor_id, neighbors in adjacency.items()
    }
    max_total = max(weighted_totals.values(), default=0.0)
    if max_total <= 0.0:
        return {mentor_id: 0.0 for mentor_id in adjacency}
    return {
        mentor_id: weighted_total / max_total
        for mentor_id, weighted_total in weighted_totals.items()
    }


def compute_graph_confidence(meta_path_breakdown: dict[str, float]) -> float:
    high = float(meta_path_breakdown.get("project_path_score", 0.0)) + float(
        meta_path_breakdown.get("advising_path_score", 0.0)
    )
    medium = float(meta_path_breakdown.get("interest_path_score", 0.0))
    low = float(meta_path_breakdown.get("complementarity_path_score", 0.0))
    total = high + medium + low
    if total == 0.0:
        return 0.0

    reliability = ((1.0 * high) + (0.6 * medium) + (0.25 * low)) / total
    consistency = min(
        sum(score > 0.0 for score in meta_path_breakdown.values()) / 3.0,
        1.0,
    )
    return (0.7 * reliability) + (0.3 * consistency)


def compute_activity_score(mentor: dict[str, object], graph: dict[str, object] | None) -> float:
    h_index = float(mentor.get("h_index") or 0.0)
    authored_count = 0
    project_count = len(mentor.get("available_projects") or [])
    if graph:
        mentor_id = mentor.get("mentor_id")
        for edge in graph.get("edges") or []:
            if edge.get("type") == "authored" and edge.get("source", {}).get("id") == mentor_id:
                authored_count += 1
            if edge.get("type") == "project_leads" and edge.get("source", {}).get("id") == mentor_id:
                project_count += 1
    h_component = min(h_index / 80.0, 1.0)
    authored_component = min(authored_count / 20.0, 1.0)
    project_component = min(project_count / 10.0, 1.0)
    return (0.5 * h_component) + (0.3 * authored_component) + (0.2 * project_component)


def trust_signals_for_candidates(
    student_id: str,
    candidate_mentor_ids: list[str],
    graph: dict[str, object] | None,
) -> dict[str, dict[str, object]]:
    graph_index = build_graph_index(graph)
    return compute_trust_signals_for_student(student_id, candidate_mentor_ids, graph_index)


def graph_features_for_mentors(
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None,
    *,
    student_id: str | None = None,
) -> dict[str, dict[str, object]]:
    adjacency = build_mentor_graph(graph)
    if not adjacency:
        adjacency = build_fallback_mentor_graph(mentors)
    adjacency = _ensure_all_mentor_nodes(adjacency, mentors)
    community_ids = compute_community_ids(adjacency)
    authority = compute_mentor_authority(adjacency)
    trust_signals = (
        trust_signals_for_candidates(
            student_id,
            [str(mentor.get("mentor_id", "")) for mentor in mentors],
            graph,
        )
        if student_id
        else {}
    )
    features: dict[str, dict[str, object]] = {}
    for mentor in mentors:
        mentor_id = str(mentor.get("mentor_id", ""))
        trust_signal = trust_signals.get(mentor_id, _default_trust_signal_payload())
        meta_path_breakdown = dict(trust_signal.get("meta_path_breakdown") or {})
        features[mentor_id] = {
            "community_id": community_ids.get(mentor_id, "community_unknown"),
            "mentor_authority": float(authority.get(mentor_id, 0.0)),
            "centrality_score": float(authority.get(mentor_id, 0.0)),
            "network_proximity": 0.0,
            "personalized_proximity": float(trust_signal.get("personalized_proximity", 0.0)),
            "meta_path_breakdown": meta_path_breakdown,
            "graph_confidence": compute_graph_confidence(meta_path_breakdown),
            "top_evidence_paths": list(trust_signal.get("top_evidence_paths") or [])[:3],
            "activity_score": compute_activity_score(mentor, graph),
        }
    return features
