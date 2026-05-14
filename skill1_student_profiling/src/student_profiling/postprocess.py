"""Shared term cleanup helpers for taxonomy and extracted profile terms."""

from __future__ import annotations


GENERIC_SKILL_TERMS = {
    "research",
    "science",
    "technology",
    "knowledge",
    "skills",
    "abilities",
}

GENERIC_INTEREST_TERMS = {
    "learning",
    "society",
    "culture",
    "community",
    "science",
}


def clean_term(term: str, *, kind: str = "generic") -> str | None:
    value = term.strip().lower()
    if not value:
        return None
    if kind == "skill" and value in GENERIC_SKILL_TERMS:
        return None
    if kind == "interest" and value in GENERIC_INTEREST_TERMS:
        return None
    if kind == "generic" and value in GENERIC_SKILL_TERMS.union(GENERIC_INTEREST_TERMS):
        return None
    return value


def clean_term_list(terms: list[str], *, kind: str = "generic") -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        value = clean_term(term, kind=kind)
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)
    return cleaned


def clean_terms_with_sources(
    terms: list[str],
    sources: list[list[str]],
    *,
    kind: str = "generic",
) -> tuple[list[str], list[list[str]]]:
    cleaned_terms: list[str] = []
    cleaned_sources: list[list[str]] = []
    seen: dict[str, int] = {}

    for term, srcs in zip(terms, sources):
        value = clean_term(term, kind=kind)
        if not value:
            continue
        if value in seen:
            existing_idx = seen[value]
            for source in srcs:
                if source not in cleaned_sources[existing_idx]:
                    cleaned_sources[existing_idx].append(source)
            continue
        seen[value] = len(cleaned_terms)
        cleaned_terms.append(value)
        cleaned_sources.append(list(srcs))

    return cleaned_terms, cleaned_sources
