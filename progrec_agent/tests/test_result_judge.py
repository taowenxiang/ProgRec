from __future__ import annotations

import unittest

from progrec_agent.result_judge import judge_results


class TestResultJudge(unittest.TestCase):
    def test_flags_rerun_for_empty_projects(self) -> None:
        verdict = judge_results(
            skill5_result={"recommendations": {"mentors": [1], "projects": [], "teammates": [1]}},
            strategy={"max_reruns": 2},
            rerun_count=0,
        )
        self.assertTrue(verdict["rerun_needed"])
        self.assertIn("project coverage too small", verdict["reasons"])


if __name__ == "__main__":
    unittest.main()
