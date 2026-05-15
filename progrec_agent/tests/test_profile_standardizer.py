from __future__ import annotations

import unittest

from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


class TestProfileStandardizer(unittest.TestCase):
    def test_standardizes_chat_slots_for_skill3(self) -> None:
        profile = standardize_temporary_profile(
            {
                "profile_source": "temporary_profile",
                "research_topic": "NLP and trustworthy AI",
                "program_type": "undergraduate research",
                "experience_level": "intermediate",
                "skills": ["python", "machine learning"],
                "availability": "low",
            }
        )

        self.assertTrue(str(profile["student_id"]).startswith("chat-temp-"))
        self.assertEqual(profile["grade"], "unknown")
        self.assertEqual(profile["major"], "unknown")
        self.assertEqual(profile["skills"], ["python", "machine learning"])
        self.assertEqual(profile["interests"], ["nlp", "trustworthy ai"])
        self.assertEqual(profile["availability"], "low")
        self.assertIn("undergraduate research", profile["experience_summary"])
        self.assertIn("intermediate", profile["experience_summary"])

    def test_defaults_missing_optional_fields(self) -> None:
        profile = standardize_temporary_profile({"research_topic": "graph neural networks"})

        self.assertEqual(profile["skills"], [])
        self.assertEqual(profile["interests"], ["graph neural networks"])
        self.assertEqual(profile["availability"], "moderate")
        self.assertEqual(profile["major"], "unknown")


if __name__ == "__main__":
    unittest.main()
