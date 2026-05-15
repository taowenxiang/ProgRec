from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestConversationE2EV2(unittest.TestCase):
    def test_mentor_only_conversation_uses_planner_clarification(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "action": "ask_user",
            "message": "Tell me your background and target opportunity.",
        }
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find me an NLP mentor.")

        self.assertIn("background", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.planner_actions[0]["action"], "ask_user")

    def test_answer_to_profile_clarification_updates_context_before_reasking(self) -> None:
        prompts: list[str] = []

        def complete_json(prompt: str) -> dict[str, object]:
            prompts.append(prompt)
            if len(prompts) == 1:
                return {
                    "action": "ask_user",
                    "message": "Tell me about your background and research interests.",
                    "pending_slot": "profile_context",
                    "expected_answer_shape": "free_text_profile",
                }
            if len(prompts) == 2:
                if '"raw_profile_text": "I am an ug and I am interested in object detection"' not in prompt:
                    return {
                        "action": "ask_user",
                        "message": "Tell me about your background and research interests.",
                        "pending_slot": "profile_context",
                        "expected_answer_shape": "free_text_profile",
                    }
                return {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.update_profile_context",
                    "arguments": {
                        "profile_context": {
                            "program_type": "undergraduate",
                            "research_topic": "object detection",
                        }
                    },
                }
            return {
                "action": "ask_user",
                "message": "What kind of mentorship are you looking for?",
                "pending_slot": "mentorship_preference",
                "expected_answer_shape": "short_text",
            }

        llm = Mock()
        llm.complete_json.side_effect = complete_json
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            _, state = core.handle_message(DialogState(), "Help me find a CV mentor.")
            reply, state = core.handle_message(state, "I am an ug and I am interested in object detection")

        self.assertEqual(state.profile_context["program_type"], "undergraduate")
        self.assertEqual(state.profile_context["research_topic"], "object detection")
        self.assertEqual(reply, "What kind of mentorship are you looking for?")
        self.assertNotEqual(reply, "Tell me about your background and research interests.")

    def test_followup_projects_reuses_existing_profile_and_mentor_refs(self) -> None:
        llm = Mock()
        llm.complete_json.side_effect = [
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.recommend_projects",
                "arguments": {
                    "student_profile_ref": "sp_001",
                    "mentor_result_ref": "rr_mentor_001",
                    "top_k": 5,
                },
                "reasoning_summary": "Use the last profile and mentor result to expand into projects.",
            },
            {
                "action": "suggest_next_steps",
                "message": "I found related projects. Want teammate matches too?",
                "suggested_next_actions": [{"target": "teammate", "label": "Find teammates"}],
                "reasoning_summary": "Projects are now available.",
            },
        ]
        runtime = Mock()
        runtime.run_project_recommendations_for_profile.return_value = {
            "projects": [{"project_id": "p1"}, {"project_id": "p2"}],
        }
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)
            state = DialogState()
            state.goal_targets = ["project"]
            state.active_goal = "project"
            state.execution_context.latest_result_refs = {
                "student_profile": "sp_001",
                "mentor_result": "rr_mentor_001",
            }
            state.execution_context.result_ref_payloads = {
                "sp_001": {"result_ref": "sp_001", "payload": {"profile": {"student_id": "chat-temp-1"}}},
                "rr_mentor_001": {"result_ref": "rr_mentor_001", "payload": {"skill3_result": {"mentor_candidates": []}}},
            }

            reply, updated = core.handle_message(state, "Recommend projects too.")

        self.assertIn("projects", reply.lower())
        self.assertEqual(updated.tool_results_summary["project_count"], 2)


if __name__ == "__main__":
    unittest.main()
