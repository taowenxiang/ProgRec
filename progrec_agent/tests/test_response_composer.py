from __future__ import annotations

import unittest

from progrec_agent.response.composer import compose_fallback_reply, compose_mentor_matches_reply


class TestResponseComposer(unittest.TestCase):
    def test_composes_mentor_result_reply_with_scores_and_reasons(self) -> None:
        reply = compose_mentor_matches_reply(
            preamble="I found 2 mentor recommendations for you.",
            mentor_result_payload={
                "skill3_result": {
                    "mentor_candidates": [
                        {
                            "mentor_id": "m1",
                            "mentor_name": "Prof Ada",
                            "final_score": 0.91,
                            "reasons": ["Strong NLP overlap.", "Good graph evidence."],
                        },
                        {
                            "mentor_id": "m2",
                            "mentor_name": "Prof Turing",
                            "final_score": 0.84,
                            "reason": "Strong project-path evidence.",
                        },
                    ]
                }
            },
            suggested_next_actions=[{"target": "project", "label": "Find related projects"}],
        )

        self.assertIn("Prof Ada", reply)
        self.assertIn("0.91", reply)
        self.assertIn("Strong NLP overlap.", reply)
        self.assertIn("related projects", reply.lower())

    def test_composes_mentor_result_reply(self) -> None:
        reply = compose_fallback_reply(
            turn_type="recommendation_result",
            tool_results_summary={"mentor_count": 2},
            suggested_next_actions=[{"target": "project", "label": "Find related projects"}],
        )

        self.assertIn("2 mentor", reply)
        self.assertIn("projects", reply.lower())

    def test_uses_question_for_clarification(self) -> None:
        reply = compose_fallback_reply(
            turn_type="clarification",
            next_question="What background should I use for your profile?",
            tool_results_summary={},
            suggested_next_actions=[],
        )

        self.assertEqual(reply, "What background should I use for your profile?")

    def test_composes_project_result_reply(self) -> None:
        reply = compose_fallback_reply(
            turn_type="recommendation_result",
            tool_results_summary={"project_count": 3},
            suggested_next_actions=[{"target": "teammate", "label": "Find teammates"}],
        )

        self.assertIn("3 project", reply)
        self.assertIn("teammates", reply.lower())


if __name__ == "__main__":
    unittest.main()
