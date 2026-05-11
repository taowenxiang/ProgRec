from __future__ import annotations


def choose_action(decision, *, tool_name: str, tool_meta: dict[str, object]) -> dict[str, object]:
    if decision.needs_clarification and decision.clarification_question:
        return {"kind": "clarify", "question": decision.clarification_question}
    if decision.confidence < 0.5 and decision.clarification_question:
        return {"kind": "clarify", "question": decision.clarification_question}
    if tool_meta.get("risk_level") == "confirm":
        return {"kind": "confirm", "tool_name": tool_name}
    if tool_name:
        return {"kind": "execute", "tool_name": tool_name}
    return {"kind": "answer_only"}
