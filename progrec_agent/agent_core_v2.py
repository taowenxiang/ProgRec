from __future__ import annotations

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.merge import merge_intent_frame
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.parser import parse_user_message
from progrec_agent.planning.planner_v2 import build_execution_plan
from progrec_agent.policy.clarification import QUESTION_BANK, choose_next_question
from progrec_agent.policy.readiness import compute_readiness
from progrec_agent.response.replies import render_clarification, render_execution_blocker


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
        self.recommendation_runtime = recommendation_runtime
        self.inspection_runtime = inspection_runtime
        self.validation_runtime = validation_runtime

    def _make_pending_question(self, slot_name: str) -> PendingQuestion:
        return PendingQuestion(
            slot_name=slot_name,
            question=QUESTION_BANK[slot_name],
            expected_answer_shape="free_text",
        )

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        if working.pending_question is not None:
            working = apply_pending_answer(working, user_text)
        else:
            frame = parse_user_message(user_text, dialog_state=working, llm_client=self.llm_client)
            working = merge_intent_frame(working, frame)
            if "student_id" in working.resolved_slots:
                working.task = "recommend_existing_student"
            elif any(k in working.resolved_slots for k in ["research_topic", "program_type", "experience_level"]):
                working.task = "recommend_temporary_profile"
        if not working.task:
            working.task = "recommend_temporary_profile"
        working.last_user_turn = user_text
        working = compute_readiness(working)
        next_question = choose_next_question(working)
        if next_question is not None:
            working.pending_question = next_question
            working.last_agent_turn = next_question.question
            return render_clarification(next_question), working
        plan = build_execution_plan(working)
        blocker = render_execution_blocker(working if plan.action == "await_clarification" else working)
        working.last_agent_turn = blocker
        return blocker, working
