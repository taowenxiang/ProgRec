from __future__ import annotations

from typing import Any


def trace_entry(
    *,
    skill_id: str,
    tool_name: str,
    status: str,
    summary: str,
    inputs: dict[str, object] | None = None,
    outputs: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "skill_id": skill_id,
        "tool_name": tool_name,
        "status": status,
        "summary": summary,
        "inputs": dict(inputs or {}),
        "outputs": dict(outputs or {}),
    }


def recommendation_trace(result: dict[str, Any], *, tool_name: str = "recommend_full_pipeline") -> list[dict[str, object]]:
    student_profile = dict(result.get("student_profile") or {})
    skill3 = dict(result.get("skill3_result") or {})
    skill5 = dict(result.get("skill5_result") or {})
    recs = dict(skill5.get("recommendations") or {})
    student_id = str(student_profile.get("student_id") or skill3.get("student_id") or "")
    return [
        trace_entry(
            skill_id="/student-profiling",
            tool_name=tool_name,
            status="succeeded",
            summary="Resolved the student profile used for the recommendation request.",
            inputs={"profile_source": student_profile.get("student_id", "")},
            outputs={"student_id": student_id},
        ),
        trace_entry(
            skill_id="/mentor-discovery",
            tool_name=tool_name,
            status="succeeded",
            summary="Ranked mentor candidates for the student context.",
            inputs={"student_id": student_id},
            outputs={"mentor_count": len(list(skill3.get("mentor_candidates") or recs.get("mentors") or []))},
        ),
        trace_entry(
            skill_id="/project-teammate-discovery",
            tool_name=tool_name,
            status="succeeded",
            summary="Expanded mentor matches into project and teammate recommendations.",
            inputs={"student_id": student_id},
            outputs={
                "project_count": len(list(recs.get("projects") or [])),
                "teammate_count": len(list(recs.get("teammates") or [])),
            },
        ),
        trace_entry(
            skill_id="/social-ranking",
            tool_name=tool_name,
            status="succeeded",
            summary="Produced the final ranked recommendation package.",
            inputs={"student_id": student_id},
            outputs={
                "mentor_count": len(list(recs.get("mentors") or [])),
                "project_count": len(list(recs.get("projects") or [])),
                "teammate_count": len(list(recs.get("teammates") or [])),
            },
        ),
    ]
