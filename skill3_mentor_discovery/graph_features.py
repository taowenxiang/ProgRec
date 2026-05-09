from __future__ import annotations

from collections import defaultdict, deque

from skill3_mentor_discovery.profile_utils import mentor_topic_terms

LIGHTWEIGHT_EDGE_TYPES = {"collaboration", "topic_similarity", "authored", "project_leads"}


def prepare_graph_for_ranking(
    graph: dict[str, object] | None,
    *,
    max_full_graph_edges: int = 250_000,
) -> tuple[dict[str, object] | None, str, str | None]:
    if not graph:
        return None, "invalid_or_missing_graph_fallback_to_derived_mentor_graph", (
            "Graph data was unavailable, so Skill 3 switched to a derived mentor-only graph."
        )
    edges = list(graph.get("edges") or [])
    if len(edges) <= max_full_graph_edges:
        return graph, "loaded", None
    slim_edges = [edge for edge in edges if edge.get("type") in LIGHTWEIGHT_EDGE_TYPES]
    slim_graph = {
        "nodes": graph.get("nodes") or {},
        "edges": slim_edges,
    }
    return (
        slim_graph,
        "loaded_lightweight_mentor_subgraph",
        (
            f"Skill 3 switched to a lightweight mentor subgraph because the full graph "
            f"had {len(edges)} edges."
        ),
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


def graph_features_for_mentors(mentors: list[dict[str, object]], graph: dict[str, object] | None) -> dict[str, dict[str, float | str]]:
    adjacency = build_mentor_graph(graph)
    if not adjacency:
        adjacency = build_fallback_mentor_graph(mentors)
    community_ids = compute_community_ids(adjacency)
    centrality = compute_degree_centrality(adjacency)
    features: dict[str, dict[str, float | str]] = {}
    for mentor in mentors:
        mentor_id = str(mentor.get("mentor_id", ""))
        features[mentor_id] = {
            "community_id": community_ids.get(mentor_id, "community_unknown"),
            "centrality_score": float(centrality.get(mentor_id, 0.0)),
            "network_proximity": 0.0,
            "activity_score": compute_activity_score(mentor, graph),
        }
    return features
