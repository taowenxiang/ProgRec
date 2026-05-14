from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.agent_sessions import (
    create_session as create_session_entry,
    list_session_messages,
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/sessions", status_code=201)
def create_session(payload: dict[str, object]) -> dict[str, object]:
    record = create_session_entry(
        runtime_profile_id=payload.get("runtime_profile_id"),
        session_mode=str(payload.get("session_mode", "chat")),
    )
    return {"session_id": record.id, "status": record.status}


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str) -> dict[str, object]:
    return {"session_id": session_id, "messages": list_session_messages(session_id)}
