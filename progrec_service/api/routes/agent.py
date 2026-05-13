from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.agent_sessions import create_session_id

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/sessions")
def create_session(payload: dict[str, object]) -> dict[str, object]:
    return {"session_id": create_session_id(), "status": "ready"}
