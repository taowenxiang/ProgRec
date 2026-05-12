from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestAgentCoreV2(unittest.TestCase):
    def test_missing_required_slot_returns_clarification_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.8,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find me a mentor.")
            self.assertIn("existing student profile", reply)
            self.assertIsNotNone(state.pending_question)

    def test_followup_answer_updates_state_instead_of_restarting_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())
            state = DialogState(
                task="recommend_existing_student",
                pending_question=core._make_pending_question("mode"),
            )
            reply, updated = core.handle_message(state, "graph")
            self.assertIn("student_id", reply)
            self.assertEqual(updated.resolved_slots["mode"], "graph")


if __name__ == "__main__":
    unittest.main()
