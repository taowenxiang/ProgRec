from __future__ import annotations

import unittest

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.merge import merge_intent_frame
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.schema import IntentFrame, SlotValue


class TestDialogMerge(unittest.TestCase):
    def test_merge_promotes_explicit_entities_to_resolved_slots(self) -> None:
        state = DialogState()
        frame = IntentFrame(
            intent="recommendation_request",
            entities={"student_id": SlotValue(value="jamie-taylor-00008", provenance="explicit")},
        )
        merged = merge_intent_frame(state, frame)
        self.assertEqual(merged.resolved_slots["student_id"], "jamie-taylor-00008")

    def test_apply_pending_answer_updates_bound_slot(self) -> None:
        state = DialogState(
            pending_question=PendingQuestion(
                slot_name="mode",
                question="Use demo or graph mode?",
                expected_answer_shape="demo|graph",
            )
        )
        updated = apply_pending_answer(state, "graph")
        self.assertEqual(updated.resolved_slots["mode"], "graph")
        self.assertIsNone(updated.pending_question)


if __name__ == "__main__":
    unittest.main()
