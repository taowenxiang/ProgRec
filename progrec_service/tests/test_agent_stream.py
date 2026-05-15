from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.runtime import agent_v2_runner
from progrec_service.services.sse import emit_chat_stream


class TestAgentStream(unittest.TestCase):
    def test_runner_returns_clarification_turn_contract(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {"profile_source": {"value": "temporary_profile", "provenance": "explicit"}},
                "constraints": {"research_topic": {"value": "NLP", "provenance": "explicit"}},
                "preferences": {},
                "references": {},
                "confidence": 0.9,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            result = agent_v2_runner.run_agent_turn(
                repo_root=__import__("pathlib").Path("."),
                dialog_state_payload={},
                runtime_context=_RuntimeContext(),
                user_text="Find an NLP mentor.",
            )

        self.assertEqual(result["structured_result"]["turn_type"], "clarification")
        self.assertEqual(result["structured_result"]["intent"], "recommend_temporary_profile")
        self.assertIn("program_type", result["structured_result"]["missing_slots"])
        self.assertIn("program", result["structured_result"]["next_question"].lower())

    def test_runner_uses_state_skill_trace_in_structured_result(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.return_value = {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP", "provenance": "explicit"},
                    "program_type": {"value": "undergraduate research", "provenance": "explicit"},
                    "experience_level": {"value": "intermediate", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.96,
                "reasoning_summary": "Complete temporary request.",
            }
            with patch(
                "progrec_agent.runtime.recommendation_runtime.run_recommendation_for_profile",
                return_value={
                    "student_profile": {"student_id": "chat-temp-1"},
                    "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
                    "skill4_result": {"target_student_id": "chat-temp-1"},
                    "skill5_result": {
                        "recommendations": {"mentors": [{"rank": 1}], "projects": [], "teammates": []}
                    },
                },
            ):
                result = agent_v2_runner.run_agent_turn(
                    repo_root=__import__("pathlib").Path("."),
                    dialog_state_payload={},
                    runtime_context=_RuntimeContext(),
                    user_text="Find an NLP mentor.",
                )

        skill_usage = result["structured_result"]["skill_usage"]
        self.assertTrue(skill_usage)
        self.assertIn("/mentor-discovery", [entry["skill_id"] for entry in skill_usage])

    def test_clarification_stream_uses_collecting_context_stage(self) -> None:
        body = "".join(
            emit_chat_stream(
                reply_text="What kind of program are you targeting?",
                structured_result={"turn_type": "clarification", "next_question": "What kind of program are you targeting?"},
            )
        )
        self.assertIn('"stage": "collecting_context"', body)

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

    def test_message_route_streams_skill_reading_progress_before_final_reply(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]

        with patch(
            "progrec_service.runtime.agent_v2_runner.run_agent_turn",
            return_value={
                "reply_text": "What kind of program are you targeting?",
                "structured_result": {
                    "turn_type": "clarification",
                    "intent": "recommend_temporary_profile",
                    "missing_slots": ["program_type", "experience_level"],
                    "next_question": "What kind of program are you targeting?",
                    "skill_usage": [],
                },
                "dialog_state_payload": {"task": "recommend_temporary_profile"},
            },
        ):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "Help me find a mentor for NLP and trustworthy AI.",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-5.4",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body = "".join(response.iter_text())

        self.assertEqual(response.status_code, 200)
        reading_stage_index = body.index('"stage": "reading_skill_documents"')
        reply_index = body.index("What kind of program are you targeting?")
        self.assertLess(reading_stage_index, reply_index)
        self.assertIn('"skill_id": "/progrec-agent"', body)
        self.assertIn("Reading local Skill.md documents", body)

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

        skill_ids = []
        for line in body.splitlines():
            if not line.startswith("data: {") or "skill_id" not in line:
                continue
            payload = json.loads(line.removeprefix("data: "))
            if "skill_id" in payload:
                skill_ids.append(payload["skill_id"])
        self.assertIn("/progrec-agent", skill_ids)
        self.assertIn("/project-teammate-discovery", skill_ids)


if __name__ == "__main__":
    unittest.main()
