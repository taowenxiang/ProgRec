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
                reply_text="Tell me a little more about your background.",
                structured_result={
                    "turn_type": "clarification",
                    "next_question": "Tell me a little more about your background.",
                },
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
                "reply_text": "Tell me about your background and target opportunity.",
                "structured_result": {
                    "turn_type": "clarification",
                    "intent": "mentor",
                    "missing_slots": [],
                    "next_question": "Tell me about your background and target opportunity.",
                    "skill_usage": [],
                },
                "dialog_state_payload": {"active_goal": "mentor"},
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
        reply_index = body.index("Tell me about your background and target opportunity.")
        self.assertLess(reading_stage_index, reply_index)
        self.assertIn('"skill_id": "/progrec-agent"', body)
        self.assertIn("Reading local Skill.md documents", body)

    def test_message_route_persists_pending_question_across_turns(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        captured_states: list[dict[str, object]] = []

        def fake_runner(*, dialog_state_payload, **kwargs):
            captured_states.append(dict(dialog_state_payload))
            if len(captured_states) == 1:
                return {
                    "reply_text": "Tell me about your background and research interests.",
                    "structured_result": {
                        "turn_type": "clarification",
                        "next_question": "Tell me about your background and research interests.",
                        "skill_usage": [],
                    },
                    "dialog_state_payload": {
                        "pending_question": {
                            "slot_name": "profile_context",
                            "question": "Tell me about your background and research interests.",
                            "expected_answer_shape": "free_text_profile",
                        },
                        "execution_context": {
                            "last_turn_type": "clarification",
                            "next_question": "Tell me about your background and research interests.",
                        },
                    },
                }
            return {
                "reply_text": "What kind of mentorship are you looking for?",
                "structured_result": {
                    "turn_type": "clarification",
                    "next_question": "What kind of mentorship are you looking for?",
                    "skill_usage": [],
                },
                "dialog_state_payload": {
                    "execution_context": {
                        "last_turn_type": "clarification",
                        "next_question": "What kind of mentorship are you looking for?",
                    },
                },
            }

        with patch("progrec_service.runtime.agent_v2_runner.run_agent_turn", side_effect=fake_runner):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "Help me find a mentor for NLP.",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                self.assertEqual(response.status_code, 200)
                list(response.iter_text())

            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "I am an ug and I am interested in object detection",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                self.assertEqual(response.status_code, 200)
                list(response.iter_text())

        self.assertIsNone(captured_states[0].get("pending_question"))
        self.assertEqual(captured_states[1]["pending_question"]["slot_name"], "profile_context")

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

    def test_message_route_supports_three_turn_closed_loop_followup(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]

        llm_instance = patch("progrec_service.runtime.agent_v2_runner.LLMClient").start().return_value
        self.addCleanup(patch.stopall)
        llm_instance.complete_json.side_effect = [
            {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
                "reasoning_summary": "Need profile details.",
            },
            {
                "action": "ask_user",
                "message": "Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                "reasoning_summary": "Planner action was invalid or unavailable.",
            },
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.recommend_projects",
                "arguments": {"top_k": 5},
                "reasoning_summary": "The user accepted the suggested project follow-up.",
            },
            {
                "action": "suggest_next_steps",
                "message": "I found related projects. Want teammate matches too?",
                "suggested_next_actions": [{"target": "teammate", "label": "Find teammates"}],
                "reasoning_summary": "Projects are now available.",
            },
        ]

        with patch(
            "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
            return_value={
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
            },
        ), patch(
            "progrec_agent.runtime.recommendation_runtime.run_project_recommendations_for_profile",
            return_value={
                "projects": [{"project_id": "p1"}, {"project_id": "p2"}],
            },
        ):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "Help me find an NLP mentor.",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body1 = "".join(response.iter_text())
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "I am an undergraduate CS student with Python and some NLP project experience.",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body2 = "".join(response.iter_text())
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={
                    "message": "yes please",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            ) as response:
                body3 = "".join(response.iter_text())

        self.assertIn("background and research interests", body1)
        self.assertIn("found 2 mentor matches", body2)
        self.assertIn("related projects", body3)

        messages_response = client.get(f"/agent/sessions/{session_id}/messages")
        assistant_messages = [
            message for message in messages_response.json()["messages"] if message["role"] == "assistant"
        ]
        self.assertEqual(len(assistant_messages), 3)
        latest_structured = assistant_messages[-1]["structured_payload"]
        self.assertEqual(latest_structured["active_goal"], "project")
        self.assertIn("project_result", latest_structured["latest_result_refs"])
        self.assertIn("mentor_result", latest_structured["latest_result_refs"])

    def test_message_route_supports_mentor_inspect_explain_and_project_followup(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]

        llm_instance = patch("progrec_service.runtime.agent_v2_runner.LLMClient").start().return_value
        self.addCleanup(patch.stopall)
        llm_instance.complete_json.side_effect = [
            {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
                "reasoning_summary": "Need profile details.",
            },
            {
                "action": "ask_user",
                "message": "Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                "reasoning_summary": "Planner action was invalid or unavailable.",
            },
            {
                "action": "call_tool",
                "tool_name": "/mentor-discovery.get_mentor_by_rank",
                "arguments": {"rank": 1},
                "reasoning_summary": "User asked to inspect the first mentor from the latest mentor result.",
            },
            {
                "action": "answer_from_context",
                "message": "Here is the first mentor from your last result.",
                "reasoning_summary": "The inspection result answered the user directly.",
            },
            {
                "action": "call_tool",
                "tool_name": "/mentor-discovery.explain_mentor_match",
                "arguments": {"rank": 1},
                "reasoning_summary": "User asked why the shown mentor was recommended.",
            },
            {
                "action": "answer_from_context",
                "message": "This mentor matches because of their strong NLP alignment.",
                "reasoning_summary": "The explanation result answered the user's why question.",
            },
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.recommend_projects",
                "arguments": {"top_k": 5},
                "reasoning_summary": "The user accepted the suggested project follow-up.",
            },
            {
                "action": "suggest_next_steps",
                "message": "I found related projects. Want teammate matches too?",
                "suggested_next_actions": [{"target": "teammate", "label": "Find teammates"}],
                "reasoning_summary": "Projects are now available.",
            },
        ]

        with patch(
            "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
            return_value={
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {
                    "mentor_candidates": [
                        {"mentor_id": "m1", "mentor_name": "Prof A", "reason": "Strong NLP alignment."},
                        {"mentor_id": "m2", "mentor_name": "Prof B", "reason": "Good research fit."},
                    ]
                },
            },
        ), patch(
            "progrec_agent.runtime.recommendation_runtime.run_project_recommendations_for_profile",
            return_value={
                "projects": [
                    {"project_id": "p1", "reason": "Extends your NLP experience."},
                    {"project_id": "p2", "reason": "Fits your Python background."},
                ],
            },
        ):
            turns = [
                "Help me find an NLP mentor.",
                "I am an undergraduate CS student with Python and some NLP project experience.",
                "Show me the first mentor.",
                "Why this mentor?",
                "yes please",
            ]
            bodies: list[str] = []
            for message in turns:
                with client.stream(
                    "POST",
                    f"/agent/sessions/{session_id}/messages",
                    json={
                        "message": message,
                        "runtime": {
                            "mode": "ephemeral",
                            "base_url": "https://api.openai.com/v1",
                            "model": "gpt-4.1-mini",
                            "api_key": "sk-test",
                        },
                    },
                ) as response:
                    self.assertEqual(response.status_code, 200)
                    bodies.append("".join(response.iter_text()))

        self.assertIn("background and research interests", bodies[0])
        self.assertIn("found 2 mentor matches", bodies[1])
        self.assertIn("first mentor", bodies[2])
        self.assertIn("strong NLP alignment", bodies[3])
        self.assertIn("related projects", bodies[4])

        messages_response = client.get(f"/agent/sessions/{session_id}/messages")
        assistant_messages = [
            message for message in messages_response.json()["messages"] if message["role"] == "assistant"
        ]
        self.assertEqual(len(assistant_messages), 5)
        latest_structured = assistant_messages[-1]["structured_payload"]
        self.assertEqual(latest_structured["active_goal"], "project")
        self.assertIn("mentor_result", latest_structured["latest_result_refs"])
        self.assertIn("project_result", latest_structured["latest_result_refs"])
        self.assertEqual(latest_structured["last_shown_entities"]["mentor"], "m1")

    def test_message_route_supports_project_inspect_and_explain_followup(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]

        llm_instance = patch("progrec_service.runtime.agent_v2_runner.LLMClient").start().return_value
        self.addCleanup(patch.stopall)
        llm_instance.complete_json.side_effect = [
            {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
                "reasoning_summary": "Need profile details.",
            },
            {
                "action": "ask_user",
                "message": "Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                "reasoning_summary": "Planner action was invalid or unavailable.",
            },
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.recommend_projects",
                "arguments": {"top_k": 5},
                "reasoning_summary": "The user accepted the suggested project follow-up.",
            },
            {
                "action": "suggest_next_steps",
                "message": "I found related projects. Want teammate matches too?",
                "suggested_next_actions": [{"target": "teammate", "label": "Find teammates"}],
                "reasoning_summary": "Projects are now available.",
            },
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.get_project_by_rank",
                "arguments": {"rank": 1},
                "reasoning_summary": "User asked to inspect the first project from the latest project result.",
            },
            {
                "action": "answer_from_context",
                "message": "Here is the first project from your last result.",
                "reasoning_summary": "The inspection result answered the user directly.",
            },
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.explain_project_match",
                "arguments": {"rank": 1},
                "reasoning_summary": "User asked why the shown project was recommended.",
            },
            {
                "action": "answer_from_context",
                "message": "This project fits because it extends your NLP experience.",
                "reasoning_summary": "The explanation result answered the user's why question.",
            },
        ]

        with patch(
            "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
            return_value={
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {
                    "mentor_candidates": [
                        {"mentor_id": "m1", "mentor_name": "Prof A", "reason": "Strong NLP alignment."},
                        {"mentor_id": "m2", "mentor_name": "Prof B", "reason": "Good research fit."},
                    ]
                },
            },
        ), patch(
            "progrec_agent.runtime.recommendation_runtime.run_project_recommendations_for_profile",
            return_value={
                "projects": [
                    {"project_id": "p1", "reason": "Extends your NLP experience."},
                    {"project_id": "p2", "reason": "Fits your Python background."},
                ],
            },
        ):
            turns = [
                "Help me find an NLP mentor.",
                "I am an undergraduate CS student with Python and some NLP project experience.",
                "yes please",
                "Show me the first project.",
                "Why this project?",
            ]
            bodies: list[str] = []
            for message in turns:
                with client.stream(
                    "POST",
                    f"/agent/sessions/{session_id}/messages",
                    json={
                        "message": message,
                        "runtime": {
                            "mode": "ephemeral",
                            "base_url": "https://api.openai.com/v1",
                            "model": "gpt-4.1-mini",
                            "api_key": "sk-test",
                        },
                    },
                ) as response:
                    self.assertEqual(response.status_code, 200)
                    bodies.append("".join(response.iter_text()))

        self.assertIn("background and research interests", bodies[0])
        self.assertIn("found 2 mentor matches", bodies[1])
        self.assertIn("related projects", bodies[2])
        self.assertIn("first project", bodies[3])
        self.assertIn("extends your NLP experience", bodies[4])

        messages_response = client.get(f"/agent/sessions/{session_id}/messages")
        assistant_messages = [
            message for message in messages_response.json()["messages"] if message["role"] == "assistant"
        ]
        self.assertEqual(len(assistant_messages), 5)
        latest_structured = assistant_messages[-1]["structured_payload"]
        self.assertEqual(latest_structured["active_goal"], "project")
        self.assertEqual(latest_structured["last_shown_entities"]["project"], "p1")
        self.assertIn("project_result", latest_structured["latest_result_refs"])


if __name__ == "__main__":
    unittest.main()
