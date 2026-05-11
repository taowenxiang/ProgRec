from __future__ import annotations

from sturec_agent.agent_schema import ClarificationQuestion, ExecutionPlan
from sturec_agent.prompts import CLARIFICATION_PROMPT


def build_execution_plan(agent_profile: dict[str, object], llm_client) -> ExecutionPlan:
    payload = llm_client.complete_json(f"{CLARIFICATION_PROMPT}\nProfile: {agent_profile}")
    questions = [
        ClarificationQuestion(key=str(item["key"]), question=str(item["question"]))
        for item in list(payload.get("clarification_questions") or [])[:2]
    ]
    tool_plan = dict(payload.get("tool_plan") or {})
    return ExecutionPlan(
        need_clarification=bool(payload.get("need_clarification")),
        clarification_questions=questions,
        run_skill3=bool(tool_plan.get("run_skill3", True)),
        run_skill4=bool(tool_plan.get("run_skill4", True)),
        run_skill5=bool(tool_plan.get("run_skill5", True)),
        rerun_needed=bool(payload.get("rerun_needed", False)),
        stop_reason=str(payload.get("stop_reason", "")),
    )
