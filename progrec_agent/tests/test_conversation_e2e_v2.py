from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestConversationE2EV2(unittest.TestCase):
    def test_existing_student_graph_request_runs_runtime_after_required_slots_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_student_id.return_value = {
                "skill5_result": {
                    "recommendations": {"mentors": [1] * 5, "projects": [1] * 4, "teammates": [1] * 5}
                }
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor", "project", "teammate"],
                "entities": {
                    "student_id": {"value": "jamie-taylor-00008", "provenance": "explicit"},
                    "mode": {"value": "graph", "provenance": "explicit"},
                },
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.95,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)
            reply, _state = core.handle_message(
                DialogState(task="recommend_existing_student"),
                "Run graph mode for jamie-taylor-00008",
            )
            self.assertIn("recommendation pipeline", reply)
            runtime.run_recommendation_for_student_id.assert_called_once()
            self.assertEqual(_state.execution_context.last_turn_type, "recommendation_result")

    def test_clarification_turn_records_structured_turn_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {"profile_source": {"value": "temporary_profile", "provenance": "explicit"}},
                "constraints": {"research_topic": {"value": "NLP", "provenance": "explicit"}},
                "preferences": {},
                "references": {},
                "confidence": 0.9,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find an NLP mentor.")
            self.assertIn("program", reply.lower())
            self.assertEqual(state.execution_context.last_turn_type, "clarification")
            self.assertEqual(state.execution_context.next_question, reply)

    def test_existing_graph_fixture_declares_expected_clarification_sequence(self) -> None:
        path = Path("progrec_agent/tests/fixtures/conversations/existing_graph_recommendation.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["expected_plan_action"], "run_existing_profile_recommendation")
        self.assertEqual(payload["turns"][0]["speaker"], "user")


if __name__ == "__main__":
    unittest.main()
