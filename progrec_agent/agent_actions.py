from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ACTIONS = {
    "ask_user",
    "call_tool",
    "answer_from_context",
    "suggest_next_steps",
    "stop",
}


@dataclass
class PlannerAction:
    action: str
    message: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    suggested_next_actions: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""


def parse_planner_action(payload: dict[str, Any], *, allowed_tools: set[str]) -> PlannerAction:
    action = str(payload.get("action") or "").strip()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown planner action {action!r}. Expected one of {sorted(VALID_ACTIONS)}.")

    tool_name = str(payload.get("tool_name") or "").strip()
    if action == "call_tool" and tool_name not in allowed_tools:
        raise ValueError(f"Unknown chat tool {tool_name!r}. Expected one of {sorted(allowed_tools)}.")

    raw_arguments = payload.get("arguments") or {}
    if not isinstance(raw_arguments, dict):
        raise ValueError("Planner action arguments must be a JSON object.")

    raw_suggestions = payload.get("suggested_next_actions") or []
    if not isinstance(raw_suggestions, list):
        raise ValueError("suggested_next_actions must be a JSON array.")

    return PlannerAction(
        action=action,
        message=str(payload.get("message") or "").strip(),
        tool_name=tool_name,
        arguments=dict(raw_arguments),
        suggested_next_actions=[item for item in raw_suggestions if isinstance(item, dict)],
        reasoning_summary=str(payload.get("reasoning_summary") or "").strip(),
    )
