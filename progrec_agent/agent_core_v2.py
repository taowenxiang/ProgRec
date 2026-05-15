from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from progrec_agent.agent_planner import AgentPlanner
from progrec_agent.contracts.registry import get_capability
from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.state import DialogState
from progrec_agent.response.composer import compose_fallback_reply
from progrec_agent.runtime import recommendation_runtime as recommendation_runtime_module
from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor, ToolExecutionResult
from progrec_agent.runtime.result_state import hydrate_result_arguments, record_shown_entity, store_result_payload
from progrec_agent.runtime.turn_execution import (
    auto_continue_after_profile_answer,
    can_auto_continue_after_profile_answer,
    handle_ask_user_action,
    handle_call_tool_action,
    handle_terminal_action,
)
from progrec_agent.runtime.turn_routing import apply_turn_routing


MAX_AGENT_STEPS = 4


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
        self.repo_root = Path(repo_root)
        self.temp_dir = Path(temp_dir)
        self.llm_client = llm_client
        self.recommendation_runtime = recommendation_runtime or recommendation_runtime_module
        self.planner = AgentPlanner(llm_client=llm_client)
        self.executor = ChatToolExecutor(
            repo_root=self.repo_root,
            temp_dir=self.temp_dir,
            recommendation_runtime=self.recommendation_runtime,
        )

    def _record_tool_result(self, state: DialogState, result: ToolExecutionResult) -> None:
        state.skill_trace.append(result.to_skill_trace_entry())
        payload = dict(result.payload)
        store_result_payload(state.execution_context, payload)

        canonical_tool_name = get_capability(result.tool_name).capability_id

        if canonical_tool_name in {
            "/student-profiling.build_temporary_profile",
            "/student-profiling.update_profile_context",
        }:
            state.profile_context.update(dict(payload.get("profile") or payload.get("profile_context") or {}))
        if canonical_tool_name == "/mentor-discovery.recommend_mentors":
            candidates = list(dict(payload.get("skill3_result") or {}).get("mentor_candidates") or [])
            state.tool_results_summary["mentor_count"] = len(candidates)
        if canonical_tool_name == "/project-teammate-discovery.recommend_projects":
            projects = list(payload.get("projects") or [])
            state.tool_results_summary["project_count"] = len(projects)
        if canonical_tool_name == "/project-teammate-discovery.recommend_teammates":
            teammates = list(payload.get("teammates") or [])
            state.tool_results_summary["teammate_count"] = len(teammates)
        if canonical_tool_name == "/mentor-discovery.get_mentor_by_rank":
            mentor_id = str(payload.get("mentor_id") or "").strip()
            record_shown_entity(state.execution_context, "mentor", mentor_id)
        if canonical_tool_name == "/project-teammate-discovery.get_project_by_rank":
            project_id = str(payload.get("project_id") or "").strip()
            record_shown_entity(state.execution_context, "project", project_id)
        if canonical_tool_name == "/project-teammate-discovery.get_teammate_by_rank":
            teammate_id = str(payload.get("student_id") or payload.get("teammate_id") or "").strip()
            record_shown_entity(state.execution_context, "teammate", teammate_id)

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        had_pending_question = working.pending_question is not None
        if working.pending_question is not None:
            working = apply_pending_answer(working, user_text)
        working.last_user_turn = user_text
        if not had_pending_question or working.suggested_next_actions:
            apply_turn_routing(working, user_text)

        reply_text = ""
        attempted_tool_calls: set[str] = set()
        for _step in range(MAX_AGENT_STEPS):
            action = self.planner.plan_next_action(working, user_text)
            working.planner_actions.append(asdict(action))
            working.last_skill_plan = asdict(action)

            if can_auto_continue_after_profile_answer(working, action):
                return auto_continue_after_profile_answer(
                    state=working,
                    executor=self.executor,
                    record_tool_result=self._record_tool_result,
                )

            if action.action == "ask_user":
                outcome = handle_ask_user_action(
                    state=working,
                    action=action,
                    user_text=user_text,
                )
                return outcome.reply_text, working

            if action.action == "call_tool":
                outcome = handle_call_tool_action(
                    state=working,
                    action=action,
                    attempted_tool_calls=attempted_tool_calls,
                    executor=self.executor,
                    record_tool_result=self._record_tool_result,
                    hydrate_arguments=self._hydrate_capability_arguments,
                )
                if outcome.continue_loop:
                    continue
                if outcome.handled:
                    return outcome.reply_text, working
                continue

            outcome = handle_terminal_action(state=working, action=action)
            if outcome.handled:
                if action.action == "stop":
                    break
                return outcome.reply_text, working

        reply_text = reply_text or compose_fallback_reply(
            turn_type=working.execution_context.last_turn_type or "recommendation_result",
            tool_results_summary=working.tool_results_summary,
            suggested_next_actions=working.suggested_next_actions,
            next_question=working.execution_context.next_question,
        )
        working.last_agent_turn = reply_text
        return reply_text, working

    def _hydrate_capability_arguments(self, state: DialogState, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
        return hydrate_result_arguments(state.execution_context, arguments)
