from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_service.db.models import AgentSession, Base
from progrec_service.db.session import build_engine, build_session_factory
from progrec_service.services.agent_sessions import create_session_record, persist_assistant_turn


class TestAgentSessionsService(unittest.TestCase):
    def test_persist_assistant_turn_uses_dialog_state_result_handle_fallback(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = build_session_factory(engine)

        with session_factory() as session:
            session.add(create_session_record(runtime_profile_id=None, session_mode="chat"))
            session.commit()
            session_id = session.query(AgentSession).first().id

        with patch("progrec_service.services.agent_sessions.SessionLocal", session_factory):
            persist_assistant_turn(
                session_id=session_id,
                content_text="Here is your mentor result.",
                structured_payload={},
                dialog_state_payload={"execution_context": {"result_handle": "rr_mentor_001"}},
            )

        with session_factory() as session:
            stored = session.query(AgentSession).first()

        self.assertEqual(stored.last_result_handle, "rr_mentor_001")

    def test_persist_assistant_turn_prefers_structured_result_handle(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = build_session_factory(engine)

        with session_factory() as session:
            session.add(create_session_record(runtime_profile_id=None, session_mode="chat"))
            session.commit()
            session_id = session.query(AgentSession).first().id

        with patch("progrec_service.services.agent_sessions.SessionLocal", session_factory):
            persist_assistant_turn(
                session_id=session_id,
                content_text="Here is your project result.",
                structured_payload={"last_result_handle": "rr_project_001"},
                dialog_state_payload={"execution_context": {"result_handle": "rr_project_fallback"}},
            )

        with session_factory() as session:
            stored = session.query(AgentSession).first()

        self.assertEqual(stored.last_result_handle, "rr_project_001")


if __name__ == "__main__":
    unittest.main()
