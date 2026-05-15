from __future__ import annotations


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
        targets = [str(item.get("target") or "") for item in suggested_next_actions]
        if "project" in targets and "teammate" in targets:
            return reply + " Would you like me to look for related projects or teammates next?"
        if "project" in targets:
            return reply + " Would you like me to look for related projects next?"
        if "teammate" in targets:
            return reply + " Would you like me to look for teammates next?"
        return reply

    return "I updated the recommendation context."
