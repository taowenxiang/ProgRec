from __future__ import annotations

import unittest

from progrec_agent.strategy import build_strategy


class TestStrategy(unittest.TestCase):
    def test_build_strategy_from_preferences(self) -> None:
        strategy = build_strategy(
            {"constraints": {"time_budget_hours_per_week": 3}, "preferences": {"prefer_diversity": True}}
        )
        self.assertTrue(strategy["prefer_diversity"])
        self.assertTrue(strategy["prefer_low_commitment"])
        self.assertEqual(strategy["top_k"], 5)


if __name__ == "__main__":
    unittest.main()
