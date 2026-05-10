from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

EDGE_TRUST_TIERS: dict[str, str] = {
    "project_participation": "high",
    "project_leads": "high",
    "advising": "high",
    "shared_interest": "medium",
    "topic_similarity": "medium",
    "collaboration": "medium",
    "skill_complementarity": "low",
}

TRUST_WEIGHTS: dict[str, float] = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.25,
}


def get_edge_trust_tier(edge_type: str) -> str | None:
    return EDGE_TRUST_TIERS.get(edge_type)


def get_edge_trust_weight(edge_type: str) -> float:
    trust_tier = get_edge_trust_tier(edge_type)
    if trust_tier is None:
        return 0.0
    return TRUST_WEIGHTS[trust_tier]


@dataclass
class GraphIndex:
    forward_neighbors: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = field(
        default_factory=dict
    )
    reverse_neighbors: dict[tuple[str, str], dict[str, list[tuple[str, str]]]] = field(
        default_factory=dict
    )
    mentor_ids: set[str] = field(default_factory=set)


def build_graph_index(graph: dict[str, object] | None) -> GraphIndex:
    forward_neighbors: defaultdict[tuple[str, str], defaultdict[str, list[tuple[str, str]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    reverse_neighbors: defaultdict[tuple[str, str], defaultdict[str, list[tuple[str, str]]]] = (
        defaultdict(lambda: defaultdict(list))
    )
    mentor_ids: set[str] = set()

    if not graph:
        return GraphIndex()

    for mentor in (graph.get("nodes") or {}).get("mentor") or []:
        mentor_id = str(mentor.get("mentor_id", ""))
        if mentor_id:
            mentor_ids.add(mentor_id)

    for edge in graph.get("edges") or []:
        edge_type = str(edge.get("type", ""))
        source = edge.get("source") or {}
        target = edge.get("target") or {}
        source_type = str(source.get("type", ""))
        source_id = str(source.get("id", ""))
        target_type = str(target.get("type", ""))
        target_id = str(target.get("id", ""))

        if not edge_type or not source_type or not source_id or not target_type or not target_id:
            continue

        source_key = (source_type, source_id)
        target_key = (target_type, target_id)
        forward_neighbors[source_key][edge_type].append(target_key)
        reverse_neighbors[target_key][edge_type].append(source_key)

        if source_type == "mentor":
            mentor_ids.add(source_id)
        if target_type == "mentor":
            mentor_ids.add(target_id)

    return GraphIndex(
        forward_neighbors={
            node: dict(neighbors) for node, neighbors in forward_neighbors.items()
        },
        reverse_neighbors={
            node: dict(neighbors) for node, neighbors in reverse_neighbors.items()
        },
        mentor_ids=mentor_ids,
    )
