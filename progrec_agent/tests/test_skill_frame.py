from __future__ import annotations

import unittest
from pathlib import Path

from progrec_agent.nlu.skill_frame import validate_skill_frame_payload
from progrec_agent.skill_catalog import build_skill_catalog


class TestSkillAwareFrame(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = build_skill_catalog(Path("."))

    def test_validates_recommendation_payload_with_candidate_skills(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": ["program_type", "experience_level"],
                "confidence": 0.92,
                "reasoning_summary": "Mentor recommendation request with a temporary profile.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertEqual(frame.slots["research_topic"].value, "NLP and trustworthy AI")
        self.assertIn("/mentor-discovery", frame.candidate_skills)

    def test_rejects_unknown_skill_and_tool_names(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {},
                "candidate_skills": ["/made-up-skill"],
                "candidate_tools": ["delete_everything"],
                "missing_information": [],
                "confidence": 0.88,
                "reasoning_summary": "Invalid tool proposal.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("unknown_skill:/made-up-skill", frame.validation_errors)
        self.assertIn("unknown_tool:delete_everything", frame.validation_errors)

    def test_invalid_mode_is_not_accepted(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_existing_student",
                "target_types": ["mentor"],
                "slots": {"mode": {"value": "production", "provenance": "explicit"}},
                "candidate_skills": ["/mentor-discovery"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.8,
                "reasoning_summary": "Bad mode.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("invalid_mode:production", frame.validation_errors)


if __name__ == "__main__":
    unittest.main()
