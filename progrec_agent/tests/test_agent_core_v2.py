from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestAgentCoreV2(unittest.TestCase):
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
                "arguments": {"profile_context": "Computer vision"},
                "reasoning_summary": "Malformed profile context.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "help me find a mentor in Computer vision")

        self.assertIn("more profile context", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.execution_context.next_question, reply)


if __name__ == "__main__":
    unittest.main()
