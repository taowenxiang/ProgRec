from __future__ import annotations


def _format_path_family(path_key: str) -> str:
    label = path_key.replace("_path_score", "").replace("_", " ")
    return label.strip() or "graph"


def build_reasons(
    mentor: dict[str, object],
    overlap_terms: set[str],
    community_id: str,
    activity_score: float,
    meta_path_breakdown: dict[str, float] | None = None,
    graph_confidence: float = 0.0,
    top_evidence_paths: list[str] | None = None,
) -> list[str]:
    reasons: list[str] = []
    if overlap_terms:
        sample_terms = ", ".join(sorted(list(overlap_terms))[:3])
        reasons.append(f"Topic fit is supported by overlap in {sample_terms}.")

    graph_breakdown = dict(meta_path_breakdown or {})
    strongest_graph_families = [
        _format_path_family(path_key)
        for path_key, _score in sorted(
            graph_breakdown.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        if float(_score) > 0.0
    ][:2]
    if strongest_graph_families:
        reasons.append(
            "Graph evidence is strongest through "
            + " and ".join(strongest_graph_families)
            + " path signals."
        )
    if top_evidence_paths:
        reasons.append(f"Representative graph path: {top_evidence_paths[0]}.")
    if graph_confidence >= 0.7:
        reasons.append("Graph support is high confidence because it includes stronger trust-weighted connections.")
    elif graph_confidence > 0.0:
        reasons.append("Graph support is useful but should be read cautiously because the trust evidence is lighter.")

    if community_id != "community_unknown":
        reasons.append(f"This mentor belongs to {community_id} in the mentor collaboration graph.")
    if activity_score > 0.35:
        reasons.append("The mentor shows solid research activity based on profile and graph signals.")
    if not reasons:
        reasons.append("This mentor remains competitive based on overall topic relevance.")
    return reasons
