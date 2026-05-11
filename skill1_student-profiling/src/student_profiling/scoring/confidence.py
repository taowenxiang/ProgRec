"""Confidence scoring for extracted profile fields.

Confidence values reflect how reliable each extraction source is:
  - Structured fields (grade, major): 1.0 (ground truth)
  - Hobby → interest: 0.95 (direct mapping, very reliable)
  - Major → skill taxonomy: 0.85 (curated mapping, high reliability)
  - Unique Quality → skill/interest: 0.80 (curated, slightly ambiguous)
  - Story explicit mention: 0.70 (regex pattern match, moderate reliability)
  - Cross-source corroboration bonus: +0.10 (same term from 2+ sources)
"""

from __future__ import annotations

# Base confidence by source tag
SOURCE_CONFIDENCE: dict[str, float] = {
    "major_taxonomy": 0.85,
    "hobby_direct": 0.95,
    "unique_quality": 0.80,
    "story_explicit": 0.70,
}

CORROBORATION_BONUS = 0.10
MAX_CONFIDENCE = 1.0


def compute_term_confidence(sources: list[str]) -> float:
    """Compute confidence for a single term given its list of source tags.

    If the term appears in multiple sources, apply a corroboration bonus.
    """
    if not sources:
        return 0.50  # unknown source

    base = max(SOURCE_CONFIDENCE.get(s, 0.50) for s in sources)
    if len(set(sources)) > 1:
        base = min(base + CORROBORATION_BONUS, MAX_CONFIDENCE)
    return round(base, 3)


def build_confidence_dict(
    terms: list[str],
    sources_per_term: list[list[str]],
) -> dict[str, float]:
    """Build a {term: confidence} dict for a list of terms and their sources."""
    return {
        term: compute_term_confidence(srcs)
        for term, srcs in zip(terms, sources_per_term)
    }
