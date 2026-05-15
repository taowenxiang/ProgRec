from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestConversationE2EV2(unittest.TestCase):
    def test_mentor_only_conversation_uses_planner_clarification(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "action": "ask_user",
            "message": "Tell me your background and target opportunity.",
        }
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find me an NLP mentor.")

        self.assertIn("background", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.planner_actions[0]["action"], "ask_user")


if __name__ == "__main__":
    unittest.main()
