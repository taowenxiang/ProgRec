"""Taxonomy mapping - load and apply major/hobby/UQ taxonomy JSONs."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from student_profiling.postprocess import clean_term_list

_DATA_DIR = files("student_profiling").joinpath("taxonomy", "data")


@lru_cache(maxsize=1)
def _load_major_skills() -> dict[str, list[str]]:
    with _DATA_DIR.joinpath("major_skills.json").open() as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_hobby_interests() -> dict[str, list[str]]:
    with _DATA_DIR.joinpath("hobby_interests.json").open() as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_uq_mapping() -> dict[str, dict]:
    with _DATA_DIR.joinpath("uq_mapping.json").open() as f:
        return json.load(f)


def get_skills_from_major(major: str) -> tuple[list[str], list[str]]:
    """Return (skills, sources) from major taxonomy."""
    mapping = _load_major_skills()
    skills = clean_term_list(mapping.get(major, []), kind="skill")
    sources = ["major_taxonomy"] * len(skills)
    return skills, sources


def get_interests_from_hobbies(hobbies: list[str]) -> tuple[list[str], list[str]]:
    """Return (interests, sources) from hobby taxonomy."""
    mapping = _load_hobby_interests()
    interests: list[str] = []
    sources: list[str] = []
    for hobby in hobbies:
        terms = mapping.get(hobby, [hobby])  # fallback: use hobby name directly
        cleaned = clean_term_list(terms, kind="interest")
        interests.extend(cleaned)
        sources.extend(["hobby_direct"] * len(cleaned))
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
        terms = clean_term_list(terms, kind="skill")
        return terms, ["unique_quality"] * len(terms), [], []
    elif uq_type == "interest":
        terms = clean_term_list(terms, kind="interest")
        return [], [], terms, ["unique_quality"] * len(terms)
    else:  # personality - no extractable terms
        return [], [], [], []
