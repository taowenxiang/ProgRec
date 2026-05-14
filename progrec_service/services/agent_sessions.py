from __future__ import annotations

import uuid
from dataclasses import asdict

from progrec_agent.dialog.state import DialogState
from progrec_service.db.models import AgentMessage, AgentSession
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


def get_session_dialog_state(session_id: str) -> dict[str, object]:
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        record = repo.get_session(session_id)
    if record is None:
        raise ValueError(f"session {session_id} not found")
    return dict(record.dialog_state_payload or {})


def persist_user_message(session_id: str, content_text: str) -> None:
    message = AgentMessage(
        id=f"msg_{uuid.uuid4().hex[:12]}",
        session_id=session_id,
        role="user",
        content_text=content_text,
        structured_payload={},
        stream_status="received",
    )
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        repo.add_message(message)
        session.commit()


def persist_assistant_turn(
    *,
    session_id: str,
    content_text: str,
    structured_payload: dict[str, object],
    dialog_state_payload: dict[str, object],
) -> None:
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        record = repo.get_session(session_id)
        if record is None:
            raise ValueError(f"session {session_id} not found")
        record.dialog_state_payload = dialog_state_payload
        record.last_result_handle = str(structured_payload.get("last_result_handle") or "")
        assistant_message = AgentMessage(
            id=f"msg_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            role="assistant",
            content_text=content_text,
            structured_payload=structured_payload,
            stream_status="completed",
        )
        repo.add_message(assistant_message)
        session.commit()
