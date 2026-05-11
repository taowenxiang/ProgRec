from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent import repl
from progrec_agent.session import AgentSession


class TestReplAgentFlow(unittest.TestCase):
    @patch("builtins.input", side_effect=["I want an NLP mentor", "exit"])
    @patch("progrec_agent.repl.AgentCore")
    def test_free_text_is_delegated_to_agent_core(self, mock_core, _mock_input) -> None:
        mock_core.return_value.handle_message.return_value = "Here are the top matches."
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_core.return_value.handle_message.assert_called_once()

    @patch("builtins.input", side_effect=["show trace", "exit"])
    @patch("builtins.print")
    def test_show_trace_without_history(self, mock_print, _mock_input) -> None:
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("No trace available.", printed)

    def test_session_tracks_pending_confirmation_state(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_pending_confirmation(
                {
                    "action_id": "confirm-1",
                    "tool_name": "rebuild_skill2_graph",
                    "arguments": {},
                    "prompt": "Confirm rebuild?",
                }
            )
            self.assertEqual(session.pending_confirmation_action["tool_name"], "rebuild_skill2_graph")


if __name__ == "__main__":
    unittest.main()
