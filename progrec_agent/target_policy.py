from __future__ import annotations

from progrec_agent.chat_tool_registry import get_chat_tool


TARGET_KEYWORDS = {
    "mentor": ("mentor", "advisor", "professor", "supervisor"),
    "project": ("project", "research project", "opportunity"),
    "teammate": ("teammate", "team mate", "collaborator", "peer"),
}


def infer_user_targets(user_text: str) -> list[str]:
    text = user_text.lower()
    targets = [
        target
        for target, keywords in TARGET_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    return targets or ["mentor"]


def _accepted_targets(state) -> set[str]:
    accepted: set[str] = set()
    for item in list(state.suggested_next_actions or []):
        if isinstance(item, dict) and item.get("accepted") is True:
            target = str(item.get("target") or "")
            if target:
                accepted.add(target)
    return accepted


def is_tool_allowed_for_state(tool_name: str, state) -> bool:
    tool = get_chat_tool(tool_name)
    if tool.skill_id == "/student-profiling":
        return True
    allowed_targets = set(tool.allowed_targets)
    requested_targets = set(state.goal_targets or [])
    requested_targets.update(_accepted_targets(state))
    if not allowed_targets:
        return True
    return bool(allowed_targets & requested_targets)
