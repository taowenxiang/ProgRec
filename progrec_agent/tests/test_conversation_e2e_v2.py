from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
