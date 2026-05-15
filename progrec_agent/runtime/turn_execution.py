from __future__ import annotations

from dataclasses import dataclass
import json

from progrec_agent.contracts.registry import get_capability
from progrec_agent.dialog.state import PendingQuestion
from progrec_agent.nlu.domain_guard import extract_research_topic
from progrec_agent.response.composer import compose_fallback_reply
from progrec_agent.target_policy import is_tool_allowed_for_state


@dataclass
class TurnExecutionOutcome:
    handled: bool
    continue_loop: bool = False
    reply_text: str = ""


def can_auto_continue_after_profile_answer(state, action) -> bool:
    return (
        action.action == "ask_user"
        and action.reasoning_summary == "Planner action was invalid or unavailable."
        and state.clarification_turn_count > 0
        and bool(state.profile_context)
        and state.active_goal in {"mentor", "project", "teammate"}
    )


def auto_continue_after_profile_answer(*, state, executor, record_tool_result) -> tuple[str, object]:
    profile_result = executor.execute(
        "/student-profiling.build_temporary_profile",
        {"profile_context": dict(state.profile_context)},
    )
    record_tool_result(state, profile_result)

    profile = dict(profile_result.payload.get("profile") or {})
    if state.active_goal == "mentor":
        recommendation_result = executor.execute(
            "/mentor-discovery.rank_mentors",
            {"profile": profile, "top_k": 5},
        )
        record_tool_result(state, recommendation_result)
        state.suggested_next_actions = [
            {"target": "project", "label": "Find related projects"},
            {"target": "teammate", "label": "Find teammates"},
        ]
    elif state.active_goal == "project":
        recommendation_result = executor.execute(
            "/project-teammate-discovery.recommend_projects",
            {"profile": profile, "top_k": 5},
        )
        record_tool_result(state, recommendation_result)
        state.suggested_next_actions = [{"target": "teammate", "label": "Find teammates"}]
    else:
        recommendation_result = executor.execute(
            "/project-teammate-discovery.recommend_teammates",
            {"profile": profile, "top_k": 5},
        )
        record_tool_result(state, recommendation_result)
        state.suggested_next_actions = [{"target": "project", "label": "Find related projects"}]

    state.execution_context.last_turn_type = "recommendation_result"
    reply_text = compose_auto_continued_reply(state)
    state.last_agent_turn = reply_text
    return reply_text, state


def handle_ask_user_action(*, state, action, user_text: str) -> TurnExecutionOutcome:
    reply_text = action.message
    if (
        action.reasoning_summary == "Planner action was invalid or unavailable."
        and not state.profile_context
    ):
        reply_text = compose_initial_profile_question(user_text, state.active_goal)
    state.pending_question = PendingQuestion(
        slot_name=action.pending_slot or "profile_context",
        question=reply_text,
        expected_answer_shape=action.expected_answer_shape or "free_text_profile",
    )
    state.execution_context.last_turn_type = "clarification"
    state.execution_context.next_question = reply_text
    state.last_agent_turn = reply_text
    return TurnExecutionOutcome(handled=True, reply_text=reply_text)


def handle_call_tool_action(
    *,
    state,
    action,
    attempted_tool_calls: set[str],
    executor,
    record_tool_result,
    hydrate_arguments,
) -> TurnExecutionOutcome:
    call_signature = tool_call_signature(action.tool_name, action.arguments)
    if call_signature in attempted_tool_calls:
        target_label = state.active_goal or "the next recommendation step"
        reply_text = (
            f"I already gathered enough context to continue with {target_label}. "
            "Please tell me if you want me to keep going from here."
        )
        state.execution_context.last_turn_type = "clarification"
        state.execution_context.next_question = reply_text
        state.last_agent_turn = reply_text
        return TurnExecutionOutcome(handled=True, reply_text=reply_text)

    attempted_tool_calls.add(call_signature)
    if not is_tool_allowed_for_state(action.tool_name, state):
        reply_text = "I can do that, but I need you to confirm this new recommendation target first."
        state.execution_context.last_turn_type = "clarification"
        state.execution_context.next_question = reply_text
        state.last_agent_turn = reply_text
        return TurnExecutionOutcome(handled=True, reply_text=reply_text)

    try:
        call_arguments = hydrate_arguments(state, action.tool_name, action.arguments)
        result = executor.execute(action.tool_name, call_arguments)
    except ValueError as exc:
        reply_text = (
            "I need a little more profile context before I can run that skill. "
            "Could you share your background, experience level, and what kind of research opportunity you want?"
        )
        state.skill_trace.append(
            {
                "skill_id": action.tool_name.split(".", 1)[0],
                "tool_name": action.tool_name,
                "status": "failed",
                "summary": str(exc),
            }
        )
        state.execution_context.last_turn_type = "clarification"
        state.execution_context.next_question = reply_text
        state.last_agent_turn = reply_text
        return TurnExecutionOutcome(handled=True, reply_text=reply_text)

    record_tool_result(state, result)
    if get_capability(action.tool_name).capability_id in {
        "/mentor-discovery.recommend_mentors",
        "/project-teammate-discovery.recommend_projects",
        "/project-teammate-discovery.recommend_teammates",
    }:
        state.execution_context.last_turn_type = "recommendation_result"
    return TurnExecutionOutcome(handled=True, continue_loop=True)


def handle_terminal_action(*, state, action) -> TurnExecutionOutcome:
    if action.action == "suggest_next_steps":
        state.suggested_next_actions = list(action.suggested_next_actions)
        reply_text = action.message or compose_fallback_reply(
            turn_type=state.execution_context.last_turn_type or "recommendation_result",
            tool_results_summary=state.tool_results_summary,
            suggested_next_actions=state.suggested_next_actions,
        )
        state.last_agent_turn = reply_text
        return TurnExecutionOutcome(handled=True, reply_text=reply_text)

    if action.action == "answer_from_context":
        reply_text = action.message or compose_fallback_reply(
            turn_type=state.execution_context.last_turn_type,
            tool_results_summary=state.tool_results_summary,
            suggested_next_actions=state.suggested_next_actions,
        )
        state.last_agent_turn = reply_text
        return TurnExecutionOutcome(handled=True, reply_text=reply_text)

    if action.action == "stop":
        return TurnExecutionOutcome(handled=True)

    return TurnExecutionOutcome(handled=False)


def tool_call_signature(tool_name: str, arguments: dict[str, object]) -> str:
    return f"{tool_name}:{json.dumps(arguments, sort_keys=True, ensure_ascii=False)}"


def compose_auto_continued_reply(state) -> str:
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


def compose_initial_profile_question(user_text: str, active_goal: str) -> str:
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
