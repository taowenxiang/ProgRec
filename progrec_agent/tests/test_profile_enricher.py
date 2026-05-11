from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.profile_enricher import build_profiles_from_text


class TestProfileEnricher(unittest.TestCase):
    def test_build_profiles_from_text(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "goal": "find a trustworthy ai mentor",
            "research_direction": ["trustworthy ai", "nlp"],
            "constraints": {"time_budget_hours_per_week": 3},
            "preferences": {"prefer_low_commitment": True},
            "skill_profile": {
                "grade": "Junior",
                "major": "Computer Science",
                "skills": ["python"],
                "interests": ["nlp"],
                "experience_summary": "Built class projects",
                "availability": "low",
            },
        }
        skill_profile, agent_profile = build_profiles_from_text("I want NLP and low commitment", llm)
        self.assertEqual(skill_profile["major"], "Computer Science")
        self.assertEqual(skill_profile["skills"], ["python"])
        self.assertTrue(agent_profile.preferences["prefer_low_commitment"])
        self.assertEqual(agent_profile.constraints["time_budget_hours_per_week"], 3)


if __name__ == "__main__":
    unittest.main()
