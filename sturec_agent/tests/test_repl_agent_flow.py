from __future__ import annotations

import unittest
from unittest.mock import patch

from sturec_agent import repl


class TestReplAgentFlow(unittest.TestCase):
    @patch("builtins.input", side_effect=["I want an NLP mentor", "exit"])
    @patch("sturec_agent.repl.run_agent_turn")
    def test_free_text_enters_agent_flow(self, mock_turn, _mock_input) -> None:
        mock_turn.return_value = "summary"
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_turn.assert_called_once()

    @patch("builtins.input", side_effect=["show trace", "exit"])
    @patch("builtins.print")
    def test_show_trace_without_history(self, mock_print, _mock_input) -> None:
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("No trace available.", printed)


if __name__ == "__main__":
    unittest.main()
