from __future__ import annotations

REASON_PROMPT = """
You write mentor recommendation explanations for ProgRec.
Return strict JSON with:
- reason_text

Rules:
- Use only the provided evidence.
- Do not invent projects, graph paths, or mentor traits.
- Mention the strongest one or two evidence families.
- If graph confidence is low, sound cautious.
- Keep the explanation to 2 or 3 sentences.
""".strip()


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


def build_reason_evidence(
    *,
    mentor: dict[str, object],
    overlap_terms: set[str],
    community_id: str,
    activity_score: float,
    meta_path_breakdown: dict[str, float] | None,
    graph_confidence: float,
    top_evidence_paths: list[str] | None,
    topic_score: float,
    graph_score: float,
    personalized_proximity: float,
    mentor_authority: float,
) -> dict[str, object]:
    return {
        "mentor_id": str(mentor.get("mentor_id", "")),
        "mentor_name": str(mentor.get("name", "")),
        "overlap_terms": sorted(overlap_terms),
        "community_id": community_id,
        "activity_score": activity_score,
        "meta_path_breakdown": dict(meta_path_breakdown or {}),
        "graph_confidence": graph_confidence,
        "top_evidence_paths": list(top_evidence_paths or [])[:3],
        "topic_score": topic_score,
        "graph_score": graph_score,
        "personalized_proximity": personalized_proximity,
        "mentor_authority": mentor_authority,
    }


def fallback_reason_text(evidence: dict[str, object]) -> str:
    overlap_terms = list(evidence.get("overlap_terms") or [])
    graph_paths = list(evidence.get("top_evidence_paths") or [])
    graph_confidence = float(evidence.get("graph_confidence", 0.0))
    parts: list[str] = []
    if overlap_terms:
        parts.append("Topic fit is supported by " + ", ".join(overlap_terms[:3]) + ".")
    if graph_paths:
        parts.append(f"Representative graph path: {graph_paths[0]}.")
    if graph_confidence >= 0.7:
        parts.append("Graph evidence is comparatively strong.")
    elif graph_confidence > 0.0:
        parts.append("Graph evidence is present but should be read cautiously.")
    return " ".join(parts) if parts else "This mentor remains competitive based on overall topic relevance."


def generate_reason_text(evidence: dict[str, object], *, llm_client) -> str:
    if llm_client is None:
        return fallback_reason_text(evidence)
    try:
        payload = llm_client.complete_json(f"{REASON_PROMPT}\nEvidence: {evidence}")
    except Exception:
        return fallback_reason_text(evidence)
    text = str(payload.get("reason_text", "")).strip()
    return text or fallback_reason_text(evidence)
