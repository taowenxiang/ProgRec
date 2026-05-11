from __future__ import annotations

import unittest

from sturec_agent.explainer import build_final_response


class TestExplainer(unittest.TestCase):
    def test_build_final_response_includes_trace(self) -> None:
        text = build_final_response(
            agent_profile={"goal": "find mentor"},
            skill5_result={"recommendations": {"mentors": [], "projects": [], "teammates": []}},
            decision_trace=["Asked for clarification", "Reran with diversity bias"],
        )
        self.assertIn("Goal: find mentor", text)
        self.assertIn("Reran with diversity bias", text)


if __name__ == "__main__":
    unittest.main()
