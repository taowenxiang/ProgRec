"""Teammate recommendation scores."""

from __future__ import annotations

from typing import Any

from skill.project_scoring import jaccard_similarity


def compute_shared_interest_score(
    student_interests: list[str],
    candidate_interests: list[str],
) -> float:
    return jaccard_similarity(student_interests, candidate_interests)


def compute_complementarity_score(missing_skills: list[str], candidate_skills: list[str]) -> float:
    if not missing_skills:
        return 0.3
    return jaccard_similarity(missing_skills, candidate_skills)


def compute_availability_score(availability: str) -> float:
    a = str(availability or "").strip().lower()
    if a == "high":
        return 1.0
    if a == "moderate":
        return 0.7
    if a == "low":
        return 0.4
    if not a or a == "unknown":
        return 0.5
    return 0.5


def compute_graph_relation_score(graph_edges_or_neighbors: list[dict[str, Any]] | None) -> float:
    """Use shared_interest / skill_complementarity edges between target and candidate."""
    if not graph_edges_or_neighbors:
        return 0.0
    best = 0.0
    for rec in graph_edges_or_neighbors:
        w = float(rec.get("weight", 0.6))
        w = max(0.0, min(1.0, w))
        et = str(rec.get("edge_type") or "")
        if et in ("shared_interest", "skill_complementarity"):
            base = 0.6 + 0.4 * w
            best = max(best, min(1.0, base))
    return best


def compute_teammate_score(
    shared_interest_score: float,
    complementarity_score: float,
    availability_score: float,
    graph_relation_score: float = 0.0,
    *,
    has_graph_signal: bool = False,
) -> float:
    sis = max(0.0, min(1.0, shared_interest_score))
    comp = max(0.0, min(1.0, complementarity_score))
    av = max(0.0, min(1.0, availability_score))
    gr = max(0.0, min(1.0, graph_relation_score))
    if has_graph_signal and gr > 0.0:
        score = 0.35 * sis + 0.35 * comp + 0.10 * av + 0.20 * gr
    else:
        score = 0.45 * sis + 0.45 * comp + 0.10 * av
    return max(0.0, min(1.0, score))


def edges_between_students(
    graph_context: dict[str, Any] | None,
    target_id: str,
    candidate_id: str,
) -> list[dict[str, Any]]:
    if not graph_context or "edge_index" not in graph_context:
        return []
    idx = graph_context["edge_index"]
    tk = f"student:{target_id}"
    ck = f"student:{candidate_id}"
    hits: list[dict[str, Any]] = []
    for rec in idx.get("edges_by_type", {}).get("shared_interest", []):
        keys = {rec["source_key"], rec["target_key"]}
        if tk in keys and ck in keys:
            hits.append(rec)
    for rec in idx.get("edges_by_type", {}).get("skill_complementarity", []):
        keys = {rec["source_key"], rec["target_key"]}
        if tk in keys and ck in keys:
            hits.append(rec)
    return hits
