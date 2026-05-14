from __future__ import annotations


def summarize_pipeline_result(result: dict[str, object]) -> dict[str, int]:
    recommendations = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    return {
        "mentor_count": len(list(recommendations.get("mentors") or [])),
        "project_count": len(list(recommendations.get("projects") or [])),
        "teammate_count": len(list(recommendations.get("teammates") or [])),
    }
