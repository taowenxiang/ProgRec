from __future__ import annotations

from pathlib import Path
from typing import Any


def make_json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]
    return value


def summarize_pipeline_result(result: dict[str, object]) -> dict[str, int]:
    recommendations = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    return {
        "mentor_count": len(list(recommendations.get("mentors") or [])),
        "project_count": len(list(recommendations.get("projects") or [])),
        "teammate_count": len(list(recommendations.get("teammates") or [])),
    }


def normalize_result_package(result: dict[str, object]) -> dict[str, dict[str, object]]:
    recommendations = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    if not recommendations:
        recommendations = dict(result.get("recommendations") or {})
    return {
        "mentors": _normalize_section("mentor", recommendations.get("mentors")),
        "projects": _normalize_section("project", recommendations.get("projects")),
        "teammates": _normalize_section("teammate", recommendations.get("teammates")),
    }


def _normalize_section(label: str, items_payload: object) -> dict[str, object]:
    items = list(items_payload or [])
    noun = f"{label} recommendation" if len(items) == 1 else f"{label} recommendations"
    return {
        "items": items,
        "count": len(items),
        "summary": f"{len(items)} {noun}",
    }
