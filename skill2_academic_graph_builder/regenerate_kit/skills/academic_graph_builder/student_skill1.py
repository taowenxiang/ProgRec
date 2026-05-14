"""Bridge Skill 1 normalized student profiles ↔ Skill 2 graph student nodes.

Schema matches the normalized outputs under ``skill1_student_profiling/outputs/``:
``student_id``, ``grade``, ``major``, ``skills``, ``interests``,
``experience_summary``, ``availability``.

Embedding input convention (per Skill 1 README): concatenate
``major + skills + interests + experience_summary`` for semantic similarity.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def profile_text_for_embedding(
    major: str,
    skills: list[str],
    interests: list[str],
    experience_summary: str,
) -> str:
    skills_txt = ", ".join(skills)
    interests_txt = ", ".join(interests)
    parts = [
        f"Major: {major}",
        f"Skills: {skills_txt}",
        f"Interests: {interests_txt}",
        f"Experience summary: {experience_summary}",
    ]
    return "\n".join(parts)


def student_node_from_skill1(profile: dict[str, Any]) -> dict[str, Any]:
    """Map one Skill 1 JSON object to a graph ``student`` node (JSON-serializable)."""
    sid = str(profile["student_id"])
    skills = [str(x) for x in (profile.get("skills") or [])]
    interests = [str(x) for x in (profile.get("interests") or [])]
    major = str(profile.get("major") or "")
    exp = str(profile.get("experience_summary") or "")
    avail = str(profile.get("availability") or "")
    grade = str(profile.get("grade") or "")
    embed = profile.get("profile_text_for_embedding")
    if not embed:
        embed = profile_text_for_embedding(major, skills, interests, exp)
    return {
        "student_id": sid,
        "grade": grade,
        "major": major,
        "skills": skills,
        "interests": interests,
        "experience_summary": exp,
        "availability": avail,
        "profile_text_for_embedding": embed,
        "profile_source": "skill1_normalized_v1",
    }


def load_skill1_student_nodes(
    jsonl_path: Path,
    *,
    max_students: int,
    major_contains_any: tuple[str, ...] | None,
) -> list[dict[str, Any]]:
    """Load up to ``max_students`` profiles from Skill 1 JSONL (streaming)."""
    out: list[dict[str, Any]] = []
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            if len(out) >= max_students:
                break
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            if major_contains_any:
                maj = str(raw.get("major", "")).lower()
                if not any(s.lower() in maj for s in major_contains_any):
                    continue
            out.append(student_node_from_skill1(raw))
    return out


def save_student_standard_bundle(
    students: list[dict[str, Any]],
    out_path: Path,
    *,
    version: str = "1.0",
    build_meta: dict[str, Any] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "students": students,
        "build_meta": build_meta or {},
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
