from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.services.agent_sessions import persist_user_message


class TestAgentRoutes(unittest.TestCase):
    def test_create_agent_session_persists_runtime_mode(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/agent/sessions",
            json={
                "session_mode": "chat",
                "runtime": {
                    "mode": "ephemeral",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4.1-mini",
                    "api_key": "sk-test",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "active")
        self.assertIn("session_id", response.json())

    def test_get_agent_messages_returns_persisted_history(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        history_response = client.get(f"/agent/sessions/{session_id}/messages")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()["messages"], [])

    def test_list_agent_sessions_returns_history_navigation_contract(self) -> None:
        client = TestClient(create_app())
        create_response = client.post(
            "/agent/sessions",
            json={"session_mode": "chat", "runtime_profile_id": "rp_saved"},
        )
        session_id = create_response.json()["session_id"]
        persist_user_message(session_id, "Find mentors for graph neural networks")

        response = client.get("/agent/sessions")

        self.assertEqual(response.status_code, 200)
        matching = [item for item in response.json()["sessions"] if item["session_id"] == session_id]
        self.assertEqual(len(matching), 1)
        item = matching[0]
        self.assertEqual(item["status"], "active")
        self.assertEqual(item["runtime_profile_id"], "rp_saved")
        self.assertIn("Find mentors", item["label"])
        self.assertIn("latest_message_preview", item)
        self.assertIn("created_at", item)
        self.assertIn("updated_at", item)
