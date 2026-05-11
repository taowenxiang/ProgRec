from __future__ import annotations


def judge_results(
    *, skill5_result: dict[str, object], strategy: dict[str, object], rerun_count: int
) -> dict[str, object]:
    recs = dict(skill5_result.get("recommendations") or {})
    mentors = list(recs.get("mentors") or [])
    projects = list(recs.get("projects") or [])
    teammates = list(recs.get("teammates") or [])
    reasons: list[str] = []
    if len(projects) < 3:
        reasons.append("project coverage too small")
    if len(mentors) < 3:
        reasons.append("mentor coverage too small")
    if len(teammates) < 3:
        reasons.append("teammate coverage too small")
    rerun_needed = bool(reasons) and rerun_count < int(strategy.get("max_reruns", 0))
    return {
        "rerun_needed": rerun_needed,
        "reasons": reasons,
        "stop_reason": "" if rerun_needed else "quality acceptable",
    }
