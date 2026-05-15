from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_actions import PlannerAction
from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState
from progrec_agent.runtime.turn_execution import handle_ask_user_action, handle_terminal_action


class TestTurnExecution(unittest.TestCase):
    def test_handle_ask_user_action_sets_pending_question_and_clarification_state(self) -> None:
        state = DialogState(active_goal="mentor")
        action = PlannerAction(
            action="ask_user",
            message="Tell me about your background.",
            pending_slot="profile_context",
            expected_answer_shape="free_text_profile",
        )

        outcome = handle_ask_user_action(
            state=state,
            action=action,
            user_text="Find me a mentor.",
        )

        self.assertTrue(outcome.handled)
        self.assertEqual(outcome.reply_text, "Tell me about your background.")
        self.assertEqual(state.pending_question.slot_name, "profile_context")
        self.assertEqual(state.execution_context.last_turn_type, "clarification")

    def test_handle_terminal_action_uses_fallback_for_suggest_next_steps(self) -> None:
        state = DialogState()
        state.execution_context.last_turn_type = "recommendation_result"
        state.tool_results_summary = {"project_count": 2}
        action = PlannerAction(
            action="suggest_next_steps",
            suggested_next_actions=[{"target": "teammate", "label": "Find teammates"}],
        )

        outcome = handle_terminal_action(state=state, action=action)

        self.assertTrue(outcome.handled)
        self.assertIn("2 project", outcome.reply_text)
        self.assertIn("teammates", outcome.reply_text.lower())

    def test_agent_core_uses_extracted_turn_execution_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "Help me find a mentor for NLP.")

        self.assertIn("background", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")


if __name__ == "__main__":
    unittest.main()
