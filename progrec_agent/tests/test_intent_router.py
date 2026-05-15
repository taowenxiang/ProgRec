from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.intent_router import route_user_message


class TestIntentRouter(unittest.TestCase):
    def test_recommend_keywords_route_to_recommend(self) -> None:
        decision = route_user_message("Find me an NLP mentor", llm_client=None, session=None)
        self.assertEqual(decision.intent, "recommend_mentor")
        self.assertIn("recommend_full_pipeline", decision.candidate_tools)

    def test_mentor_profile_request_routes_to_inspect(self) -> None:
        decision = route_user_message(
            "Show me the current profile of the first mentor you recommend",
            llm_client=None,
            session=None,
        )
        self.assertEqual(decision.intent, "inspect_current_mentor")
        self.assertEqual(decision.candidate_tools, ["show_recommended_mentor_profile"])

    def test_rebuild_keywords_route_to_rebuild(self) -> None:
        decision = route_user_message("Rebuild the graph artifacts", llm_client=None, session=None)
        self.assertEqual(decision.intent, "rebuild_graph")
        self.assertIn("rebuild_skill2_graph", decision.candidate_tools)

    def test_llm_meta_question_routes_to_answer_only(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "message_type": "meta_question",
            "intent": "ask_last_action",
            "confidence": 0.96,
            "candidate_tools": [],
            "needs_clarification": False,
            "clarification_question": "",
            "answer_only": True,
            "tool_name": "",
            "tool_arguments": {},
            "meta_reply": "I only asked a clarification question in the last turn.",
            "reasoning_summary": "This is a session meta-question.",
        }
        decision = route_user_message("Which skill did you use just now?", llm_client=llm, session=None)
        self.assertEqual(decision.message_type, "meta_question")
        self.assertTrue(decision.answer_only)

    def test_llm_invalid_route_is_coerced_to_clarification(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "message_type": "unsupported",
            "intent": "unsupported",
            "confidence": 0.99,
            "candidate_tools": [],
            "needs_clarification": False,
            "clarification_question": "",
            "answer_only": True,
            "tool_name": "",
            "tool_arguments": {},
            "meta_reply": "",
            "reasoning_summary": "The user asked about weather.",
        }
        decision = route_user_message("How is the weather today?", llm_client=llm, session=None)
        self.assertEqual(decision.message_type, "domain_task")
        self.assertTrue(decision.needs_clarification)


if __name__ == "__main__":
    unittest.main()
