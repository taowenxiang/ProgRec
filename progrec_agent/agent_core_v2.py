from __future__ import annotations

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.merge import merge_skill_frame
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.parser import parse_skill_aware_user_message
from progrec_agent.planning.planner_v2 import build_execution_plan
from progrec_agent.policy.clarification import QUESTION_BANK, choose_next_question
from progrec_agent.policy.readiness import compute_readiness
from progrec_agent.response.replies import (
    render_clarification,
    render_execution_blocker,
    render_meta_answer,
    render_ranked_entity,
    render_recommendation_summary,
    render_scope_refusal,
)
from progrec_agent.runtime import inspection_runtime as inspection_runtime_module
from progrec_agent.runtime import recommendation_runtime as recommendation_runtime_module
from progrec_agent.runtime import validation_runtime as validation_runtime_module
from progrec_agent.runtime.skill_trace import recommendation_trace, trace_entry
from progrec_agent.skill_catalog import build_skill_catalog

TOPIC_SLOT_ALIASES = ("research_topic", "topic", "research_area", "area", "field")


class AgentCoreV2:
    def __init__(
        self,
        *,
        repo_root,
        temp_dir,
        llm_client,
        recommendation_runtime=None,
        inspection_runtime=None,
        validation_runtime=None,
    ) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.llm_client = llm_client
        self.recommendation_runtime = recommendation_runtime or recommendation_runtime_module
        self.inspection_runtime = inspection_runtime or inspection_runtime_module
        self.validation_runtime = validation_runtime or validation_runtime_module
        self.skill_catalog = build_skill_catalog(self.repo_root)

    def _make_pending_question(self, slot_name: str) -> PendingQuestion:
        return PendingQuestion(
            slot_name=slot_name,
            question=QUESTION_BANK[slot_name],
            expected_answer_shape="free_text",
        )

    def _normalize_recommendation_state(self, state: DialogState) -> DialogState:
        if "research_topic" not in state.resolved_slots:
            for alias in TOPIC_SLOT_ALIASES:
                if alias in state.resolved_slots:
                    state.resolved_slots["research_topic"] = state.resolved_slots[alias]
                    break

        profile_source = str(state.resolved_slots.get("profile_source") or "").strip().lower()
        if "student_id" in state.resolved_slots or profile_source in {"existing_profile", "existing"}:
            state.task = "recommend_existing_student"
        elif (
            profile_source in {"temporary_profile", "temporary", "use my description"}
            or any(slot in state.resolved_slots for slot in ["research_topic", "program_type", "experience_level"])
        ):
            state.task = "recommend_temporary_profile"
        return state

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        if working.pending_question is not None:
            working = apply_pending_answer(working, user_text)
        else:
            frame = parse_skill_aware_user_message(
                user_text,
                dialog_state=working,
                llm_client=self.llm_client,
                skill_catalog=self.skill_catalog,
            )
            working = merge_skill_frame(working, frame)
        if working.task in {"recommendation_request", "recommend_temporary_profile", "recommend_existing_student"}:
            working = self._normalize_recommendation_state(working)
        if not working.task:
            working.task = "recommend_temporary_profile"
        working.last_user_turn = user_text
        working = compute_readiness(working)
        next_question = choose_next_question(working)
        if next_question is not None:
            working.pending_question = next_question
            working.execution_context.last_turn_type = "clarification"
            working.execution_context.next_question = next_question.question
            working.last_agent_turn = next_question.question
            return render_clarification(next_question), working
        plan = build_execution_plan(working)
        if plan.action == "await_clarification":
            blocker = render_execution_blocker(working)
            working.execution_context.last_turn_type = "clarification"
            working.execution_context.next_question = blocker
            working.last_agent_turn = blocker
            return blocker, working
        if plan.action == "run_existing_profile_recommendation":
            result = self.recommendation_runtime.run_recommendation_for_student_id(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                student_id=str(plan.arguments["student_id"]),
                mode=str(plan.arguments["mode"]),
                top_k=int(plan.arguments["top_k"]),
            )
            working.execution_context.result_handle = "latest"
            working.execution_context.last_result = result
            working.execution_context.last_turn_type = "recommendation_result"
            working.execution_context.next_question = ""
            working.skill_trace = recommendation_trace(result)
            working.last_agent_turn = render_recommendation_summary(result)
            return working.last_agent_turn, working
        if plan.action == "run_temporary_profile_recommendation":
            result = self.recommendation_runtime.run_recommendation_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(plan.arguments["profile"]),
                top_k=int(plan.arguments["top_k"]),
            )
            working.execution_context.result_handle = "latest"
            working.execution_context.last_result = result
            working.execution_context.last_turn_type = "recommendation_result"
            working.execution_context.next_question = ""
            working.skill_trace = recommendation_trace(result)
            working.last_agent_turn = render_recommendation_summary(result)
            return working.last_agent_turn, working
        if plan.action == "inspect_ranked_entity":
            if not working.execution_context.result_handle or not working.execution_context.last_result:
                message = "I need a recommendation result before I can inspect a ranked mentor, project, or teammate."
                working.execution_context.last_turn_type = "clarification"
                working.execution_context.next_question = message
                working.last_agent_turn = message
                return message, working
            entity_type = str(plan.arguments["entity_type"])
            rank = int(plan.arguments["rank"])
            result = dict(working.execution_context.last_result)
            entity = self.inspection_runtime.get_ranked_entity(
                skill5_result=dict(result.get("skill5_result") or {}),
                entity_type=entity_type,
                rank=rank,
            )
            message = render_ranked_entity(entity_type, rank, entity)
            working.execution_context.last_turn_type = "inspection"
            working.execution_context.next_question = ""
            working.last_agent_turn = message
            return message, working
        if plan.action == "explain_ranked_entity":
            entity_type = str(plan.arguments["entity_type"])
            rank = int(plan.arguments["rank"])
            result = dict(working.execution_context.last_result)
            entity = self.inspection_runtime.get_ranked_entity(
                skill5_result=dict(result.get("skill5_result") or {}),
                entity_type=entity_type,
                rank=rank,
            )
            message = render_ranked_entity(entity_type, rank, entity)
            working.execution_context.last_turn_type = "inspection"
            working.execution_context.next_question = ""
            working.last_agent_turn = message
            return message, working
        if plan.action == "validate_resources":
            payload = self.validation_runtime.validate_resources(
                repo_root=self.repo_root,
                mode=str(plan.arguments["mode"]),
            )
            message = f"I validated the resources for {payload['mode']} mode."
            working.execution_context.last_turn_type = "resource_validation"
            working.execution_context.next_question = ""
            working.skill_trace = [
                trace_entry(
                    skill_id="/academic-graph",
                    tool_name="validate_resources",
                    status="succeeded",
                    summary=f"Validated resources for {payload['mode']} mode.",
                    inputs={"mode": payload["mode"]},
                    outputs=dict(payload),
                )
            ]
            working.last_agent_turn = message
            return message, working
        if plan.action == "answer_meta_question":
            message = render_meta_answer(working)
            working.execution_context.last_turn_type = "meta_answer"
            working.execution_context.next_question = ""
            working.last_agent_turn = message
            return message, working
        message = render_scope_refusal()
        working.execution_context.last_turn_type = "refusal"
        working.execution_context.next_question = ""
        working.last_agent_turn = message
        return message, working
