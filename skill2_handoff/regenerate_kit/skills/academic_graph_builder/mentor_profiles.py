"""Mentor profile loading, merge with CSV seeds, and standardized export."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _auto_embedding_text(
    research_areas: list[str],
    keywords: list[str],
    profile_text: str,
    name: str,
    department: str,
) -> str:
    parts = [
        name,
        department,
        "Research areas: " + "; ".join(research_areas),
        "Keywords: " + "; ".join(keywords),
        profile_text.strip(),
    ]
    return "\n".join(p for p in parts if p)


def load_mentor_profiles_json(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    items = raw.get("mentors") or raw.get("items") or []
    by_id: dict[str, dict[str, Any]] = {}
    for row in items:
        mid = row["mentor_id"]
        by_id[mid] = dict(row)
    return by_id


def available_projects_from_projects_table(
    projects_rows: list[dict[str, str]],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for r in projects_rows:
        out[r["mentor_id"]].append(r["project_id"])
    for k in out:
        out[k] = sorted(out[k])
    return dict(out)


def merge_mentor_records(
    csv_rows: list[dict[str, str]],
    profiles_by_id: dict[str, dict[str, Any]],
    projects_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Merge mentors.csv + mentor_profiles.json + derived ``available_projects``."""
    proj_map = available_projects_from_projects_table(projects_rows)
    merged: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in csv_rows:
        mid = row["mentor_id"]
        prof = profiles_by_id.get(mid)
        if prof is None:
            warnings.append(f"缺少 mentor_profiles.json 条目: {mid}")
            continue
        research_areas = list(prof.get("research_areas") or [])
        keywords = list(prof.get("keywords") or [])
        profile_text = str(prof.get("profile_text") or "").strip()
        required_skills = list(prof.get("required_skills") or [])
        preferred_background = str(prof.get("preferred_background") or "").strip()
        exp_summary = str(prof.get("experience_summary") or "").strip()
        advising_style = str(prof.get("advising_style") or "").strip()
        weekly_time_expectation = str(prof.get("weekly_time_expectation") or "").strip()
        lab_focus = str(prof.get("lab_focus") or "").strip()

        embed = prof.get("profile_text_for_embedding")
        if not embed:
            embed = _auto_embedding_text(
                research_areas,
                keywords,
                profile_text,
                row["name"],
                row["department"],
            )

        available = prof.get("available_projects")
        if available is None:
            available = proj_map.get(mid, [])
        else:
            available = list(available)

        record: dict[str, Any] = {
            "mentor_id": mid,
            "name": row["name"],
            "department": row["department"],
            "h_index": int(row["h_index"]),
            "research_areas": research_areas,
            "keywords": keywords,
            "profile_text": profile_text,
            "required_skills": required_skills,
            "preferred_background": preferred_background,
            "available_projects": available,
            "experience_summary": exp_summary,
            "advising_style": advising_style,
            "weekly_time_expectation": weekly_time_expectation,
            "lab_focus": lab_focus,
            "profile_text_for_embedding": embed.strip(),
        }
        merged.append(record)

    seen_csv = {r["mentor_id"] for r in csv_rows}
    for mid in profiles_by_id:
        if mid not in seen_csv:
            warnings.append(f"mentor_profiles.json 存在多余 mentor_id（未在 mentors.csv）: {mid}")
    return merged, warnings


def save_mentor_standard_bundle(
    mentors: list[dict[str, Any]],
    out_path: Path,
    *,
    version: str = "1.0",
    build_meta: dict[str, Any] | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": version,
        "mentors": mentors,
        "build_meta": build_meta or {},
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
