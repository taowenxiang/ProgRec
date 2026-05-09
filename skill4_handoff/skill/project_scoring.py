"""Project–student fit scores (keyword-based; embeddings optional later)."""

from __future__ import annotations

from typing import Iterable


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(str(x).lower() for x in a), set(str(x).lower() for x in b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compute_topic_match_score(student_interests: list[str], project_topic_tags: list[str]) -> float:
    return jaccard_similarity(student_interests, project_topic_tags)


def compute_skill_match_score(student_skills: list[str], required_skills: list[str]) -> float:
    if not required_skills:
        return 0.5
    return jaccard_similarity(student_skills, required_skills)


def compute_skill_gap(student_skills: list[str], required_skills: list[str]) -> list[str]:
    need = {str(s).lower() for s in required_skills}
    have = {str(s).lower() for s in student_skills}
    return sorted(need - have)


def _grade_level(grade: str) -> int:
    g = str(grade or "").strip().lower()
    mapping = {
        "freshman": 1,
        "year 1": 1,
        "first year": 1,
        "1": 1,
        "sophomore": 2,
        "year 2": 2,
        "second year": 2,
        "2": 2,
        "junior": 3,
        "year 3": 3,
        "third year": 3,
        "3": 3,
        "senior": 4,
        "year 4": 4,
        "fourth year": 4,
        "4": 4,
    }
    if g in mapping:
        return mapping[g]
    for k, v in mapping.items():
        if k in g:
            return v
    return 2


def _difficulty_level(difficulty: str) -> int:
    d = str(difficulty or "medium").strip().lower()
    if d == "easy":
        return 1
    if d == "hard":
        return 3
    return 2


def compute_difficulty_match_score(grade: str, difficulty: str) -> float:
    gl = _grade_level(grade)
    dl = _difficulty_level(difficulty)
    if gl >= dl:
        return 1.0
    if gl == dl - 1:
        return 0.7
    return 0.4


def compute_project_fit_score(
    topic_match_score: float,
    skill_match_score: float,
    difficulty_match_score: float,
    mentor_project_link_score: float = 1.0,
) -> float:
    fit = (
        0.40 * topic_match_score
        + 0.30 * skill_match_score
        + 0.20 * difficulty_match_score
        + 0.10 * mentor_project_link_score
    )
    return max(0.0, min(1.0, fit))


def matched_interests_skills(
    student_interests: list[str],
    student_skills: list[str],
    topic_tags: list[str],
    required_skills: list[str],
) -> tuple[list[str], list[str]]:
    si = {str(x).lower() for x in student_interests}
    sk = {str(x).lower() for x in student_skills}
    tt = {str(x).lower() for x in topic_tags}
    rs = {str(x).lower() for x in required_skills}
    return sorted(si & tt), sorted(sk & rs)
