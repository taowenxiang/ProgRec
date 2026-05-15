from __future__ import annotations

import unittest

from progrec_agent.response.composer import compose_fallback_reply


class TestResponseComposer(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
