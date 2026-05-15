from __future__ import annotations

import unittest

from progrec_agent.contracts.result_refs import ResultReference, ResultRegistry


class TestResultRefs(unittest.TestCase):
    def test_registry_tracks_latest_refs_by_result_type(self) -> None:
        registry = ResultRegistry()
        mentor_ref = ResultReference(
            result_ref="rr_mentor_001",
            result_type="mentor_result",
            owner_skill="/mentor-discovery",
            session_id="sess_1",
            input_refs=["sp_001"],
            summary={"count": 2, "top_ids": ["m1", "m2"]},
            followups=["/mentor-discovery.get_mentor_by_rank"],
            payload={"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]}},
        )

        registry.store(mentor_ref)

        self.assertEqual(registry.latest_ref("mentor_result"), "rr_mentor_001")
        self.assertEqual(registry.get("rr_mentor_001").summary["count"], 2)


if __name__ == "__main__":
    unittest.main()
