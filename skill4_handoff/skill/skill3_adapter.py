"""Mentor candidates from Skill 3 JSON, mock list, or Skill 2 graph fallback."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill.skill2_adapter import extract_all_mentors_from_graph

# Envelope keys whose value is a list of mentor-like dicts (Skill 3 CLI and variants).
_MENTOR_LIST_KEYS: tuple[str, ...] = (
    "mentor_candidates",
    "candidates",
    "recommendations",
    "ranked_mentors",
    "top_mentors",
    "results",
    "mentor_recommendations",
    "mentors",
)


def _coerce_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_mentor_list(raw: Any) -> list[Any] | None:
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict):
        return None
    for key in _MENTOR_LIST_KEYS:
        val = raw.get(key)
        if isinstance(val, list) and val:
            if key == "mentors":
                if not all(isinstance(x, dict) for x in val):
                    continue
                if not any(str(x.get("mentor_id") or x.get("id") or "").strip() for x in val):
                    continue
            return val
    inner = raw.get("data")
    if isinstance(inner, dict):
        nested = _extract_mentor_list(inner)
        if nested is not None:
            return nested
    inner = raw.get("output")
    if isinstance(inner, dict):
        nested = _extract_mentor_list(inner)
        if nested is not None:
            return nested
    return None


def _normalize_mentor_row(row: dict[str, Any], *, rank: int) -> dict[str, Any] | None:
    mid = str(row.get("mentor_id") or row.get("id") or row.get("mentorId") or "").strip()
    if not mid:
        return None
    topic = _coerce_float(row.get("topic_score"), 0.0)
    graph = _coerce_float(row.get("graph_score"), 0.0)
    activity = _coerce_float(row.get("activity_score"), 0.0)
    centrality = _coerce_float(
        row.get("centrality_score") if row.get("centrality_score") is not None else row.get("centrality"),
        0.0,
    )
    proximity = _coerce_float(row.get("network_proximity"), 0.0)
    final = row.get("final_score")
    if final is None:
        final = row.get("score")
    if final is None:
        final = row.get("overall_score")
    final_f = _coerce_float(final, 0.0)

    reasons: list[str] = []
    raw_reasons = row.get("reasons")
    if isinstance(raw_reasons, list):
        reasons = [str(x) for x in raw_reasons if str(x).strip()]
    elif isinstance(raw_reasons, str) and raw_reasons.strip():
        reasons = [raw_reasons.strip()]
    reason_one = row.get("reason")
    if isinstance(reason_one, str) and reason_one.strip() and not reasons:
        reasons = [reason_one.strip()]

    community = row.get("community_id")
    if community is not None:
        community = str(community)

    name = row.get("mentor_name") or row.get("name") or ""
    name_s = str(name).strip()

    out: dict[str, Any] = {
        "mentor_id": mid,
        "topic_score": topic,
        "graph_score": graph,
        "community_id": community,
        "final_score": final_f,
        "activity_score": activity,
        "centrality_score": centrality,
        "network_proximity": proximity,
        "skill3_rank": rank,
    }
    if name_s:
        out["mentor_name"] = name_s
    if reasons:
        out["reasons"] = reasons

    matched_topics = row.get("matched_topics")
    if isinstance(matched_topics, list) and matched_topics:
        out["matched_topics"] = [str(x) for x in matched_topics]

    mprof = row.get("mentor_profile")
    if isinstance(mprof, dict) and mprof:
        out["mentor_profile"] = mprof

    explicit_rank = row.get("rank")
    if explicit_rank is not None:
        try:
            out["rank"] = int(explicit_rank)
        except (TypeError, ValueError):
            pass

    return out


def parse_skill3_mentor_json(raw: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse arbitrary JSON into normalized mentor rows plus envelope metadata."""
    meta: dict[str, Any] = {}
    if isinstance(raw, dict):
        ts = raw.get("target_student_id")
        if ts is not None and str(ts).strip():
            meta["skill3_declared_target_student_id"] = str(ts).strip()
            meta["target_student_id"] = meta["skill3_declared_target_student_id"]
        sid = raw.get("student_id")
        if sid is not None and str(sid).strip():
            meta["skill3_declared_student_id"] = str(sid).strip()
            if "target_student_id" not in meta:
                meta["target_student_id"] = meta["skill3_declared_student_id"]
        for key in ("graph_status", "graph_notice"):
            if raw.get(key) is not None:
                meta[key] = raw[key]
    items = _extract_mentor_list(raw)
    if not items:
        return [], meta
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        norm = _normalize_mentor_row(item, rank=i)
        if norm:
            out.append(norm)
    return out, meta


def load_skill3_mentor_candidates(path: str | Path | None) -> list[dict[str, Any]] | None:
    """Load and normalize mentor candidates from a Skill 3 (or compatible) JSON file.

    Accepts:
    - A JSON array of mentor objects.
    - A JSON object with ``mentor_candidates`` (Skill 3 ``run_skill3.py`` stdout shape),
      or ``candidates`` / ``recommendations`` / other known list keys.
    """
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    rows, _meta = parse_skill3_mentor_json(raw)
    return rows or None


def read_skill3_mentor_payload(path: str | Path | None) -> dict[str, Any] | None:
    """Load file and return ``candidates`` plus envelope fields for validation and data_sources."""
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    rows, meta = parse_skill3_mentor_json(raw)
    if not rows:
        return None
    return {"candidates": rows, **meta}


def load_mentor_candidates(path: str | Path | None) -> list[dict[str, Any]] | None:
    """Backward-compatible alias for :func:`load_skill3_mentor_candidates`."""
    return load_skill3_mentor_candidates(path)


def fallback_mentor_candidates_from_skill2(
    graph: dict[str, Any] | None,
    mentors: list[dict[str, Any]] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    rows = mentors if mentors is not None else (
        extract_all_mentors_from_graph(graph) if graph else []
    )
    out: list[dict[str, Any]] = []
    for i, m in enumerate(rows[: max(0, top_k)], start=1):
        mid = str(m.get("mentor_id") or "").strip()
        if not mid:
            continue
        out.append(
            {
                "mentor_id": mid,
                "topic_score": 0.0,
                "graph_score": 0.0,
                "community_id": None,
                "final_score": 1.0,
                "activity_score": 0.0,
                "centrality_score": 0.0,
                "network_proximity": 0.0,
                "skill3_rank": i,
            }
        )
    return out
