from __future__ import annotations

from progrec_agent.planning.actions import ExecutionPlanV2


def build_execution_plan(state) -> ExecutionPlanV2:
    if state.task == "out_of_scope":
        return ExecutionPlanV2(action="refuse_out_of_scope")
    if state.task == "answer_meta_question":
        return ExecutionPlanV2(action="answer_meta_question")
    if (
        state.task in {"inspect_recommendation", "explain_recommendation"}
        and not state.execution_context.last_result
        and not state.execution_context.result_handle
    ):
        return ExecutionPlanV2(action="await_clarification")
    if state.missing_slots:
        return ExecutionPlanV2(action="await_clarification")
    if state.task == "recommend_existing_student":
        return ExecutionPlanV2(
            action="run_existing_profile_recommendation",
            arguments={
                "student_id": state.resolved_slots["student_id"],
                "mode": state.resolved_slots["mode"],
                "top_k": state.resolved_slots.get("top_k", 5),
            },
        )
    if state.task == "recommend_temporary_profile":
        return ExecutionPlanV2(
            action="run_temporary_profile_recommendation",
            arguments={"profile": dict(state.resolved_slots), "top_k": state.resolved_slots.get("top_k", 5)},
        )
    if state.task == "inspect_recommendation":
        return ExecutionPlanV2(
            action="inspect_ranked_entity",
            arguments={
                "result_handle": state.execution_context.result_handle,
                "entity_type": state.resolved_slots.get("entity_type", "mentor"),
                "rank": state.resolved_slots.get("rank", 1),
            },
        )
    if state.task == "explain_recommendation":
        return ExecutionPlanV2(
            action="explain_ranked_entity",
            arguments={
                "entity_type": state.resolved_slots.get("entity_type", "mentor"),
                "rank": state.resolved_slots.get("rank", 1),
            },
        )
    if state.task == "validate_resources":
        return ExecutionPlanV2(action="validate_resources", arguments={"mode": state.resolved_slots["mode"]})
    return ExecutionPlanV2(action="refuse_out_of_scope")
