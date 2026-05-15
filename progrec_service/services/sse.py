from __future__ import annotations

import json
from collections.abc import Iterator


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stage_for_turn(structured_result: dict[str, object]) -> str:
    turn_type = str(structured_result.get("turn_type") or "")
    return {
        "clarification": "collecting_context",
        "inspection": "inspecting_result",
        "recommendation_result": "running_recommendation",
        "resource_validation": "validating_resources",
    }.get(turn_type, "running_recommendation")


def emit_chat_prelude() -> Iterator[str]:
    yield sse_event("message.accepted", {"status": "accepted"})
    yield sse_event("agent.stage", {"stage": "reading_skill_documents"})
    yield sse_event(
        "agent.skill",
        {
            "skill_id": "/progrec-agent",
            "status": "running",
            "summary": "Reading local Skill.md documents before selecting ProgRec skills.",
        },
    )
    yield sse_event("agent.stage", {"stage": "selecting_skills"})


def emit_chat_stream(*, reply_text: str, structured_result: dict[str, object], include_prelude: bool = True) -> Iterator[str]:
    if include_prelude:
        yield from emit_chat_prelude()
    yield sse_event("agent.stage", {"stage": _stage_for_turn(structured_result)})
    yield sse_event("agent.delta", {"text": reply_text})
    for skill in list(structured_result.get("skill_usage") or []):
        if isinstance(skill, dict):
            yield sse_event("agent.skill", skill)
    yield sse_event("agent.result", structured_result)
    yield sse_event("done", {"status": "completed"})
