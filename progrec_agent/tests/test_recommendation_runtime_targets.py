from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from progrec_agent.runtime import recommendation_runtime


class TestRecommendationRuntimeTargets(unittest.TestCase):
    def test_mentor_only_profile_does_not_run_skill4_or_skill5(self) -> None:
        profile = {
            "student_id": "chat-temp-1",
            "grade": "undergraduate",
            "major": "computer science",
            "skills": ["nlp"],
            "interests": ["trustworthy ai"],
            "experience_summary": "medium experience",
            "availability": "summer research",
        }

        with tempfile.TemporaryDirectory() as td:
            fake_orchestrator = Mock()
            fake_orchestrator.rank_mentors_for_profile.return_value = {
                "mode": "custom_profile_mode",
                "student_profile": profile,
                "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
            }
            with patch(
                "progrec_agent.runtime.recommendation_runtime.ProgRecOrchestrator",
                return_value=fake_orchestrator,
            ):
                result = recommendation_runtime.run_mentor_recommendation_for_profile(
                    repo_root=Path("."),
                    temp_dir=Path(td),
                    profile=profile,
                    top_k=5,
                )

        fake_orchestrator.rank_mentors_for_profile.assert_called_once()
        self.assertIn("skill3_result", result)
        self.assertNotIn("skill4_result", result)
        self.assertNotIn("skill5_result", result)


if __name__ == "__main__":
    unittest.main()
