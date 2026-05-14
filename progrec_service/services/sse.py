from __future__ import annotations

import json
from collections.abc import Iterator


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def emit_chat_stream(*, reply_text: str, structured_result: dict[str, object]) -> Iterator[str]:
    yield sse_event("message.accepted", {"status": "accepted"})
    yield sse_event("agent.stage", {"stage": "running_recommendation"})
    yield sse_event("agent.delta", {"text": reply_text})
    for skill in list(structured_result.get("skill_usage") or []):
        if isinstance(skill, dict):
            yield sse_event("agent.skill", skill)
    yield sse_event("agent.result", structured_result)
    yield sse_event("done", {"status": "completed"})
