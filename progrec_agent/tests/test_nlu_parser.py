from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.nlu.parser import parse_user_message


class TestNLUParser(unittest.TestCase):
    def test_parse_extracts_student_id_and_mode(self) -> None:
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
        frame = parse_user_message(
            "Recommend mentors for student_id jamie-taylor-00008 in graph mode.",
            dialog_state=None,
            llm_client=llm,
        )
        self.assertEqual(frame.entities["student_id"].value, "jamie-taylor-00008")
        self.assertEqual(frame.entities["mode"].value, "graph")

    def test_invalid_mode_becomes_safe_out_of_scope_frame(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "intent": "recommendation_request",
            "target_types": ["mentor"],
            "entities": {"mode": {"value": "production", "provenance": "explicit"}},
            "constraints": {},
            "preferences": {},
            "references": {},
            "confidence": 0.6,
            "uncertain_fields": [],
            "possible_conflicts": [],
        }
        frame = parse_user_message("use production mode", dialog_state=None, llm_client=llm)
        self.assertEqual(frame.intent, "out_of_scope")
        self.assertIn("mode", frame.uncertain_fields)


if __name__ == "__main__":
    unittest.main()
