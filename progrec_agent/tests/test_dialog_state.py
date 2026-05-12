from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState, ExecutionContext, PendingQuestion


class TestDialogStateObjects(unittest.TestCase):
    def test_execution_context_defaults_are_empty(self) -> None:
        ctx = ExecutionContext()
        self.assertIsNone(ctx.result_handle)
        self.assertIsNone(ctx.selected_entity_type)
        self.assertIsNone(ctx.selected_entity_id)

    def test_dialog_state_defaults_are_safe(self) -> None:
        state = DialogState()
        self.assertEqual(state.task, "")
        self.assertEqual(state.goal, "")
        self.assertEqual(state.required_slots, [])
        self.assertEqual(state.missing_slots, [])
        self.assertEqual(state.conflicts, [])

    def test_dialog_state_accepts_pending_question(self) -> None:
        state = DialogState(
            pending_question=PendingQuestion(
                slot_name="mode",
                question="Should I use demo mode or graph mode?",
                expected_answer_shape="demo|graph",
            )
        )
        self.assertEqual(state.pending_question.slot_name, "mode")


if __name__ == "__main__":
    unittest.main()
