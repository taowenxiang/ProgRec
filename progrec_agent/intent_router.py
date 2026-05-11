from __future__ import annotations

from progrec_agent.agent_schema import RouterDecision
from progrec_agent.prompts import ROUTER_PROMPT


def route_user_message(user_text: str, *, llm_client, session) -> RouterDecision:
    normalized = user_text.lower().strip()
    if llm_client is not None:
        payload = llm_client.complete_json(f"{ROUTER_PROMPT}\nUser message: {user_text}")
        return RouterDecision(
            intent=str(payload.get("intent", "chat")),
            confidence=float(payload.get("confidence", 0.0)),
            candidate_tools=[str(item) for item in payload.get("candidate_tools", [])],
            needs_clarification=bool(payload.get("needs_clarification")),
            clarification_question=str(payload.get("clarification_question", "")),
            reasoning_summary=str(payload.get("reasoning_summary", "")),
        )
    if any(word in normalized for word in ["mentor", "recommend", "project", "teammate"]):
        return RouterDecision(intent="recommend", confidence=0.8, candidate_tools=["recommend_full_pipeline"])
    if "rebuild" in normalized and "graph" in normalized:
        return RouterDecision(intent="rebuild", confidence=0.9, candidate_tools=["rebuild_skill2_graph"])
    if any(word in normalized for word in ["why", "debug", "mismatch", "graph mode"]):
        return RouterDecision(
            intent="debug",
            confidence=0.75,
            candidate_tools=["debug_graph_mode", "inspect_artifacts"],
        )
    if any(word in normalized for word in ["show profile", "current profile"]):
        return RouterDecision(intent="inspect", confidence=0.9, candidate_tools=["show_current_profile"])
    return RouterDecision(
        intent="chat",
        confidence=0.35,
        candidate_tools=[],
        needs_clarification=True,
        clarification_question="Do you want recommendations, an explanation, or a graph/debug check?",
        reasoning_summary="Fallback router could not confidently classify the request.",
    )
