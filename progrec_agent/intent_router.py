from __future__ import annotations

import re

from progrec_agent.agent_schema import RouterDecision
from progrec_agent.prompts import ROUTER_PROMPT
from progrec_agent.tool_registry import TOOLS


RECOMMENDATION_CLARIFICATION = (
    "I can help turn this into a recommendation workflow. "
    "Should I use an existing student profile, or build a temporary profile from your interests?"
)


def _clarify_recommendation_request(*, confidence: float = 0.35, reasoning_summary: str = "") -> RouterDecision:
    return RouterDecision(
        message_type="domain_task",
        intent="recommend_mentor",
        confidence=confidence,
        candidate_tools=["recommend_full_pipeline"],
        needs_clarification=True,
        clarification_question=RECOMMENDATION_CLARIFICATION,
        reasoning_summary=reasoning_summary,
    )


def _route_explicit_pipeline_request(user_text: str) -> RouterDecision | None:
    normalized = user_text.lower().strip()
    if "student_id" not in normalized:
        return None
    if not any(word in normalized for word in ["recommend", "pipeline", "mentor", "project", "teammate"]):
        return None
    match = re.search(r"\bstudent_id\s*[:=]?\s*([A-Za-z0-9_-]+)", user_text, flags=re.IGNORECASE)
    if not match:
        return None
    tool_arguments: dict[str, object] = {"student_id": match.group(1)}
    if "graph-mode" in normalized or "graph mode" in normalized or "mode graph" in normalized:
        tool_arguments["mode"] = "graph"
    elif "demo-mode" in normalized or "demo mode" in normalized or "mode demo" in normalized:
        tool_arguments["mode"] = "demo"
    return RouterDecision(
        message_type="domain_task",
        intent="recommend_mentor",
        confidence=0.99,
        candidate_tools=["recommend_full_pipeline"],
        tool_name="recommend_full_pipeline",
        tool_arguments=tool_arguments,
        reasoning_summary="Explicit student_id request for the full recommendation pipeline.",
    )


def _route_deterministic_message_local(user_text: str) -> RouterDecision | None:
    normalized = user_text.lower().strip()
    explicit_decision = _route_explicit_pipeline_request(user_text)
    if explicit_decision is not None:
        return explicit_decision
    if any(phrase in normalized for phrase in ["which skill", "what tool", "what did you do", "last response"]):
        return RouterDecision(
            message_type="meta_question",
            intent="ask_last_action",
            confidence=0.65,
            candidate_tools=[],
            answer_only=True,
        )
    if any(phrase in normalized for phrase in ["show mentor", "mentor profile", "top mentor"]):
        return RouterDecision(
            message_type="domain_task",
            intent="inspect_current_mentor",
            confidence=0.9,
            candidate_tools=["show_recommended_mentor_profile"],
            tool_name="show_recommended_mentor_profile",
        )
    if any(phrase in normalized for phrase in ["show profile", "current profile"]):
        tool_name = "show_recommended_mentor_profile" if "mentor" in normalized else "show_current_profile"
        intent = "inspect_current_mentor" if "mentor" in normalized else "show_current_profile"
        return RouterDecision(
            message_type="domain_task",
            intent=intent,
            confidence=0.9,
            candidate_tools=[tool_name],
            tool_name=tool_name,
        )
    if "rebuild" in normalized and "graph" in normalized:
        return RouterDecision(
            message_type="domain_task",
            intent="rebuild_graph",
            confidence=0.9,
            candidate_tools=["rebuild_skill2_graph"],
            tool_name="rebuild_skill2_graph",
        )
    if any(word in normalized for word in ["why", "debug", "mismatch", "graph mode"]):
        return RouterDecision(
            message_type="domain_task",
            intent="debug_graph_mode",
            confidence=0.75,
            candidate_tools=["debug_graph_mode", "inspect_artifacts"],
            tool_name="debug_graph_mode",
        )
    return None


def _route_user_message_local(user_text: str) -> RouterDecision:
    deterministic = _route_deterministic_message_local(user_text)
    if deterministic is not None:
        return deterministic
    normalized = user_text.lower().strip()
    if any(word in normalized for word in ["mentor", "recommend", "project", "teammate"]):
        return RouterDecision(
            message_type="domain_task",
            intent="recommend_mentor",
            confidence=0.8,
            candidate_tools=["recommend_full_pipeline"],
            tool_name="recommend_full_pipeline",
        )
    return _clarify_recommendation_request(reasoning_summary="Local routing needs more recommendation context.")


def route_user_message(user_text: str, *, llm_client, session) -> RouterDecision:
    deterministic = _route_deterministic_message_local(user_text)
    if deterministic is not None:
        return deterministic
    if llm_client is not None:
        try:
            payload = llm_client.complete_json(f"{ROUTER_PROMPT}\nUser message: {user_text}")
            decision = RouterDecision(
                message_type=str(payload.get("message_type", "domain_task")),
                intent=str(payload.get("intent", "recommend_mentor")),
                confidence=float(payload.get("confidence", 0.0)),
                candidate_tools=[str(item) for item in payload.get("candidate_tools", [])],
                needs_clarification=bool(payload.get("needs_clarification")),
                clarification_question=str(payload.get("clarification_question", "")),
                answer_only=bool(payload.get("answer_only", False)),
                tool_name=str(payload.get("tool_name", "")),
                tool_arguments=dict(payload.get("tool_arguments") or {}),
                meta_reply=str(payload.get("meta_reply", "")),
                reasoning_summary=str(payload.get("reasoning_summary", "")),
            )
            if decision.message_type not in {"domain_task", "meta_question", "startup_help"}:
                return _clarify_recommendation_request(
                    confidence=decision.confidence,
                    reasoning_summary=decision.reasoning_summary,
                )
            decision.candidate_tools = [tool_name for tool_name in decision.candidate_tools if tool_name in TOOLS]
            if decision.tool_name and decision.tool_name not in TOOLS:
                decision.tool_name = ""
            return decision
        except Exception:
            return _clarify_recommendation_request(reasoning_summary="LLM routing failed.")
    return _route_user_message_local(user_text)
