from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class _StubExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, tool_name: str, arguments: dict[str, object], *, session):
        self.calls.append((tool_name, arguments))
        from progrec_agent.agent_schema import ToolExecutionResult

        return ToolExecutionResult(tool_name=tool_name, ok=True, payload={"tool_name": tool_name})


class TestAgentCore(unittest.TestCase):
    def test_recommend_message_executes_safe_tool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("tool_name", reply)

    def test_rebuild_message_creates_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Rebuild the graph artifacts")
            self.assertIn("Do you want me to continue", reply)
            self.assertIsNotNone(session.pending_confirmation_action)


if __name__ == "__main__":
    unittest.main()
