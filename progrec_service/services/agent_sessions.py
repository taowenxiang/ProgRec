from __future__ import annotations

import uuid
from dataclasses import asdict

from progrec_agent.dialog.state import DialogState
from progrec_service.db.models import AgentSession
from progrec_service.db.repositories.agent_sessions import AgentSessionRepository
from progrec_service.db.session import SessionLocal


def create_session_id() -> str:
    return f"as_{uuid.uuid4().hex[:12]}"


def create_session_record(*, runtime_profile_id: str | None, session_mode: str) -> AgentSession:
    return AgentSession(
        id=create_session_id(),
        runtime_profile_id=runtime_profile_id,
        session_mode=session_mode,
        status="active",
        dialog_state_payload=asdict(DialogState()),
        last_result_handle=None,
    )


def create_session(*, runtime_profile_id: str | None, session_mode: str) -> AgentSession:
    record = create_session_record(runtime_profile_id=runtime_profile_id, session_mode=session_mode)
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        repo.add_session(record)
        session.commit()
    return record


def list_session_messages(session_id: str) -> list[dict[str, object]]:
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        messages = repo.list_messages(session_id)
    return [
        {
            "id": message.id,
            "role": message.role,
            "content_text": message.content_text,
            "structured_payload": message.structured_payload,
            "stream_status": message.stream_status,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
