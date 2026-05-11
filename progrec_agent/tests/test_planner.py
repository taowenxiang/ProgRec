from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.planner import build_execution_plan


class TestPlanner(unittest.TestCase):
    def test_requests_clarification_when_slots_missing(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "need_clarification": True,
            "clarification_questions": [{"key": "time_budget", "question": "How many hours per week?"}],
            "tool_plan": {"run_skill3": False, "run_skill4": False, "run_skill5": False},
        }
        plan = build_execution_plan({"goal": "find a mentor"}, llm)
        self.assertTrue(plan.need_clarification)
        self.assertEqual(plan.clarification_questions[0].key, "time_budget")
        self.assertFalse(plan.run_skill3)


if __name__ == "__main__":
    unittest.main()
