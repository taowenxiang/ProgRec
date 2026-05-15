from __future__ import annotations

from dataclasses import asdict

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
- Ask the user when required arguments are missing or ambiguous.
- Return only JSON with keys: action, message, tool_name, arguments, suggested_next_actions, reasoning_summary.
""".strip()


class AgentPlanner:
    def __init__(self, *, llm_client) -> None:
        self.llm_client = llm_client

    def plan_next_action(self, state, user_text: str) -> PlannerAction:
        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"Registered tools:\n{planner_tool_context()}\n\n"
            f"Dialog state:\n{asdict(state)}\n\n"
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
