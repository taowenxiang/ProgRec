from __future__ import annotations

from progrec_agent.response.replies import render_ranked_entity


def compose_mentor_matches_reply(
    *,
    preamble: str,
    mentor_result_payload: dict[str, object],
    suggested_next_actions: list[dict[str, object]],
) -> str:
    mentor_rows = list(dict(mentor_result_payload.get("skill3_result") or {}).get("mentor_candidates") or [])
    lines = [preamble.strip() or "I found mentor recommendations for you."]
    if mentor_rows:
        lines.append("")
        lines.append("Top mentor matches:")
        for rank, mentor in enumerate(mentor_rows[:3], start=1):
            lines.append(f"{rank}. {render_ranked_entity('mentor', rank, dict(mentor))}")
    next_steps = _compose_next_steps_suffix(suggested_next_actions)
    if next_steps:
        lines.append("")
        lines.append(next_steps)
    return "\n".join(lines)


def compose_fallback_reply(
    *,
    turn_type: str,
    tool_results_summary: dict[str, object],
    suggested_next_actions: list[dict[str, object]],
    next_question: str = "",
) -> str:
    if turn_type == "clarification" and next_question:
        return next_question

    if turn_type == "recommendation_result":
        mentor_count = int(tool_results_summary.get("mentor_count") or 0)
        project_count = int(tool_results_summary.get("project_count") or 0)
        teammate_count = int(tool_results_summary.get("teammate_count") or 0)
        if mentor_count:
            reply = f"I found {mentor_count} mentor recommendations for you."
        elif project_count:
            reply = f"I found {project_count} project recommendations for you."
        elif teammate_count:
            reply = f"I found {teammate_count} teammate recommendations for you."
        else:
            reply = "I finished the recommendation step."
        next_steps = _compose_next_steps_suffix(suggested_next_actions)
        if next_steps:
            return reply + " " + next_steps
        return reply

    return "I updated the recommendation context."


def _compose_next_steps_suffix(suggested_next_actions: list[dict[str, object]]) -> str:
    targets = [str(item.get("target") or "") for item in suggested_next_actions]
    if "project" in targets and "teammate" in targets:
        return "Would you like me to look for related projects or teammates next?"
    if "project" in targets:
        return "Would you like me to look for related projects next?"
    if "teammate" in targets:
        return "Would you like me to look for teammates next?"
    return ""
