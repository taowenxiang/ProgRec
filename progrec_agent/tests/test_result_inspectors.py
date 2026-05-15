from __future__ import annotations

import unittest

from progrec_agent.inspectors.bundle_result_inspector import show_bundle_summary
from progrec_agent.inspectors.mentor_result_inspector import get_mentor_by_rank
from progrec_agent.inspectors.project_result_inspector import get_project_by_rank
from progrec_agent.inspectors.teammate_result_inspector import get_teammate_by_rank


class TestResultInspectors(unittest.TestCase):
    def test_get_mentor_by_rank_returns_first_candidate_profile(self) -> None:
        mentor_result = {
            "result_ref": "rr_mentor_001",
            "payload": {
                "skill3_result": {
                    "mentor_candidates": [
                        {"mentor_id": "m1", "mentor_name": "Prof A", "rank": 1},
                        {"mentor_id": "m2", "mentor_name": "Prof B", "rank": 2},
                    ]
                }
            },
        }

        card = get_mentor_by_rank(mentor_result, rank=1)

        self.assertEqual(card["mentor_id"], "m1")
        self.assertEqual(card["rank"], 1)

    def test_get_project_by_rank_reads_project_payload(self) -> None:
        project_result = {
            "payload": {
                "projects": [
                    {"project_id": "p1", "title": "Project One"},
                    {"project_id": "p2", "title": "Project Two"},
                ]
            }
        }

        card = get_project_by_rank(project_result, rank=2)

        self.assertEqual(card["project_id"], "p2")
        self.assertEqual(card["rank"], 2)

    def test_get_teammate_by_rank_reads_teammate_payload(self) -> None:
        teammate_result = {
            "payload": {
                "teammates": [
                    {"student_id": "s1", "name": "A"},
                    {"student_id": "s2", "name": "B"},
                ]
            }
        }

        card = get_teammate_by_rank(teammate_result, rank=1)

        self.assertEqual(card["student_id"], "s1")
        self.assertEqual(card["rank"], 1)

    def test_show_bundle_summary_prefers_final_recommendation(self) -> None:
        bundle_result = {
            "payload": {
                "final_recommendation": {
                    "summary": {"mentor_count": 3},
                }
            }
        }

        summary = show_bundle_summary(bundle_result)

        self.assertEqual(summary["summary"]["mentor_count"], 3)


if __name__ == "__main__":
    unittest.main()
