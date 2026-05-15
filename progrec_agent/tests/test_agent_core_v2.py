from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState
from progrec_agent.runtime.chat_tool_executor import ToolExecutionResult


class TestAgentCoreV2(unittest.TestCase):
    def test_ask_user_persists_pending_question_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
                "reasoning_summary": "Need profile details.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            _, state = core.handle_message(DialogState(), "Help me find a mentor for NLP.")

        self.assertIsNotNone(state.pending_question)
        self.assertEqual(state.pending_question.slot_name, "profile_context")
        self.assertEqual(state.pending_question.expected_answer_shape, "free_text_profile")

    def test_first_turn_uses_planner_question_not_question_bank(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me a bit about your NLP background and the opportunity you want.",
                "reasoning_summary": "Need profile context before mentor discovery.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "Help me find a mentor for NLP and trustworthy AI.")

        self.assertIn("NLP background", reply)
        self.assertNotIn("What kind of program are you targeting", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.planner_actions[-1]["action"], "ask_user")

    def test_complete_mentor_request_runs_mentor_discovery_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.build_temporary_profile",
                    "arguments": {
                        "profile_context": {
                            "research_topic": "NLP and trustworthy AI",
                            "program_type": "undergraduate research",
                            "experience_level": "medium",
                        }
                    },
                    "reasoning_summary": "Build profile.",
                },
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.rank_mentors",
                    "arguments": {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
                    "reasoning_summary": "Rank mentors only.",
                },
                {
                    "action": "suggest_next_steps",
                    "message": "I found mentors. Would you like related projects next?",
                    "suggested_next_actions": [{"target": "project", "label": "Find related projects"}],
                    "reasoning_summary": "Original mentor request is satisfied.",
                },
            ]
            runtime = Mock()
            runtime.run_mentor_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, state = core.handle_message(
                DialogState(),
                "Find an NLP mentor for undergraduate research. My experience is medium.",
            )

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertIn("mentor", reply.lower())
        self.assertEqual(state.execution_context.last_turn_type, "recommendation_result")
        self.assertIn("/mentor-discovery", [entry["skill_id"] for entry in state.skill_trace])
        self.assertNotIn("/project-teammate-discovery", [entry["skill_id"] for entry in state.skill_trace])

    def test_malformed_tool_arguments_return_clarification_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "action": "call_tool",
                "tool_name": "/student-profiling.build_temporary_profile",
                "arguments": {},
                "reasoning_summary": "Missing profile context.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "help me find a mentor in Computer vision")

        self.assertIn("more profile context", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.execution_context.next_question, reply)

    def test_free_text_profile_context_can_continue_without_repeating_same_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.build_temporary_profile",
                    "arguments": {
                        "profile_context": "I want a mentor recommendation in NLP and trustworthy AI.",
                    },
                    "reasoning_summary": "Build an initial temporary profile from the user's free-text request.",
                },
                {
                    "action": "answer_from_context",
                    "message": "I have your initial profile context and can use it to narrow mentor matches next.",
                    "reasoning_summary": "Profile build succeeded, so I can respond naturally instead of repeating a fallback.",
                },
            ]
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "I want a mentor recommendation in NLP and trustworthy AI.")

        self.assertEqual(
            reply,
            "I have your initial profile context and can use it to narrow mentor matches next.",
        )
        self.assertEqual(state.execution_context.last_turn_type, "")
        self.assertEqual(state.skill_trace[0]["status"], "succeeded")

    def test_invalid_followup_planner_output_auto_continues_with_profile_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "ask_user",
                    "message": "Tell me about your background and research interests.",
                    "pending_slot": "profile_context",
                    "expected_answer_shape": "free_text_profile",
                },
                {
                    "action": "ask_user",
                    "message": "Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                    "reasoning_summary": "Planner action was invalid or unavailable.",
                },
            ]
            runtime = Mock()
            runtime.run_mentor_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            _, state = core.handle_message(DialogState(), "Help me find an NLP mentor.")
            reply, state = core.handle_message(
                state,
                "I am an undergraduate CS student with Python and some NLP project experience.",
            )

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertIn("found 2 mentor matches", reply)
        self.assertEqual(state.execution_context.last_turn_type, "recommendation_result")
        self.assertEqual(state.tool_results_summary["mentor_count"], 2)

    def test_record_tool_result_tracks_latest_result_refs(self) -> None:
        state = DialogState()
        result = ToolExecutionResult(
            tool_name="/mentor-discovery.recommend_mentors",
            skill_id="/mentor-discovery",
            status="succeeded",
            summary="Ranked mentor candidates.",
            payload={
                "result_ref": "rr_mentor_001",
                "result_type": "mentor_result",
                "summary": {"count": 2},
                "payload": {"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]}},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
            },
        )
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())

        core._record_tool_result(state, result)

        self.assertEqual(state.execution_context.latest_result_refs["mentor_result"], "rr_mentor_001")
        self.assertEqual(state.execution_context.active_result_ref, "rr_mentor_001")

    def test_followup_first_mentor_profile_uses_existing_mentor_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.get_mentor_by_rank",
                    "arguments": {"mentor_result_ref": "rr_mentor_001", "rank": 1},
                    "reasoning_summary": "User asked to inspect the first mentor from the previous result.",
                },
                {
                    "action": "answer_from_context",
                    "message": "Here is the first mentor from your last result.",
                    "reasoning_summary": "The inspection result already answered the user.",
                },
            ]
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            state = DialogState()
            state.execution_context.latest_result_refs = {"mentor_result": "rr_mentor_001"}
            state.execution_context.active_result_ref = "rr_mentor_001"
            state.execution_context.result_ref_payloads = {
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "payload": {
                        "skill3_result": {
                            "mentor_candidates": [{"mentor_id": "m1", "mentor_name": "Prof A"}]
                        }
                    },
                }
            }

            reply, updated = core.handle_message(state, "I want to see the first mentor's profile.")

        self.assertIn("first mentor", reply)
        self.assertEqual(updated.execution_context.last_shown_entities["mentor"], "m1")

    def test_followup_inspect_can_use_latest_result_without_explicit_ref_argument(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.get_mentor_by_rank",
                    "arguments": {"rank": 1},
                    "reasoning_summary": "User asked to inspect the first mentor from the active result.",
                },
                {
                    "action": "answer_from_context",
                    "message": "Here is the first mentor from your active result.",
                    "reasoning_summary": "The inspection result already answered the user.",
                },
            ]
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            state = DialogState()
            state.execution_context.latest_result_refs = {"mentor_result": "rr_mentor_001"}
            state.execution_context.active_result_ref = "rr_mentor_001"
            state.execution_context.result_ref_payloads = {
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "payload": {
                        "skill3_result": {
                            "mentor_candidates": [{"mentor_id": "m1", "mentor_name": "Prof A"}]
                        }
                    },
                }
            }

            reply, updated = core.handle_message(state, "Show me the first mentor.")

        self.assertIn("first mentor", reply)
        self.assertEqual(updated.execution_context.last_shown_entities["mentor"], "m1")


if __name__ == "__main__":
    unittest.main()
