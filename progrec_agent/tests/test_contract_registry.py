from __future__ import annotations

import unittest

from progrec_agent.contracts.registry import get_capability, list_capabilities, planner_capability_context


class TestContractRegistry(unittest.TestCase):
    def test_registry_exposes_action_and_inspect_capabilities(self) -> None:
        capability_ids = [item.capability_id for item in list_capabilities()]

        self.assertIn("/student-profiling.build_temporary_profile", capability_ids)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", capability_ids)
        self.assertIn("/project-teammate-discovery.recommend_projects", capability_ids)
        self.assertIn("/social-ranking.rerank_bundle", capability_ids)

    def test_planner_context_mentions_followups(self) -> None:
        context = planner_capability_context()

        self.assertIn("/mentor-discovery.recommend_mentors", context)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", context)
        self.assertIn("followups", context)

    def test_legacy_alias_resolves_to_canonical_contract(self) -> None:
        contract = get_capability("/mentor-discovery.rank_mentors")

        self.assertEqual(contract.capability_id, "/mentor-discovery.recommend_mentors")


if __name__ == "__main__":
    unittest.main()
