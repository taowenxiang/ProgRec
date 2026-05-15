from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.nlu.parser import parse_user_message


class TestNLUParser(unittest.TestCase):
    def test_missing_llm_uses_domain_fallback_for_mentor_request(self) -> None:
        frame = parse_user_message(
            "Help me find a mentor for NLP and trustworthy AI.",
            dialog_state=None,
            llm_client=None,
        )
        self.assertEqual(frame.intent, "recommendation_request")
        self.assertEqual(frame.entities["profile_source"].value, "temporary_profile")
        self.assertEqual(frame.constraints["research_topic"].value, "NLP and trustworthy AI")

    def test_invalid_llm_payload_uses_domain_fallback_for_project_request(self) -> None:
        llm = Mock()
        llm.complete_json.side_effect = ValueError("bad json")
        frame = parse_user_message(
            "Recommend projects about graph neural networks.",
            dialog_state=None,
            llm_client=llm,
        )
        self.assertEqual(frame.intent, "recommendation_request")
        self.assertEqual(frame.constraints["research_topic"].value, "graph neural networks")

    def test_parse_extracts_student_id_and_mode(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "intent": "recommendation_request",
            "target_types": ["mentor", "project", "teammate"],
            "entities": {
                "student_id": {"value": "jamie-taylor-00008", "provenance": "explicit"},
                "mode": {"value": "graph", "provenance": "explicit"},
            },
            "constraints": {},
            "preferences": {},
            "references": {},
            "confidence": 0.95,
            "uncertain_fields": [],
            "possible_conflicts": [],
        }
        frame = parse_user_message(
            "Recommend mentors for student_id jamie-taylor-00008 in graph mode.",
            dialog_state=None,
            llm_client=llm,
        )
        self.assertEqual(frame.entities["student_id"].value, "jamie-taylor-00008")
        self.assertEqual(frame.entities["mode"].value, "graph")

    def test_invalid_mode_becomes_recommendation_fallback_frame(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "intent": "recommendation_request",
            "target_types": ["mentor"],
            "entities": {"mode": {"value": "production", "provenance": "explicit"}},
            "constraints": {},
            "preferences": {},
            "references": {},
            "confidence": 0.6,
            "uncertain_fields": [],
            "possible_conflicts": [],
        }
        frame = parse_user_message("use production mode", dialog_state=None, llm_client=llm)
        self.assertEqual(frame.intent, "recommendation_request")
        self.assertIn("mode", frame.uncertain_fields)

    def test_skill_aware_parser_returns_candidate_skills_and_slots(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.return_value = {
            "turn_type": "domain_task",
            "task": "recommend_temporary_profile",
            "target_types": ["mentor"],
            "slots": {
                "profile_source": {"value": "temporary_profile", "provenance": "inferred"},
                "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"},
            },
            "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
            "candidate_tools": ["recommend_full_pipeline"],
            "missing_information": ["program_type", "experience_level"],
            "confidence": 0.91,
            "reasoning_summary": "The user wants a mentor recommendation for a temporary profile.",
        }

        frame = parse_skill_aware_user_message(
            "Help me find a mentor for NLP and trustworthy AI.",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertEqual(frame.slots["research_topic"].value, "NLP and trustworthy AI")
        self.assertIn("/mentor-discovery", frame.candidate_skills)

    def test_skill_aware_parser_prompt_includes_full_skill_docs(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.return_value = {
            "turn_type": "domain_task",
            "task": "recommend_temporary_profile",
            "target_types": ["mentor"],
            "slots": {
                "research_topic": {"value": "NLP", "provenance": "explicit"},
            },
            "selected_skills": ["/mentor-discovery"],
            "selected_tools": ["recommend_full_pipeline"],
            "missing_information": ["program_type", "experience_level"],
            "confidence": 0.9,
            "reasoning_summary": "Selected Skill 3 from the full skill docs.",
        }

        parse_skill_aware_user_message(
            "Help me find an NLP mentor.",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        prompt = llm.complete_json.call_args.args[0]
        self.assertIn("# Mentor Discovery (Skill 3)", prompt)
        self.assertIn("# Skill 4", prompt)
        self.assertIn("# Student Recommendation Ranker", prompt)

    def test_skill_aware_parser_accepts_selected_skill_aliases(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.return_value = {
            "turn_type": "domain_task",
            "task": "recommend_temporary_profile",
            "target_types": ["mentor"],
            "slots": {
                "research_topic": {"value": "NLP", "provenance": "explicit"},
            },
            "selected_skills": ["/mentor-discovery", "/social-ranking"],
            "selected_tools": ["recommend_full_pipeline"],
            "missing_information": ["program_type", "experience_level"],
            "confidence": 0.9,
            "reasoning_summary": "The user wants mentor recommendations.",
        }

        frame = parse_skill_aware_user_message(
            "Help me find an NLP mentor.",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertEqual(frame.candidate_skills, ["/mentor-discovery", "/social-ranking"])
        self.assertEqual(frame.candidate_tools, ["recommend_full_pipeline"])

    def test_skill_aware_parser_recovers_domain_request_misclassified_as_invalid_task(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.side_effect = [
            {
                "turn_type": "unsupported",
                "task": "unsupported",
                "target_types": [],
                "slots": {},
                "candidate_skills": [],
                "candidate_tools": [],
                "missing_information": [],
                "confidence": 0.8,
                "reasoning_summary": "No matching tool.",
            },
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"},
                },
                "selected_skills": ["/mentor-discovery", "/social-ranking"],
                "selected_tools": ["recommend_full_pipeline"],
                "missing_information": ["program_type", "experience_level"],
                "confidence": 0.92,
                "reasoning_summary": "Skill 3 and Skill 5 apply to a mentor recommendation request.",
            },
        ]

        frame = parse_skill_aware_user_message(
            "Help me find a mentor for NLP and trustworthy AI.",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(llm.complete_json.call_count, 1)
        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertIn("/mentor-discovery", frame.candidate_skills)

    def test_skill_aware_parser_recovers_vague_invalid_task_without_keyword_match(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.side_effect = [
            {
                "turn_type": "unsupported",
                "task": "unsupported",
                "target_types": [],
                "slots": {},
                "selected_skills": [],
                "selected_tools": [],
                "missing_information": [],
                "confidence": 0.77,
                "reasoning_summary": "No matching tool.",
            },
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["teammate"],
                "slots": {
                    "research_topic": {"value": "cohort collaboration planning", "provenance": "explicit"},
                },
                "selected_skills": ["/project-teammate-discovery"],
                "selected_tools": ["recommend_full_pipeline"],
                "missing_information": ["program_type", "experience_level"],
                "confidence": 0.88,
                "reasoning_summary": "Skill 4 applies because the user is asking about collaborator discovery.",
            },
        ]

        frame = parse_skill_aware_user_message(
            "Could the local skills help with cohort collaboration planning?",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(llm.complete_json.call_count, 1)
        self.assertEqual(frame.task, "recommendation_request")
        self.assertEqual(frame.candidate_tools, ["recommend_full_pipeline"])

    def test_skill_aware_parser_falls_back_to_recommendation_on_llm_error(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.side_effect = ValueError("bad upstream json")

        frame = parse_skill_aware_user_message(
            "what is the weather today?",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(frame.task, "recommendation_request")
        self.assertIn("llm_parse_error", frame.validation_errors)

if __name__ == "__main__":
    unittest.main()
