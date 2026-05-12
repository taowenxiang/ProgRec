from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.schema import IntentFrame, SlotValue


class TestNLUSchema(unittest.TestCase):
    def test_intent_frame_defaults_to_empty_safe_collections(self) -> None:
        frame = IntentFrame(intent="recommendation_request")
        self.assertEqual(frame.target_types, [])
        self.assertEqual(frame.entities, {})
        self.assertEqual(frame.uncertain_fields, [])

    def test_slot_value_tracks_provenance(self) -> None:
        slot = SlotValue(value="graph", provenance="explicit")
        self.assertEqual(slot.value, "graph")
        self.assertEqual(slot.provenance, "explicit")


class TestDialogState(unittest.TestCase):
    def test_new_state_has_no_pending_question(self) -> None:
        state = DialogState()
        self.assertIsNone(state.pending_question)
        self.assertEqual(state.resolved_slots, {})

    def test_pending_question_carries_slot_binding(self) -> None:
        question = PendingQuestion(
            slot_name="profile_source",
            question="Should I use an existing student profile or build a temporary profile?",
            expected_answer_shape="existing_profile|temporary_profile",
        )
        self.assertEqual(question.slot_name, "profile_source")


if __name__ == "__main__":
    unittest.main()
