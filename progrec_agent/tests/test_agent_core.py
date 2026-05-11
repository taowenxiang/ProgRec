from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

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
    def test_session_records_last_action_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            session.set_last_action(kind="answer_only", tool_name="", tool_arguments={}, result_summary="answered meta")
            self.assertEqual(session.last_action_kind, "answer_only")
            self.assertEqual(session.last_action_result_summary, "answered meta")
            self.assertIsNotNone(core)

    def test_session_clears_last_action_on_reset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_last_action(
                kind="execute_tool",
                tool_name="recommend_full_pipeline",
                tool_arguments={},
                result_summary="ran",
            )
            session.reset()
            self.assertIsNone(session.last_action_kind)
            self.assertIsNone(session.last_tool_name)

    def test_recommend_message_executes_safe_tool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("recommendation pipeline", reply)

    def test_rebuild_message_creates_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Rebuild the graph artifacts")
            self.assertIn("Do you want me to continue", reply)
            self.assertIsNotNone(session.pending_confirmation_action)

    def test_llm_router_failure_falls_back_to_local_routing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            llm_client = Mock()
            llm_client.complete_json.side_effect = RuntimeError("HTTP Error 500")
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm_client)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("couldn't safely classify", reply)
            self.assertEqual(executor.calls, [])

    def test_unknown_llm_tool_name_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            llm_client = Mock()
            llm_client.complete_json.return_value = {
                "message_type": "domain_task",
                "intent": "recommend_mentor",
                "confidence": 0.99,
                "candidate_tools": ["MentorSearch"],
                "in_scope": True,
                "needs_clarification": False,
                "clarification_question": "",
                "answer_only": False,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "",
                "reasoning_summary": "Use MentorSearch",
            }
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm_client)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("more detail", reply)
            self.assertEqual(executor.calls, [])

    def test_meta_question_is_answered_without_tool_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_last_action(
                kind="clarify_then_wait",
                tool_name="",
                tool_arguments={},
                result_summary="Do you want to use an existing student_id, or should I build a short profile from your interests?",
            )
            llm = Mock()
            llm.complete_json.return_value = {
                "message_type": "meta_question",
                "intent": "ask_last_action",
                "confidence": 0.97,
                "candidate_tools": [],
                "in_scope": True,
                "needs_clarification": False,
                "clarification_question": "",
                "answer_only": True,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "",
                "reasoning_summary": "Session meta-question.",
            }
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm)
            reply = core.handle_message(session, "Which skill did you use just now?")
            self.assertIn("clarification question", reply)
            self.assertEqual(executor.calls, [])

    def test_out_of_scope_question_is_refused_without_tool_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            llm = Mock()
            llm.complete_json.return_value = {
                "message_type": "out_of_scope",
                "intent": "out_of_scope_other",
                "confidence": 0.99,
                "candidate_tools": [],
                "in_scope": False,
                "needs_clarification": False,
                "clarification_question": "",
                "answer_only": True,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "That question is outside ProgRec's recommendation scope.",
                "reasoning_summary": "Out of scope.",
            }
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm)
            reply = core.handle_message(session, "What is the weather today?")
            self.assertIn("outside ProgRec", reply)
            self.assertEqual(executor.calls, [])


if __name__ == "__main__":
    unittest.main()
