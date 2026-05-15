from __future__ import annotations

import json

from progrec_agent.agent_actions import PlannerAction, parse_planner_action
from progrec_agent.chat_tool_registry import allowed_tool_names, planner_tool_context


PLANNER_PROMPT = """
You are the semi-autonomous planner for ProgRec chat.
Choose exactly one next action as strict JSON.

Allowed actions:
- ask_user: ask one natural question when required information is missing.
- call_tool: call one registered tool.
- answer_from_context: answer using existing state or tool results.
- suggest_next_steps: offer optional follow-up skills without executing them.
- stop: finish the turn.

Rules:
- Satisfy the user's current target first.
- Do not run extra recommendation categories.
- Do not call project, teammate, or social ranking tools unless the user requested that target or accepted a suggestion.
- Do not invent student IDs, profile facts, mentor facts, or tool outputs.
- Prefer ask_user when you only know a broad topic and still need real profile details.
- Ask the user when required arguments are missing or ambiguous.
- When calling /student-profiling.build_temporary_profile or /student-profiling.update_profile_context, arguments.profile_context must be a JSON object, never a raw string.
- If the user just answered a profile question, reuse the profile_context already stored in dialog state instead of repeating the same clarification.
- Avoid repeating the exact same clarification after the user already provided an answer.
- When action is ask_user, also return pending_slot and expected_answer_shape.
- Use pending_slot "profile_context" for free-form background/profile clarifications.
- Return only JSON with keys: action, message, tool_name, arguments, suggested_next_actions, reasoning_summary, pending_slot, expected_answer_shape.
""".strip()


class AgentPlanner:
    def __init__(self, *, llm_client) -> None:
        self.llm_client = llm_client

    def plan_next_action(self, state, user_text: str) -> PlannerAction:
        state_snapshot = _planner_state_snapshot(state)
        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"Registered tools:\n{planner_tool_context()}\n\n"
            f"Compact dialog state:\n{json.dumps(state_snapshot, ensure_ascii=False)}\n\n"
            f"Latest user message:\n{user_text}"
        )
        try:
            payload = self.llm_client.complete_json(prompt)
            return parse_planner_action(dict(payload), allowed_tools=allowed_tool_names())
        except Exception:
            return PlannerAction(
                action="ask_user",
                message="Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                reasoning_summary="Planner action was invalid or unavailable.",
            )


def _planner_state_snapshot(state) -> dict[str, object]:
    execution_context = state.execution_context
    pending_question = None
    if state.pending_question is not None:
        pending_question = {
            "slot_name": state.pending_question.slot_name,
            "question": state.pending_question.question,
            "expected_answer_shape": state.pending_question.expected_answer_shape,
        }

    return {
        "task": state.task,
        "goal": state.goal,
        "active_goal": state.active_goal,
        "goal_targets": list(state.goal_targets),
        "profile_context": dict(state.profile_context),
        "pending_question": pending_question,
        "clarification_turn_count": state.clarification_turn_count,
        "resolved_slots": dict(state.resolved_slots),
        "tool_results_summary": dict(state.tool_results_summary),
        "last_turn_type": execution_context.last_turn_type,
        "next_question": execution_context.next_question,
        "latest_result_refs": dict(getattr(execution_context, "latest_result_refs", {}) or {}),
        "active_result_ref": str(getattr(execution_context, "active_result_ref", "") or ""),
        "last_shown_entities": dict(getattr(execution_context, "last_shown_entities", {}) or {}),
        "recent_planner_actions": [
            {
                "action": str(item.get("action") or ""),
                "tool_name": str(item.get("tool_name") or ""),
                "message": str(item.get("message") or ""),
            }
            for item in list(state.planner_actions)[-2:]
        ],
        "recent_skill_trace": [
            {
                "skill_id": str(item.get("skill_id") or ""),
                "tool_name": str(item.get("tool_name") or ""),
                "status": str(item.get("status") or ""),
                "summary": str(item.get("summary") or ""),
            }
            for item in list(state.skill_trace)[-3:]
        ],
        "has_result": bool(execution_context.result_handle or getattr(execution_context, "latest_result_refs", {})),
    }
