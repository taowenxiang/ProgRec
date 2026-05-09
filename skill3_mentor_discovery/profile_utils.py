from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

TOKEN_RE = re.compile(r"[a-z0-9\+\#]+")


def normalize_terms(values: Iterable[str]) -> list[str]:
    text = " ".join(str(v).lower() for v in values if v)
    return TOKEN_RE.findall(text)


def token_counter(values: Iterable[str]) -> Counter[str]:
    return Counter(normalize_terms(values))


def build_student_counter(student: dict[str, object]) -> Counter[str]:
    return token_counter(
        [
            student.get("major", ""),
            " ".join(student.get("skills") or []),
            " ".join(student.get("interests") or []),
            student.get("experience_summary", ""),
        ]
    )


def build_mentor_counter(mentor: dict[str, object]) -> Counter[str]:
    return token_counter(
        [
            mentor.get("department", ""),
            " ".join(mentor.get("research_areas") or []),
            " ".join(mentor.get("keywords") or []),
            " ".join(mentor.get("required_skills") or []),
            mentor.get("profile_text_for_embedding", ""),
        ]
    )


def student_interest_skill_terms(student: dict[str, object]) -> set[str]:
    return set(
        normalize_terms(
            list(student.get("skills") or []) + list(student.get("interests") or [])
        )
    )


def mentor_topic_terms(mentor: dict[str, object]) -> set[str]:
    return set(
        normalize_terms(
            list(mentor.get("research_areas") or [])
            + list(mentor.get("keywords") or [])
            + list(mentor.get("required_skills") or [])
        )
    )
