from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState
from progrec_agent.target_policy import infer_user_targets, is_tool_allowed_for_state


class TestTargetPolicy(unittest.TestCase):
    def test_infers_mentor_target(self) -> None:
        self.assertEqual(infer_user_targets("Help me find a mentor for NLP"), ["mentor"])

    def test_project_tool_blocked_for_mentor_only_request(self) -> None:
        state = DialogState(goal_targets=["mentor"], active_goal="mentor")

        self.assertFalse(is_tool_allowed_for_state("/project-teammate-discovery.recommend_projects", state))

    def test_project_tool_allowed_after_suggestion_acceptance(self) -> None:
        state = DialogState(
            goal_targets=["mentor"],
            active_goal="mentor",
            suggested_next_actions=[{"target": "project", "accepted": True}],
        )

        self.assertTrue(is_tool_allowed_for_state("/project-teammate-discovery.recommend_projects", state))


if __name__ == "__main__":
    unittest.main()
