from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from progrec_agent.agent_planner import AgentPlanner
from progrec_agent.dialog.state import DialogState
from progrec_agent.response.composer import compose_fallback_reply
from progrec_agent.runtime import recommendation_runtime as recommendation_runtime_module
from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor, ToolExecutionResult
from progrec_agent.target_policy import infer_user_targets, is_tool_allowed_for_state


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
        if result.tool_name in {
            "/student-profiling.build_temporary_profile",
            "/student-profiling.update_profile_context",
        }:
            state.profile_context.update(dict(result.payload.get("profile") or result.payload.get("profile_context") or {}))
        if result.tool_name == "/mentor-discovery.rank_mentors":
            state.execution_context.result_handle = "latest"
            state.execution_context.last_result = dict(result.payload)
            candidates = list(dict(result.payload.get("skill3_result") or {}).get("mentor_candidates") or [])
            state.tool_results_summary["mentor_count"] = len(candidates)
        if result.tool_name == "/project-teammate-discovery.recommend_projects":
            projects = list(result.payload.get("projects") or [])
            state.tool_results_summary["project_count"] = len(projects)
        if result.tool_name == "/project-teammate-discovery.recommend_teammates":
            teammates = list(result.payload.get("teammates") or [])
            state.tool_results_summary["teammate_count"] = len(teammates)

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        working.last_user_turn = user_text
        if not working.goal_targets:
            working.goal_targets = infer_user_targets(user_text)
        if not working.active_goal and working.goal_targets:
            working.active_goal = working.goal_targets[0]

        reply_text = ""
        for _step in range(MAX_AGENT_STEPS):
            action = self.planner.plan_next_action(working, user_text)
            working.planner_actions.append(asdict(action))
            working.last_skill_plan = asdict(action)

            if action.action == "ask_user":
                reply_text = action.message
                working.execution_context.last_turn_type = "clarification"
                working.execution_context.next_question = reply_text
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "call_tool":
                if not is_tool_allowed_for_state(action.tool_name, working):
                    reply_text = "I can do that, but I need you to confirm this new recommendation target first."
                    working.execution_context.last_turn_type = "clarification"
                    working.execution_context.next_question = reply_text
                    working.last_agent_turn = reply_text
                    return reply_text, working
                result = self.executor.execute(action.tool_name, action.arguments)
                self._record_tool_result(working, result)
                if action.tool_name in {
                    "/mentor-discovery.rank_mentors",
                    "/project-teammate-discovery.recommend_projects",
                    "/project-teammate-discovery.recommend_teammates",
                }:
                    working.execution_context.last_turn_type = "recommendation_result"
                continue

            if action.action == "suggest_next_steps":
                working.suggested_next_actions = list(action.suggested_next_actions)
                reply_text = action.message or compose_fallback_reply(
                    turn_type=working.execution_context.last_turn_type or "recommendation_result",
                    tool_results_summary=working.tool_results_summary,
                    suggested_next_actions=working.suggested_next_actions,
                )
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "answer_from_context":
                reply_text = action.message or compose_fallback_reply(
                    turn_type=working.execution_context.last_turn_type,
                    tool_results_summary=working.tool_results_summary,
                    suggested_next_actions=working.suggested_next_actions,
                )
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "stop":
                break

        reply_text = reply_text or compose_fallback_reply(
            turn_type=working.execution_context.last_turn_type or "recommendation_result",
            tool_results_summary=working.tool_results_summary,
            suggested_next_actions=working.suggested_next_actions,
            next_question=working.execution_context.next_question,
        )
        working.last_agent_turn = reply_text
        return reply_text, working
