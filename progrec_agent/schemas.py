"""Lightweight JSON validation helpers for Agent-layer preflight and post-run checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Not found: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {p}: {exc}") from exc


def validate_student_profiles(path: str | Path) -> dict[str, Any]:
    """Validate Skill 2 ``student_profiles_standard.json`` shape."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {p}")
    students = data.get("students")
    if not isinstance(students, list):
        raise ValueError(f"Missing list 'students' at {p}")
    ids: list[str] = []
    for i, row in enumerate(students):
        if not isinstance(row, dict):
            raise ValueError(f"students[{i}] is not an object at {p}")
        sid = row.get("student_id")
        if sid is None or not str(sid).strip():
            raise ValueError(f"students[{i}] missing student_id at {p}")
        ids.append(str(sid).strip())
    return {
        "path": str(p.resolve()),
        "count": len(ids),
        "sample_ids": ids[:10],
        "all_student_ids": ids,
    }


def validate_skill3_output(path: str | Path) -> dict[str, Any]:
    """Validate Skill 3 mentor JSON (file or stdout-captured shape)."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Skill 3 output must be a JSON object at {p}")
    sid = str(data.get("student_id") or data.get("target_student_id") or "").strip()
    if not sid:
        raise ValueError(f"Skill 3 output missing student_id/target_student_id at {p}")
    mcs = data.get("mentor_candidates")
    if not isinstance(mcs, list):
        raise ValueError(f"Skill 3 output missing list mentor_candidates at {p}")
    for i, row in enumerate(mcs):
        if not isinstance(row, dict):
            raise ValueError(f"mentor_candidates[{i}] not an object at {p}")
        mid = row.get("mentor_id")
        if mid is None or not str(mid).strip():
            raise ValueError(f"mentor_candidates[{i}] missing mentor_id at {p}")
    return {"path": str(p.resolve()), "student_id": sid, "mentor_count": len(mcs)}


def validate_skill4_output(path: str | Path) -> dict[str, Any]:
    """Validate Skill 4 pipeline JSON."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Skill 4 output must be a JSON object at {p}")
    tid = str(data.get("target_student_id") or "").strip()
    if not tid:
        raise ValueError(f"Skill 4 output missing target_student_id at {p}")
    bundles = data.get("mentor_project_teammate_recommendations")
    if not isinstance(bundles, list):
        raise ValueError(f"Skill 4 output missing list mentor_project_teammate_recommendations at {p}")
    n_proj = 0
    n_mate = 0
    for b in bundles:
        if not isinstance(b, dict):
            continue
        n_proj += len(b.get("project_recommendations") or []) if isinstance(b.get("project_recommendations"), list) else 0
        n_mate += len(b.get("teammate_recommendations") or []) if isinstance(b.get("teammate_recommendations"), list) else 0
    return {
        "path": str(p.resolve()),
        "target_student_id": tid,
        "mentor_bundle_count": len(bundles),
        "total_project_recommendations": n_proj,
        "total_teammate_recommendations": n_mate,
    }


def get_skill3_student_id(path: str | Path) -> str:
    """Return the student identifier from Skill 3 JSON: ``student_id`` if set, else ``target_student_id``."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Skill 3 output must be a JSON object at {p}")
    sid = str(data.get("student_id") or "").strip()
    if sid:
        return sid
    tid = str(data.get("target_student_id") or "").strip()
    if tid:
        return tid
    raise ValueError(f"Skill 3 output missing student_id and target_student_id at {p}")


def get_skill4_student_id(path: str | Path) -> str:
    """Return ``target_student_id`` from Skill 4 pipeline JSON."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Skill 4 output must be a JSON object at {p}")
    tid = str(data.get("target_student_id") or "").strip()
    if not tid:
        raise ValueError(f"Skill 4 output missing target_student_id at {p}")
    return tid


def assert_agent_student_alignment(
    expected_student_id: str,
    skill3_path: str | Path | None,
    skill4_path: str | Path | None,
) -> None:
    """
    Hard gate before Skill 5: ``expected_student_id`` must match Skill 3 and Skill 4 on-disk JSON.

    Raises ``FileNotFoundError`` / ``ValueError`` (invalid JSON, missing ids, or mismatch).
    """
    exp = str(expected_student_id or "").strip()
    if not exp:
        raise ValueError("expected_student_id is empty")
    if skill3_path is None:
        raise ValueError("skill3_path is required for student alignment check")
    if skill4_path is None:
        raise ValueError("skill4_path is required for student alignment check")
    p3 = Path(skill3_path)
    p4 = Path(skill4_path)
    s3_id = get_skill3_student_id(p3)
    s4_id = get_skill4_student_id(p4)
    if s3_id == exp and s4_id == exp:
        return
    raise ValueError(
        "Student ID mismatch before Skill 5:\n"
        f"  expected_student_id: {exp!r}\n"
        f"  skill3 student_id: {s3_id!r} (from {p3.resolve()})\n"
        f"  skill4 target_student_id: {s4_id!r} (from {p4.resolve()})"
    )


def validate_skill5_output(path: str | Path) -> dict[str, Any]:
    """Validate Skill 5 ``joint_ranker`` output."""
    p = Path(path)
    data = load_json(p)
    if not isinstance(data, dict):
        raise ValueError(f"Skill 5 output must be a JSON object at {p}")
    summary = data.get("summary")
    recs = data.get("recommendations")
    if not isinstance(summary, dict) and not isinstance(recs, dict):
        raise ValueError(f"Skill 5 output missing 'summary' and 'recommendations' at {p}")
    out: dict[str, Any] = {"path": str(p.resolve())}
    if isinstance(summary, dict):
        out.update(
            {
                "total_mentor_candidates": summary.get("total_mentor_candidates"),
                "total_project_candidates": summary.get("total_project_candidates"),
                "total_teammate_candidates": summary.get("total_teammate_candidates"),
                "ranked_mentors": summary.get("ranked_mentors"),
                "ranked_projects": summary.get("ranked_projects"),
                "ranked_teammates": summary.get("ranked_teammates"),
            }
        )
    if isinstance(recs, dict):
        out["recommendation_keys"] = list(recs.keys())
    return out


def assert_same_student_id(
    skill3_path: Path | None,
    skill4_path: Path | None,
    expected_student_id: str,
) -> None:
    """Same contract as :func:`assert_agent_student_alignment` (delegates to it)."""
    assert_agent_student_alignment(expected_student_id, skill3_path, skill4_path)
