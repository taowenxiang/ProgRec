from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app
from progrec_service.runtime import agent_v2_runner
from progrec_service.services.sse import emit_chat_stream


class TestAgentStream(unittest.TestCase):
    def test_runner_preserves_semi_autonomous_state_fields(self) -> None:
        state = agent_v2_runner._dialog_state_from_payload(
            {
                "active_goal": "mentor",
                "goal_targets": ["mentor"],
                "profile_context": {"research_topic": "NLP"},
                "planner_actions": [{"action": "ask_user"}],
                "suggested_next_actions": [{"target": "project"}],
                "tool_results_summary": {"mentor_count": 5},
            }
        )

        self.assertEqual(state.active_goal, "mentor")
        self.assertEqual(state.goal_targets, ["mentor"])
        self.assertEqual(state.profile_context["research_topic"], "NLP")
        self.assertEqual(state.planner_actions[0]["action"], "ask_user")
        self.assertEqual(state.suggested_next_actions[0]["target"], "project")
        self.assertEqual(state.tool_results_summary["mentor_count"], 5)

    def test_runner_returns_semi_autonomous_clarification_contract(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me about your background and target research opportunity.",
                "reasoning_summary": "Need profile context.",
            }
            result = agent_v2_runner.run_agent_turn(
                repo_root=__import__("pathlib").Path("."),
                dialog_state_payload={},
                runtime_context=_RuntimeContext(),
                user_text="Find an NLP mentor.",
            )

        self.assertEqual(result["structured_result"]["turn_type"], "clarification")
        self.assertEqual(
            result["structured_result"]["next_question"],
            "Tell me about your background and target research opportunity.",
        )
        self.assertEqual(result["structured_result"]["planner_actions"][0]["action"], "ask_user")
        self.assertNotIn("program_type", result["structured_result"]["missing_slots"])

    def test_runner_returns_mentor_only_skill_usage(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.build_temporary_profile",
                    "arguments": {
                        "profile_context": {
                            "research_topic": "NLP",
                            "program_type": "undergraduate research",
                            "experience_level": "medium",
                        }
                    },
                },
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.rank_mentors",
                    "arguments": {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
                },
                {
                    "action": "answer_from_context",
                    "message": "I found mentor recommendations. Want projects next?",
                },
            ]
            with patch(
                "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
                return_value={
                    "student_profile": {"student_id": "chat-temp-1"},
                    "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
                },
            ):
                result = agent_v2_runner.run_agent_turn(
                    repo_root=__import__("pathlib").Path("."),
                    dialog_state_payload={},
                    runtime_context=_RuntimeContext(),
                    user_text="Find an NLP mentor.",
                )

        skill_ids = [entry["skill_id"] for entry in result["structured_result"]["skill_usage"]]
        self.assertIn("/student-profiling", skill_ids)
        self.assertIn("/mentor-discovery", skill_ids)
        self.assertNotIn("/project-teammate-discovery", skill_ids)

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
