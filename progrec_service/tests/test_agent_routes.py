from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app


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
