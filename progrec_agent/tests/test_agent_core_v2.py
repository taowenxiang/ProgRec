from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestAgentCoreV2(unittest.TestCase):
    def test_domain_request_misclassified_by_llm_still_asks_clarification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "unsupported",
                "target_types": [],
                "entities": {},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.0,
                "uncertain_fields": [],
                "possible_conflicts": ["llm_misclassified_domain_request"],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Help me find a mentor for NLP and trustworthy AI.")

            self.assertNotIn("I can only help", reply)
            self.assertIn("program", reply.lower())
            self.assertEqual(state.task, "recommend_temporary_profile")
            self.assertEqual(state.resolved_slots["research_topic"], "NLP and trustworthy AI")

    def test_temporary_profile_source_with_topic_alias_asks_next_profile_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {"profile_source": {"value": "temporary_profile", "provenance": "explicit"}},
                "constraints": {"topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"}},
                "preferences": {},
                "references": {},
                "confidence": 0.9,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Help me find a mentor for NLP and trustworthy AI.")
            self.assertIn("program", reply.lower())
            self.assertEqual(state.task, "recommend_temporary_profile")
            self.assertEqual(state.resolved_slots["research_topic"], "NLP and trustworthy AI")

    def test_existing_profile_source_asks_for_student_id_instead_of_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {"profile_source": {"value": "existing_profile", "provenance": "explicit"}},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.9,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Use an existing student profile to find mentors.")
            self.assertIn("student_id", reply)
            self.assertEqual(state.task, "recommend_existing_student")

    def test_followup_inspects_latest_ranked_mentor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "inspect_recommendation",
                "target_types": ["mentor"],
                "entities": {"entity_type": {"value": "mentor", "provenance": "explicit"}},
                "constraints": {},
                "preferences": {},
                "references": {"rank": {"value": 1, "provenance": "explicit"}},
                "confidence": 0.9,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            inspection = Mock()
            inspection.get_ranked_entity.return_value = {
                "rank": 1,
                "mentor_id": "m_101",
                "mentor_name": "Dr. Ada",
                "final_score": 0.97,
            }
            core = AgentCoreV2(
                repo_root=Path("."),
                temp_dir=Path(td),
                llm_client=llm,
                inspection_runtime=inspection,
            )
            state = DialogState(
                task="inspect_recommendation",
                resolved_slots={"entity_type": "mentor", "rank": 1},
            )
            state.execution_context.result_handle = "latest"
            state.execution_context.last_result = {
                "skill5_result": {
                    "recommendations": {
                        "mentors": [
                            {
                                "rank": 1,
                                "mentor_id": "m_101",
                                "mentor_name": "Dr. Ada",
                                "final_score": 0.97,
                            }
                        ]
                    }
                }
            }

            reply, _updated = core.handle_message(state, "Show me the top mentor.")

            self.assertIn("Dr. Ada", reply)
            inspection.get_ranked_entity.assert_called_once()

    def test_missing_required_slot_returns_clarification_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.8,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find me a mentor.")
            self.assertIn("existing student profile", reply)
            self.assertIsNotNone(state.pending_question)

    def test_followup_answer_updates_state_instead_of_restarting_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())
            state = DialogState(
                task="recommend_existing_student",
                pending_question=core._make_pending_question("mode"),
            )
            reply, updated = core.handle_message(state, "graph")
            self.assertIn("student_id", reply)
            self.assertEqual(updated.resolved_slots["mode"], "graph")

    def test_full_temporary_profile_answer_continues_after_profile_source_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.8,
                "uncertain_fields": ["profile_source"],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            first_reply, state = core.handle_message(
                DialogState(),
                "Help me find a mentor for NLP and trustworthy AI.",
            )

            second_reply, updated = core.handle_message(
                state,
                "build a temporary profile from your description",
            )

            self.assertIn("existing student profile", first_reply)
            self.assertNotIn("I can help with mentor", second_reply)
            self.assertEqual(updated.task, "recommend_temporary_profile")
            self.assertEqual(updated.resolved_slots["profile_source"], "temporary_profile")
            self.assertIn("research_topic", updated.missing_slots)

    def test_skill_aware_parser_runs_complete_temporary_profile_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
                "skill4_result": {"target_student_id": "chat-temp-1"},
                "skill5_result": {
                    "recommendations": {"mentors": [{"rank": 1}], "projects": [], "teammates": []}
                },
            }
            llm = Mock()
            llm.complete_json.return_value = {
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
                "reasoning_summary": "Complete temporary mentor request.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, state = core.handle_message(DialogState(), "Find an NLP mentor for undergraduate research.")

            self.assertIn("recommendation pipeline", reply)
            self.assertEqual(state.task, "recommend_temporary_profile")
            runtime.run_recommendation_for_profile.assert_called_once()
            self.assertTrue(state.skill_trace)

    def test_meta_question_answers_from_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "meta_question",
                "task": "answer_meta_question",
                "target_types": [],
                "slots": {},
                "candidate_skills": [],
                "candidate_tools": [],
                "missing_information": [],
                "confidence": 0.95,
                "reasoning_summary": "User asked which skills were used.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            state = DialogState(skill_trace=[{"skill_id": "/mentor-discovery", "summary": "Ranked mentor candidates."}])

            reply, updated = core.handle_message(state, "Which skills did you use?")

            self.assertIn("/mentor-discovery", reply)
            self.assertEqual(updated.execution_context.last_turn_type, "meta_answer")

    def test_weather_question_stays_in_agent_loop_without_running_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "unsupported",
                "task": "unsupported",
                "target_types": [],
                "slots": {},
                "candidate_skills": [],
                "candidate_tools": [],
                "missing_information": [],
                "confidence": 0.99,
                "reasoning_summary": "No registered skill was selected.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, updated = core.handle_message(DialogState(), "What is the weather today?")

            self.assertIn("existing student profile", reply)
            runtime.run_recommendation_for_profile.assert_not_called()
            self.assertEqual(updated.execution_context.last_turn_type, "clarification")

    def test_validate_resources_records_graph_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            validation = Mock()
            validation.validate_resources.return_value = {
                "mode": "graph",
                "students_path": "students.json",
                "mentors_path": "mentors.json",
                "graph_path": "academic_graph.json",
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "resource_validation",
                "task": "validate_resources",
                "target_types": [],
                "slots": {"mode": {"value": "graph", "provenance": "explicit"}},
                "candidate_skills": ["/academic-graph"],
                "candidate_tools": ["debug_graph_mode"],
                "missing_information": [],
                "confidence": 0.92,
                "reasoning_summary": "User wants graph resources validated.",
            }
            core = AgentCoreV2(
                repo_root=Path("."),
                temp_dir=Path(td),
                llm_client=llm,
                validation_runtime=validation,
            )

            reply, state = core.handle_message(DialogState(), "Validate graph mode resources.")

            self.assertIn("validated", reply.lower())
            self.assertEqual(state.skill_trace[0]["skill_id"], "/academic-graph")


if __name__ == "__main__":
    unittest.main()
