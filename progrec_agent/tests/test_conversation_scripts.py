from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class TestConversationScripts(unittest.TestCase):
    @patch("progrec_agent.tool_executor.ToolExecutor.execute")
    def test_recommendation_flow_mentions_recommendations(self, mock_execute) -> None:
        from progrec_agent.agent_schema import ToolExecutionResult

        mock_execute.return_value = ToolExecutionResult(
            tool_name="recommend_full_pipeline",
            ok=True,
            payload={
                "skill5_result": {
                    "recommendations": {"mentors": [1] * 5, "projects": [1] * 5, "teammates": [1] * 5}
                }
            },
        )
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), llm_client=None)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("recommendation", reply.lower())

    def test_confirmation_decline_clears_pending_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.pending_confirmation_action = {
                "action_id": "a1",
                "tool_name": "rebuild_skill2_graph",
                "arguments": {},
                "prompt": "confirm?",
            }
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), llm_client=None)
            reply = core.handle_message(session, "no")
            self.assertIn("won't run", reply.lower())
            self.assertIsNone(session.pending_confirmation_action)


if __name__ == "__main__":
    unittest.main()
