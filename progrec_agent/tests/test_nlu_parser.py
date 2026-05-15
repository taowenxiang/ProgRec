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

    def test_invalid_mode_becomes_safe_out_of_scope_frame(self) -> None:
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
        self.assertEqual(frame.intent, "out_of_scope")
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

    def test_skill_aware_parser_falls_back_to_out_of_scope_on_llm_error(self) -> None:
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

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("llm_parse_error", frame.validation_errors)

    def test_skill_aware_parser_overrides_llm_out_of_scope_for_domain_request(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.return_value = {
            "turn_type": "out_of_scope",
            "task": "out_of_scope",
            "target_types": [],
            "slots": {},
            "candidate_skills": [],
            "candidate_tools": [],
            "missing_information": [],
            "confidence": 0.96,
            "reasoning_summary": "Incorrectly classified as unrelated.",
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


if __name__ == "__main__":
    unittest.main()
