from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestAgentRoutes(unittest.TestCase):
    def test_create_agent_session(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/agent/sessions",
            json={
                "runtime_profile": {
                    "mode": "ephemeral",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4.1-mini",
                    "api_key": "sk-test",
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("session_id", response.json())
