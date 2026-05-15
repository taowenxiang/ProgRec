from __future__ import annotations

import unittest

from progrec_agent.contracts.capability_schema import CapabilityContract, CapabilityInput


class TestCapabilitySchema(unittest.TestCase):
    def test_action_contract_formats_prompt_context(self) -> None:
        contract = CapabilityContract(
            capability_id="/mentor-discovery.recommend_mentors",
            kind="action",
            owner_skill="/mentor-discovery",
            when_to_use="Use when a student profile is ready and the user wants mentor recommendations.",
            requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
            returns="mentor_result",
            can_follow=["student_profile"],
            followups=["/mentor-discovery.get_mentor_by_rank"],
            failure_modes=["missing_profile"],
            executor_binding="mentor_discovery.run_recommend_mentors",
        )

        prompt_line = contract.to_prompt_block()

        self.assertIn("/mentor-discovery.recommend_mentors", prompt_line)
        self.assertIn("kind: action", prompt_line)
        self.assertIn("student_profile_ref", prompt_line)


if __name__ == "__main__":
    unittest.main()
