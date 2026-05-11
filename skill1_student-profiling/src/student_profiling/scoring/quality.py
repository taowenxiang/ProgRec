"""Profile quality scoring.

Composite score (0.0–1.0) combining:
  - Information density: how many distinct sources contributed
  - Extraction richness: total terms extracted vs expected minimum
  - Confidence average: mean confidence across all extracted terms
"""

from __future__ import annotations


def compute_profile_quality(
    skills: list[str],
    interests: list[str],
    experience_summary: str,
    skill_sources: list[list[str]],
    interest_sources: list[list[str]],
    skill_confidences: dict[str, float],
    interest_confidences: dict[str, float],
) -> float:
    """Compute a composite quality score for a student profile.

    Returns a float in [0.0, 1.0].
    """
    # 1. Source diversity: how many distinct source types contributed
    all_sources: set[str] = set()
    for srcs in skill_sources + interest_sources:
        all_sources.update(srcs)
    source_diversity = min(len(all_sources) / 4.0, 1.0)  # 4 source types max

    # 2. Term richness: total terms vs expected (8 skills + 6 interests = 14)
    total_terms = len(skills) + len(interests)
    term_richness = min(total_terms / 14.0, 1.0)

    # 3. Experience quality: non-empty and reasonably long
    exp_len = len(experience_summary.strip())
    experience_quality = min(exp_len / 150.0, 1.0)  # 150 chars = full score

    # 4. Average confidence
    all_confidences = list(skill_confidences.values()) + list(interest_confidences.values())
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.5

    # Weighted composite
    score = (
        0.25 * source_diversity
        + 0.30 * term_richness
        + 0.20 * experience_quality
        + 0.25 * avg_confidence
    )
    return round(score, 4)
