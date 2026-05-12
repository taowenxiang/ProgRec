from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState
from progrec_agent.policy.clarification import choose_next_question
from progrec_agent.policy.readiness import compute_readiness


class TestClarificationPolicy(unittest.TestCase):
    def test_existing_student_request_needs_student_id_before_mode(self) -> None:
        state = DialogState(task="recommend_existing_student", resolved_slots={})
        state = compute_readiness(state)
        question = choose_next_question(state)
        self.assertEqual(question.slot_name, "student_id")

    def test_missing_mode_is_asked_after_student_id(self) -> None:
        state = DialogState(task="recommend_existing_student", resolved_slots={"student_id": "jamie-taylor-00008"})
        state = compute_readiness(state)
        question = choose_next_question(state)
        self.assertEqual(question.slot_name, "mode")


if __name__ == "__main__":
    unittest.main()
