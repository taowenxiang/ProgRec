from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState
from progrec_agent.runtime.turn_routing import apply_turn_routing, detect_explicit_targets, resolve_turn_targets


class TestTurnRouting(unittest.TestCase):
    def test_detect_explicit_targets_finds_project_keyword(self) -> None:
        targets = detect_explicit_targets("Can you show me projects too?")

        self.assertEqual(targets, ["project"])

    def test_affirmative_followup_accepts_first_suggested_target(self) -> None:
        state = DialogState(
            goal_targets=["mentor"],
            active_goal="mentor",
            suggested_next_actions=[
                {"target": "project", "label": "Find related projects"},
                {"target": "teammate", "label": "Find teammates"},
            ],
        )

        apply_turn_routing(state, "yes please")

        self.assertEqual(state.goal_targets, ["project"])
        self.assertEqual(state.active_goal, "project")
        self.assertTrue(state.suggested_next_actions[0]["accepted"])
        self.assertFalse(state.suggested_next_actions[1]["accepted"])

    def test_affirmative_followup_can_accept_multiple_suggestions(self) -> None:
        state = DialogState(
            goal_targets=["mentor"],
            active_goal="mentor",
            suggested_next_actions=[
                {"target": "project", "label": "Find related projects"},
                {"target": "teammate", "label": "Find teammates"},
            ],
        )

        targets = resolve_turn_targets(state, "yes, both please")

        self.assertEqual(targets, ["project", "teammate"])


if __name__ == "__main__":
    unittest.main()
