from __future__ import annotations

import uuid
from dataclasses import asdict

from progrec_agent.dialog.state import DialogState
from progrec_agent.runtime.result_state import result_handle_from_payload
from progrec_service.db.models import AgentMessage, AgentSession, utcnow
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


def _preview(text: str, *, limit: int = 80) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3].rstrip() + "..."


def list_sessions(*, limit: int = 50) -> list[dict[str, object]]:
    with SessionLocal() as session:
        repo = AgentSessionRepository(session)
        records = repo.list_sessions(limit=limit)
        payloads: list[dict[str, object]] = []
        for record in records:
            messages = repo.list_messages(record.id)
            latest = messages[-1] if messages else None
            latest_user = next((message for message in reversed(messages) if message.role == "user"), None)
            label = _preview(latest_user.content_text) if latest_user is not None else record.session_mode
            latest_preview = _preview(latest.content_text) if latest is not None else ""
            payloads.append(
                {
                    "session_id": record.id,
                    "status": record.status,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                    "runtime_profile_id": record.runtime_profile_id,
                    "label": label,
                    "summary": label,
                    "latest_message_preview": latest_preview,
                }
            )
        return payloads


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
        record = repo.get_session(session_id)
        if record is not None:
            record.updated_at = utcnow()
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
        record.last_result_handle = result_handle_from_payload(
            structured_payload=structured_payload,
            dialog_state_payload=dialog_state_payload,
        )
        record.updated_at = utcnow()
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
