from __future__ import annotations

from datetime import UTC, datetime


def _split_tags(value: str) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for part in value.split(","):
        tag = part.strip().lower()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def normalize_manual_profile(raw: dict[str, str]) -> dict[str, object]:
    return {
        "student_id": f"cli-custom-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "grade": raw.get("grade", "").strip() or "unknown",
        "major": raw.get("major", "").strip() or "unknown",
        "skills": _split_tags(raw.get("skills", "")),
        "interests": _split_tags(raw.get("interests", "")),
        "experience_summary": raw.get("experience_summary", "").strip(),
        "availability": raw.get("availability", "moderate").strip().lower() or "moderate",
        "resume_text": raw.get("resume_text", "").strip(),
    }
