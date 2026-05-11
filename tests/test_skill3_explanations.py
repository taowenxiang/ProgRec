from __future__ import annotations

import unittest
from unittest.mock import Mock

from skill3_mentor_discovery.explanations import (
    build_reason_evidence,
    fallback_reason_text,
    generate_reason_text,
)
from skill3_mentor_discovery.models import MentorCandidate


class TestSkill3Explanations(unittest.TestCase):
    def test_reason_evidence_keeps_top_graph_inputs(self) -> None:
        mentor = {"mentor_id": "m_1", "name": "Dr. Ada"}
        evidence = build_reason_evidence(
            mentor=mentor,
            overlap_terms={"nlp", "summarization"},
            community_id="community_0",
            activity_score=0.6,
            meta_path_breakdown={"project_path_score": 0.4, "interest_path_score": 0.1},
            graph_confidence=0.8,
            top_evidence_paths=["student->project->mentor"],
            topic_score=0.7,
            graph_score=0.5,
            personalized_proximity=0.4,
            mentor_authority=0.3,
        )
        self.assertEqual(evidence["mentor_name"], "Dr. Ada")
        self.assertEqual(evidence["top_evidence_paths"], ["student->project->mentor"])
        self.assertEqual(evidence["graph_confidence"], 0.8)

    def test_mentor_candidate_includes_reason_text(self) -> None:
        candidate = MentorCandidate(
            mentor_id="m_1",
            mentor_name="Dr. Ada",
            topic_score=0.8,
            reason_text="Topic fit is strong.",
        )
        payload = candidate.to_dict()
        self.assertEqual(payload["reason_text"], "Topic fit is strong.")

    def test_generate_reason_text_uses_llm_output(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "reason_text": "This mentor fits because topic overlap and project-path evidence are both strong."
        }
        text = generate_reason_text(
            {
                "mentor_name": "Dr. Ada",
                "overlap_terms": ["nlp"],
                "graph_confidence": 0.8,
                "top_evidence_paths": ["student->project->mentor"],
                "meta_path_breakdown": {"project_path_score": 0.4},
            },
            llm_client=llm,
        )
        self.assertIn("project-path evidence", text)

    def test_generate_reason_text_falls_back_without_llm(self) -> None:
        text = generate_reason_text(
            {
                "overlap_terms": ["nlp", "summarization"],
                "graph_confidence": 0.6,
                "top_evidence_paths": ["student->project->mentor"],
            },
            llm_client=None,
        )
        self.assertEqual(text, fallback_reason_text(
            {
                "overlap_terms": ["nlp", "summarization"],
                "graph_confidence": 0.6,
                "top_evidence_paths": ["student->project->mentor"],
            }
        ))


if __name__ == "__main__":
    unittest.main()
