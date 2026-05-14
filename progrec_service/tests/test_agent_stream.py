from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestAgentStream(unittest.TestCase):
    def test_message_route_streams_stage_result_and_done_events(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        with patch(
            "progrec_service.runtime.agent_v2_runner.run_agent_turn",
            return_value={
                "reply_text": "I found 5 mentors for you.",
                "structured_result": {
                    "mentor_count": 5,
                    "skill_usage": [
                        {
                            "skill_id": "/mentor-discovery",
                            "status": "succeeded",
                            "summary": "Ranked mentor candidates.",
                        }
                    ],
                },
                "dialog_state_payload": {"task": "recommend_existing_student"},
            },
        ):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "Find me a mentor",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body = "".join(response.iter_text())
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: message.accepted", body)
        self.assertIn("event: agent.skill", body)
        self.assertIn("event: agent.result", body)
        self.assertIn("event: done", body)

        messages_response = client.get(f"/agent/sessions/{session_id}/messages")
        assistant_messages = [
            message for message in messages_response.json()["messages"] if message["role"] == "assistant"
        ]
        self.assertEqual(len(assistant_messages), 1)
        self.assertEqual(
            assistant_messages[0]["structured_payload"]["skill_usage"][0]["skill_id"],
            "/mentor-discovery",
        )

    def test_agent_skill_event_payload_is_json_decodable(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        skill_usage = [
            {
                "skill_id": "/project-teammate-discovery",
                "status": "succeeded",
                "summary": "Expanded project and teammate matches.",
            }
        ]
        with patch(
            "progrec_service.runtime.agent_v2_runner.run_agent_turn",
            return_value={
                "reply_text": "I expanded your matches.",
                "structured_result": {"skill_usage": skill_usage},
                "dialog_state_payload": {"task": "recommend_existing_student"},
            },
        ):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "Find project teammates",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body = "".join(response.iter_text())

        skill_line = next(line for line in body.splitlines() if line.startswith("data: {") and "skill_id" in line)
        self.assertEqual(json.loads(skill_line.removeprefix("data: "))["skill_id"], "/project-teammate-discovery")


if __name__ == "__main__":
    unittest.main()
