from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    parts = [text]
    for separator in [",", ";"]:
        if separator in text:
            parts = text.split(separator)
            break
    return [part.strip().lower() for part in parts if part.strip()]


def _topic_terms(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    normalized = text.replace("&", " and ")
    parts = [part.strip().lower() for part in normalized.split(" and ") if part.strip()]
    return parts or [text.lower()]


def _experience_summary(slots: dict[str, object]) -> str:
    pieces: list[str] = []
    topic = str(slots.get("research_topic") or "").strip()
    program = str(slots.get("program_type") or "").strip()
    experience = str(slots.get("experience_level") or "").strip()
    freeform = str(slots.get("profile_details") or slots.get("description") or "").strip()
    if topic:
        pieces.append(f"Interested in {topic}.")
    if program:
        pieces.append(f"Targeting {program}.")
    if experience:
        pieces.append(f"Experience level: {experience}.")
    if freeform:
        pieces.append(freeform)
    return " ".join(pieces).strip()


def standardize_temporary_profile(slots: dict[str, object]) -> dict[str, object]:
    topic = slots.get("research_topic") or slots.get("topic") or slots.get("research_area") or ""
    skills = _as_list(slots.get("skills"))
    topic_terms = _topic_terms(topic)
    interests = topic_terms + [item for item in _as_list(slots.get("interests")) if item not in topic_terms]
    availability = str(slots.get("availability") or "moderate").strip().lower() or "moderate"
    return {
        "student_id": f"chat-temp-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "grade": str(slots.get("grade") or "unknown").strip() or "unknown",
        "major": str(slots.get("major") or "unknown").strip() or "unknown",
        "skills": skills,
        "interests": interests,
        "experience_summary": _experience_summary({**slots, "research_topic": topic}),
        "availability": availability,
    }
