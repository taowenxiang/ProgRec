from __future__ import annotations

import unittest

from progrec_agent.intent_router import route_user_message


class TestIntentRouter(unittest.TestCase):
    def test_recommend_keywords_route_to_recommend(self) -> None:
        decision = route_user_message("Find me an NLP mentor", llm_client=None, session=None)
        self.assertEqual(decision.intent, "recommend")
        self.assertIn("recommend_full_pipeline", decision.candidate_tools)

    def test_rebuild_keywords_route_to_rebuild(self) -> None:
        decision = route_user_message("Rebuild the graph artifacts", llm_client=None, session=None)
        self.assertEqual(decision.intent, "rebuild")
        self.assertIn("rebuild_skill2_graph", decision.candidate_tools)


if __name__ == "__main__":
    unittest.main()
