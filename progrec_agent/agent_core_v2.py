from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from progrec_agent.agent_planner import AgentPlanner
from progrec_agent.contracts.registry import get_capability
from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.domain_guard import extract_research_topic
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
        payload = dict(result.payload)
        result_ref = str(payload.get("result_ref") or "").strip()
        result_type = str(payload.get("result_type") or "").strip()
        if result_ref and result_type:
            state.execution_context.latest_result_refs[result_type] = result_ref
            state.execution_context.active_result_ref = result_ref
            state.execution_context.result_ref_payloads[result_ref] = payload
            state.execution_context.result_handle = result_ref
            state.execution_context.last_result = payload

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
            if mentor_id:
                state.execution_context.last_shown_entities["mentor"] = mentor_id
        if canonical_tool_name == "/project-teammate-discovery.get_project_by_rank":
            project_id = str(payload.get("project_id") or "").strip()
            if project_id:
                state.execution_context.last_shown_entities["project"] = project_id
        if canonical_tool_name == "/project-teammate-discovery.get_teammate_by_rank":
            teammate_id = str(payload.get("student_id") or payload.get("teammate_id") or "").strip()
            if teammate_id:
                state.execution_context.last_shown_entities["teammate"] = teammate_id

    def _can_auto_continue_after_profile_answer(self, state: DialogState, action) -> bool:
        return (
            action.action == "ask_user"
            and action.reasoning_summary == "Planner action was invalid or unavailable."
            and state.clarification_turn_count > 0
            and bool(state.profile_context)
            and state.active_goal in {"mentor", "project", "teammate"}
        )

    def _auto_continue_after_profile_answer(self, state: DialogState) -> tuple[str, DialogState]:
        profile_result = self.executor.execute(
            "/student-profiling.build_temporary_profile",
            {"profile_context": dict(state.profile_context)},
        )
        self._record_tool_result(state, profile_result)

        profile = dict(profile_result.payload.get("profile") or {})
        if state.active_goal == "mentor":
            recommendation_result = self.executor.execute(
                "/mentor-discovery.rank_mentors",
                {"profile": profile, "top_k": 5},
            )
            self._record_tool_result(state, recommendation_result)
            state.suggested_next_actions = [
                {"target": "project", "label": "Find related projects"},
                {"target": "teammate", "label": "Find teammates"},
            ]
        elif state.active_goal == "project":
            recommendation_result = self.executor.execute(
                "/project-teammate-discovery.recommend_projects",
                {"profile": profile, "top_k": 5},
            )
            self._record_tool_result(state, recommendation_result)
            state.suggested_next_actions = [{"target": "teammate", "label": "Find teammates"}]
        else:
            recommendation_result = self.executor.execute(
                "/project-teammate-discovery.recommend_teammates",
                {"profile": profile, "top_k": 5},
            )
            self._record_tool_result(state, recommendation_result)
            state.suggested_next_actions = [{"target": "project", "label": "Find related projects"}]

        state.execution_context.last_turn_type = "recommendation_result"
        reply_text = _compose_auto_continued_reply(state)
        state.last_agent_turn = reply_text
        return reply_text, state

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        if working.pending_question is not None:
            working = apply_pending_answer(working, user_text)
        working.last_user_turn = user_text
        if not working.goal_targets:
            working.goal_targets = infer_user_targets(user_text)
        if not working.active_goal and working.goal_targets:
            working.active_goal = working.goal_targets[0]

        reply_text = ""
        attempted_tool_calls: set[str] = set()
        for _step in range(MAX_AGENT_STEPS):
            action = self.planner.plan_next_action(working, user_text)
            working.planner_actions.append(asdict(action))
            working.last_skill_plan = asdict(action)

            if self._can_auto_continue_after_profile_answer(working, action):
                return self._auto_continue_after_profile_answer(working)

            if action.action == "ask_user":
                reply_text = action.message
                if (
                    action.reasoning_summary == "Planner action was invalid or unavailable."
                    and not working.profile_context
                ):
                    reply_text = _compose_initial_profile_question(user_text, working.active_goal)
                working.pending_question = PendingQuestion(
                    slot_name=action.pending_slot or "profile_context",
                    question=reply_text,
                    expected_answer_shape=action.expected_answer_shape or "free_text_profile",
                )
                working.execution_context.last_turn_type = "clarification"
                working.execution_context.next_question = reply_text
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "call_tool":
                call_signature = _tool_call_signature(action.tool_name, action.arguments)
                if call_signature in attempted_tool_calls:
                    target_label = working.active_goal or "the next recommendation step"
                    reply_text = (
                        f"I already gathered enough context to continue with {target_label}. "
                        "Please tell me if you want me to keep going from here."
                    )
                    working.execution_context.last_turn_type = "clarification"
                    working.execution_context.next_question = reply_text
                    working.last_agent_turn = reply_text
                    return reply_text, working
                attempted_tool_calls.add(call_signature)
                if not is_tool_allowed_for_state(action.tool_name, working):
                    reply_text = "I can do that, but I need you to confirm this new recommendation target first."
                    working.execution_context.last_turn_type = "clarification"
                    working.execution_context.next_question = reply_text
                    working.last_agent_turn = reply_text
                    return reply_text, working
                try:
                    call_arguments = self._hydrate_capability_arguments(working, action.tool_name, action.arguments)
                    result = self.executor.execute(action.tool_name, call_arguments)
                except ValueError as exc:
                    reply_text = (
                        "I need a little more profile context before I can run that skill. "
                        "Could you share your background, experience level, and what kind of research opportunity you want?"
                    )
                    working.skill_trace.append(
                        {
                            "skill_id": action.tool_name.split(".", 1)[0],
                            "tool_name": action.tool_name,
                            "status": "failed",
                            "summary": str(exc),
                        }
                    )
                    working.execution_context.last_turn_type = "clarification"
                    working.execution_context.next_question = reply_text
                    working.last_agent_turn = reply_text
                    return reply_text, working
                self._record_tool_result(working, result)
                if get_capability(action.tool_name).capability_id in {
                    "/mentor-discovery.recommend_mentors",
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

    def _hydrate_capability_arguments(self, state: DialogState, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
        hydrated = dict(arguments)
        for ref_key in (
            "student_profile_ref",
            "mentor_result_ref",
            "project_result_ref",
            "teammate_result_ref",
            "bundle_result_ref",
            "resource_validation_ref",
        ):
            ref_value = hydrated.get(ref_key)
            if isinstance(ref_value, str) and ref_value in state.execution_context.result_ref_payloads:
                hydrated[ref_key] = dict(state.execution_context.result_ref_payloads[ref_value])
        return hydrated


def _tool_call_signature(tool_name: str, arguments: dict[str, object]) -> str:
    return f"{tool_name}:{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"


def _compose_auto_continued_reply(state: DialogState) -> str:
    program_type = str(state.profile_context.get("program_type") or "student").strip()
    skills = list(state.profile_context.get("skills") or [])
    topic = str(state.profile_context.get("research_topic") or "").strip()
    background_bits = [program_type]
    if skills:
        background_bits.append("/".join(str(item) for item in skills[:2]))
    if topic and topic.lower() not in {"next semester"}:
        background_bits.append(topic)
    background = ", ".join(bit for bit in background_bits if bit)

    if state.active_goal == "mentor":
        mentor_count = int(state.tool_results_summary.get("mentor_count") or 0)
        return (
            f"Thanks, that gives me enough to work with. I used your {background} context to start the mentor search "
            f"and found {mentor_count} mentor matches. If you want, I can next expand this into related projects or teammates."
        )
    if state.active_goal == "project":
        project_count = int(state.tool_results_summary.get("project_count") or 0)
        return (
            f"Thanks, I had enough profile detail to continue directly. I found {project_count} project matches "
            f"for your {background} context."
        )
    teammate_count = int(state.tool_results_summary.get("teammate_count") or 0)
    return (
        f"Thanks, I had enough profile detail to continue directly. I found {teammate_count} teammate matches "
        f"for your {background} context."
    )


def _compose_initial_profile_question(user_text: str, active_goal: str) -> str:
    topic = extract_research_topic(user_text)
    goal = active_goal or "mentor"
    if topic:
        return (
            f"I can help with {goal} recommendations for {topic}. "
            "To make the matches useful, could you tell me your degree level, relevant skills or project experience, "
            "and what kind of opportunity or guidance you want?"
        )
    return (
        f"I can help with {goal} recommendations. "
        "To make the matches useful, could you tell me your degree level, relevant skills or project experience, "
        "and what kind of opportunity or guidance you want?"
    )
