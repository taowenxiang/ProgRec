from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from progrec_service.db.models import AgentMessage, AgentSession


class AgentSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_session(self, model: AgentSession) -> AgentSession:
        self.session.add(model)
        self.session.flush()
        return model

    def get_session(self, session_id: str) -> AgentSession | None:
        return self.session.get(AgentSession, session_id)

    def list_sessions(self, *, limit: int = 50) -> list[AgentSession]:
        stmt = select(AgentSession).order_by(AgentSession.updated_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def add_message(self, model: AgentMessage) -> AgentMessage:
        self.session.add(model)
        self.session.flush()
        return model

    def list_messages(self, session_id: str) -> list[AgentMessage]:
        stmt = select(AgentMessage).where(AgentMessage.session_id == session_id).order_by(AgentMessage.created_at.asc())
        return list(self.session.scalars(stmt))
