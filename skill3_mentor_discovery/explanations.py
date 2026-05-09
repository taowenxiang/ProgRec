from __future__ import annotations


def build_reasons(mentor: dict[str, object], overlap_terms: set[str], community_id: str, activity_score: float) -> list[str]:
    reasons: list[str] = []
    if overlap_terms:
        sample_terms = ", ".join(sorted(list(overlap_terms))[:3])
        reasons.append(f"Topic fit is supported by overlap in {sample_terms}.")
    if community_id != "community_unknown":
        reasons.append(f"This mentor belongs to {community_id} in the mentor collaboration graph.")
    if activity_score > 0.35:
        reasons.append("The mentor shows solid research activity based on profile and graph signals.")
    if not reasons:
        reasons.append("This mentor remains competitive based on overall topic relevance.")
    return reasons
