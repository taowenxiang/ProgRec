from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState, ExecutionContext
from progrec_agent.planning.planner_v2 import build_execution_plan


class TestPlannerV2(unittest.TestCase):
    def test_existing_student_plan_uses_student_runtime(self) -> None:
        state = DialogState(
            task="recommend_existing_student",
            resolved_slots={"student_id": "jamie-taylor-00008", "mode": "graph"},
            missing_slots=[],
        )
        plan = build_execution_plan(state)
        self.assertEqual(plan.action, "run_existing_profile_recommendation")

    def test_top_mentor_followup_uses_inspection_runtime(self) -> None:
        state = DialogState(
            task="inspect_recommendation",
            execution_context=ExecutionContext(result_handle="result-1"),
            resolved_slots={"entity_type": "mentor", "rank": 1},
            missing_slots=[],
        )
        plan = build_execution_plan(state)
        self.assertEqual(plan.action, "inspect_ranked_entity")


if __name__ == "__main__":
    unittest.main()
