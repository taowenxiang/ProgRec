"""Read Skill 1 normalized JSONL and build student indexes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_skill1_profiles(jsonl_path: str | Path) -> list[dict[str, Any]]:
    path = Path(jsonl_path)
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def normalize_skill1_profile(profile: dict[str, Any]) -> dict[str, Any]:
    skills = profile.get("skills") or []
    interests = profile.get("interests") or []
    if not isinstance(skills, list):
        skills = [str(skills)]
    if not isinstance(interests, list):
        interests = [str(interests)]
    skills_l = sorted({str(s).strip().lower() for s in skills if str(s).strip()})
    interests_l = sorted({str(s).strip().lower() for s in interests if str(s).strip()})
    avail = str(profile.get("availability") or "").strip().lower()
    if not avail:
        avail = "moderate"
    grade = str(profile.get("grade") or "").strip() or "unknown"
    sid = str(profile.get("student_id") or profile.get("id") or "").strip()
    return {
        "student_id": sid,
        "grade": grade,
        "major": str(profile.get("major") or "").strip(),
        "skills": skills_l,
        "interests": interests_l,
        "experience_summary": str(profile.get("experience_summary") or "").strip(),
        "availability": avail,
    }


def list_available_student_ids(students: list[dict[str, Any]], n: int = 10) -> list[str]:
    """First ``n`` distinct ``student_id`` values (stable order)."""
    out: list[str] = []
    seen: set[str] = set()
    for row in students:
        sid = str(row.get("student_id") or "").strip()
        if not sid or sid in seen:
            continue
        seen.add(sid)
        out.append(sid)
        if len(out) >= max(0, n):
            break
    return out


def build_student_index(profiles: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    idx: dict[str, dict[str, Any]] = {}
    for p in profiles:
        n = normalize_skill1_profile(p)
        sid = n.get("student_id")
        if sid:
            idx[sid] = n
    return idx


def split_target_and_candidates(
    profiles: list[dict[str, Any]],
    target_student_id: str,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    idx = build_student_index(profiles)
    target = idx.get(target_student_id)
    candidates = [idx[s] for s in idx if s != target_student_id]
    return target, candidates


def load_student_ids(student_ids_path: str | Path) -> list[str]:
    path = Path(student_ids_path)
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, dict) and "student_ids" in raw:
        return [str(x) for x in raw["student_ids"]]
    return []
