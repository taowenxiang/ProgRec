from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from progrec_service.config import settings
from progrec_service.runtime import agent_v2_runner
from progrec_service.services.agent_sessions import (
    create_session as create_session_entry,
    get_session_dialog_state,
    list_sessions as list_session_entries,
    list_session_messages,
    persist_assistant_turn,
    persist_user_message,
)
from progrec_service.services.runtime_context import resolve_runtime_context
from progrec_service.services.sse import emit_chat_stream

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/sessions", status_code=201)
def create_session(payload: dict[str, object]) -> dict[str, object]:
    record = create_session_entry(
        runtime_profile_id=payload.get("runtime_profile_id"),
        session_mode=str(payload.get("session_mode", "chat")),
    )
    return {"session_id": record.id, "status": record.status}


@router.get("/sessions")
def list_sessions() -> dict[str, object]:
    return {"sessions": list_session_entries()}


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str) -> dict[str, object]:
    return {"session_id": session_id, "messages": list_session_messages(session_id)}


@router.post("/sessions/{session_id}/messages")
def create_message(session_id: str, payload: dict[str, object]) -> StreamingResponse:
    persist_user_message(session_id, str(payload["message"]))
    dialog_state_payload = get_session_dialog_state(session_id)
    runtime_context = resolve_runtime_context(
        ephemeral_runtime=payload.get("runtime"),
        runtime_profile_id=payload.get("runtime_profile_id"),
    )
    result = agent_v2_runner.run_agent_turn(
        repo_root=settings.progrec_repo_root,
        dialog_state_payload=dialog_state_payload,
        runtime_context=runtime_context,
        user_text=str(payload["message"]),
    )

    def event_stream() -> Iterator[str]:
        for event in emit_chat_stream(
            reply_text=result["reply_text"],
            structured_result=result["structured_result"],
        ):
            yield event
        persist_assistant_turn(
            session_id=session_id,
            content_text=result["reply_text"],
            structured_payload=result["structured_result"],
            dialog_state_payload=result["dialog_state_payload"],
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
