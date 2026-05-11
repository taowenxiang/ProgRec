"""Taxonomy mapping - load and apply major/hobby/UQ taxonomy JSONs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"


@lru_cache(maxsize=1)
def _load_major_skills() -> dict[str, list[str]]:
    with open(_DATA_DIR / "major_skills.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_hobby_interests() -> dict[str, list[str]]:
    with open(_DATA_DIR / "hobby_interests.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_uq_mapping() -> dict[str, dict]:
    with open(_DATA_DIR / "uq_mapping.json") as f:
        return json.load(f)


def get_skills_from_major(major: str) -> tuple[list[str], list[str]]:
    """Return (skills, sources) from major taxonomy."""
    mapping = _load_major_skills()
    skills = mapping.get(major, [])
    sources = ["major_taxonomy"] * len(skills)
    return skills, sources


def get_interests_from_hobbies(hobbies: list[str]) -> tuple[list[str], list[str]]:
    """Return (interests, sources) from hobby taxonomy."""
    mapping = _load_hobby_interests()
    interests: list[str] = []
    sources: list[str] = []
    for hobby in hobbies:
        terms = mapping.get(hobby, [hobby])  # fallback: use hobby name directly
        interests.extend(terms)
        sources.extend(["hobby_direct"] * len(terms))
    return interests, sources


def get_terms_from_uq(uq: str) -> tuple[list[str], list[str], list[str], list[str]]:
    """Return (skills, skill_sources, interests, interest_sources) from UQ mapping."""
    mapping = _load_uq_mapping()
    entry = mapping.get(uq)
    if not entry:
        return [], [], [], []

    uq_type = entry.get("type", "personality")
    terms = entry.get("terms", [])

    if uq_type == "skill":
        return terms, ["unique_quality"] * len(terms), [], []
    elif uq_type == "interest":
        return [], [], terms, ["unique_quality"] * len(terms)
    else:  # personality - no extractable terms
        return [], [], [], []
