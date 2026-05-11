from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent import repl
from progrec_agent.session import AgentSession


class TestReplAgentFlow(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"PROGREC_AGENT_API_KEY": "prog-key", "PROGREC_AGENT_MODEL": "demo-model"},
        clear=True,
    )
    @patch("builtins.input", side_effect=["I want an NLP mentor", "quit"])
    @patch("progrec_agent.repl.AgentCore")
    def test_free_text_is_delegated_to_agent_core(self, mock_core, _mock_input) -> None:
        mock_core.return_value.handle_message.return_value = "Here are the top matches."
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_core.return_value.handle_message.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    def test_main_raises_when_llm_is_not_configured(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "LLM"):
            repl.main()

    @patch.dict(
        os.environ,
        {"PROGREC_AGENT_API_KEY": "prog-key", "PROGREC_AGENT_MODEL": "demo-model"},
        clear=True,
    )
    @patch("builtins.input", side_effect=["quit"])
    @patch("builtins.print")
    def test_main_prints_chat_first_intro(self, mock_print, _mock_input) -> None:
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("You can talk to me naturally", printed)
        self.assertNotIn("Commands:", printed)

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

    @patch.dict(
        os.environ,
        {
            "PROGREC_AGENT_API_KEY": "prog-key",
            "PROGREC_AGENT_MODEL": "demo-model",
            "PROGREC_AGENT_BASE_URL": "https://llm.example.com",
        },
        clear=True,
    )
    def test_build_llm_client_from_env_reads_key_model_and_base_url(self) -> None:
        client = repl._build_llm_client_from_env()
        assert client is not None
        self.assertEqual(client.config.api_key, "prog-key")
        self.assertEqual(client.config.model, "demo-model")
        self.assertEqual(client.config.endpoint, "https://llm.example.com/v1/responses")


if __name__ == "__main__":
    unittest.main()
