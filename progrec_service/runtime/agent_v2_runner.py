from __future__ import annotations

import tempfile
from dataclasses import asdict
from dataclasses import fields
from pathlib import Path

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState, ExecutionContext, PendingQuestion
from progrec_agent.llm_client import LLMClient, LLMConfig
from progrec_service.runtime.result_mapper import make_json_safe, normalize_result_package, summarize_pipeline_result


def _recommendation_skill_usage(state: DialogState) -> list[dict[str, str]]:
    if not state.execution_context.result_handle:
        return []
    return [
        {
            "skill_id": "/student-profiling",
            "status": "succeeded",
            "summary": "Resolved the student profile used for the recommendation request.",
        },
        {
            "skill_id": "/academic-graph",
            "status": "succeeded",
            "summary": "Loaded the academic graph and aligned resource bundle.",
        },
        {
            "skill_id": "/mentor-discovery",
            "status": "succeeded",
            "summary": "Ranked mentor candidates for the student context.",
        },
        {
            "skill_id": "/project-teammate-discovery",
            "status": "succeeded",
            "summary": "Expanded mentor matches into project and teammate recommendations.",
        },
        {
            "skill_id": "/social-ranking",
            "status": "succeeded",
            "summary": "Produced the final ranked recommendation package.",
        },
    ]


def _dialog_state_from_payload(payload: dict[str, object]) -> DialogState:
    pending_question_payload = payload.get("pending_question")
    execution_context_payload = payload.get("execution_context")
    pending_question = None
    if isinstance(pending_question_payload, dict):
        pending_question = PendingQuestion(**pending_question_payload)
    execution_context = ExecutionContext()
    if isinstance(execution_context_payload, dict):
        allowed_context_keys = {item.name for item in fields(ExecutionContext)}
        execution_context = ExecutionContext(
            **{key: value for key, value in execution_context_payload.items() if key in allowed_context_keys}
        )
    return DialogState(
        task=str(payload.get("task", "")),
        goal=str(payload.get("goal", "")),
        active_goal=str(payload.get("active_goal", "")),
        goal_targets=list(payload.get("goal_targets", []) or []),
        profile_context=dict(payload.get("profile_context", {}) or {}),
        planner_actions=list(payload.get("planner_actions", []) or []),
        suggested_next_actions=list(payload.get("suggested_next_actions", []) or []),
        tool_results_summary=dict(payload.get("tool_results_summary", {}) or {}),
        resolved_slots=dict(payload.get("resolved_slots", {}) or {}),
        candidate_slots=dict(payload.get("candidate_slots", {}) or {}),
        required_slots=list(payload.get("required_slots", []) or []),
        missing_slots=list(payload.get("missing_slots", []) or []),
        pending_question=pending_question,
        conflicts=list(payload.get("conflicts", []) or []),
        execution_context=execution_context,
        clarification_turn_count=int(payload.get("clarification_turn_count", 0) or 0),
        last_user_turn=str(payload.get("last_user_turn", "")),
        last_agent_turn=str(payload.get("last_agent_turn", "")),
        skill_trace=list(payload.get("skill_trace", []) or []),
        last_skill_plan=dict(payload.get("last_skill_plan", {}) or {}),
        last_result_summary=str(payload.get("last_result_summary", "")),
    )


def _structured_result_from_state(state: DialogState) -> dict[str, object]:
    turn_type = state.execution_context.last_turn_type or (
        "recommendation_result" if state.execution_context.result_handle else "clarification"
    )
    structured: dict[str, object] = {
        "turn_type": turn_type,
        "intent": state.active_goal or state.task,
        "active_goal": state.active_goal,
        "goal_targets": list(state.goal_targets),
        "missing_slots": list(state.missing_slots),
        "next_question": state.execution_context.next_question,
        "last_result_handle": state.execution_context.result_handle,
        "latest_result_refs": dict(state.execution_context.latest_result_refs),
        "active_result_ref": state.execution_context.active_result_ref,
        "last_shown_entities": dict(state.execution_context.last_shown_entities),
        "skill_usage": list(state.skill_trace or []),
        "planner_actions": list(state.planner_actions or []),
        "suggested_next_actions": list(state.suggested_next_actions or []),
        "tool_results_summary": dict(state.tool_results_summary or {}),
    }
    if turn_type == "recommendation_result" and state.execution_context.last_result:
        last_result = dict(state.execution_context.last_result)
        if "skill5_result" in last_result:
            structured["summary"] = summarize_pipeline_result(last_result)
            structured["recommendation_result"] = normalize_result_package(last_result)
        else:
            structured["summary"] = dict(state.tool_results_summary)
            structured["recommendation_result"] = make_json_safe(last_result)
    return make_json_safe(structured)


def run_agent_turn(*, repo_root: Path, dialog_state_payload: dict[str, object], runtime_context, user_text: str) -> dict[str, object]:
    llm_client = LLMClient(
        LLMConfig(
            model=runtime_context.model,
            api_key=runtime_context.api_key,
            endpoint=runtime_context.base_url,
        )
    )
    state = _dialog_state_from_payload(dialog_state_payload)
    with tempfile.TemporaryDirectory(prefix="progrec_agent_turn_") as tmp_dir:
        agent = AgentCoreV2(
            repo_root=repo_root,
            temp_dir=Path(tmp_dir),
            llm_client=llm_client,
        )
        reply_text, next_state = agent.handle_message(state, user_text)
    return {
        "reply_text": reply_text,
        "structured_result": _structured_result_from_state(next_state),
        "dialog_state_payload": make_json_safe(asdict(next_state)),
    }
