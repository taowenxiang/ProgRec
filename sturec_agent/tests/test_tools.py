from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from sturec_agent.tools import AgentTools


class TestAgentTools(unittest.TestCase):
    @patch("sturec_agent.tools.run_skill3")
    def test_run_mentor_discovery_tool(self, mock_skill3) -> None:
        mock_skill3.return_value = {"student_id": "s1", "mentor_candidates": []}
        tools = AgentTools(repo_root=Path("."), temp_dir=Path("."))
        result = tools.run_mentor_discovery_tool({"student_id": "s1"}, top_k=5)
        self.assertEqual(result["student_id"], "s1")


if __name__ == "__main__":
    unittest.main()
