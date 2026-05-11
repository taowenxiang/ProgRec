from __future__ import annotations


def build_final_response(
    *, agent_profile: dict[str, object], skill5_result: dict[str, object], decision_trace: list[str]
) -> str:
    recs = dict(skill5_result.get("recommendations") or {})
    return "\n".join(
        [
            f"Goal: {agent_profile.get('goal', '')}",
            f"Top mentors: {len(list(recs.get('mentors') or []))}",
            f"Top projects: {len(list(recs.get('projects') or []))}",
            f"Top teammates: {len(list(recs.get('teammates') or []))}",
            "Decision Trace:",
            *[f"- {line}" for line in decision_trace],
        ]
    )
