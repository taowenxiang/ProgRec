import unittest

from skill3_mentor_discovery.graph_features import (
    compute_graph_confidence,
    trust_signals_for_candidates,
)
from skill3_mentor_discovery.graph_index import build_graph_index
from skill3_mentor_discovery.trust_signals import compute_trust_signals_for_student


class TrustSignalsTest(unittest.TestCase):
    def test_graph_confidence_downweights_low_trust_only_paths(self):
        strong_breakdown = {
            "interest_path_score": 0.6,
            "complementarity_path_score": 0.0,
            "project_path_score": 1.0,
            "advising_path_score": 1.0,
        }
        low_only_breakdown = {
            "interest_path_score": 0.0,
            "complementarity_path_score": 0.25,
            "project_path_score": 0.0,
            "advising_path_score": 0.0,
        }

        strong_confidence = compute_graph_confidence(strong_breakdown)
        low_only_confidence = compute_graph_confidence(low_only_breakdown)

        self.assertGreater(strong_confidence, low_only_confidence)
        self.assertAlmostEqual(low_only_confidence, 0.275, places=3)

    def test_compute_trust_signals_aggregates_project_and_advising_paths(self):
        graph = {
            "nodes": {
                "student": [{"student_id": "student-1"}],
                "project": [{"project_id": "project-1"}],
                "mentor": [{"mentor_id": "mentor-1"}, {"mentor_id": "mentor-2"}],
            },
            "edges": [
                {
                    "type": "project_participation",
                    "source": {"type": "student", "id": "student-1"},
                    "target": {"type": "project", "id": "project-1"},
                },
                {
                    "type": "project_leads",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "project", "id": "project-1"},
                },
                {
                    "type": "shared_interest",
                    "source": {"type": "student", "id": "student-1"},
                    "target": {"type": "student", "id": "student-2"},
                },
                {
                    "type": "advising",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "student", "id": "student-2"},
                },
                {
                    "type": "skill_complementarity",
                    "source": {"type": "student", "id": "student-1"},
                    "target": {"type": "student", "id": "student-3"},
                },
                {
                    "type": "advising",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "student", "id": "student-3"},
                },
            ],
        }

        signals = compute_trust_signals_for_student(
            "student-1",
            ["mentor-1", "mentor-2"],
            build_graph_index(graph),
        )

        mentor_1 = signals["mentor-1"]
        mentor_2 = signals["mentor-2"]

        self.assertGreater(mentor_1["personalized_proximity"], 0.0)
        self.assertGreater(mentor_1["meta_path_breakdown"]["project_path_score"], 0.0)
        self.assertGreater(mentor_1["meta_path_breakdown"]["advising_path_score"], 0.0)
        self.assertTrue(mentor_1["top_evidence_paths"])
        self.assertEqual(mentor_2["personalized_proximity"], 0.0)
        self.assertEqual(mentor_2["top_evidence_paths"], [])

    def test_compute_trust_signals_includes_inbound_student_edges_without_double_counting(self):
        graph = {
            "nodes": {
                "student": [
                    {"student_id": "student-1"},
                    {"student_id": "student-2"},
                    {"student_id": "student-3"},
                ],
                "mentor": [{"mentor_id": "mentor-1"}],
            },
            "edges": [
                {
                    "type": "shared_interest",
                    "source": {"type": "student", "id": "student-2"},
                    "target": {"type": "student", "id": "student-1"},
                },
                {
                    "type": "shared_interest",
                    "source": {"type": "student", "id": "student-1"},
                    "target": {"type": "student", "id": "student-2"},
                },
                {
                    "type": "advising",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "student", "id": "student-2"},
                },
                {
                    "type": "skill_complementarity",
                    "source": {"type": "student", "id": "student-3"},
                    "target": {"type": "student", "id": "student-1"},
                },
                {
                    "type": "advising",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "student", "id": "student-3"},
                },
            ],
        }

        signals = compute_trust_signals_for_student(
            "student-1",
            ["mentor-1"],
            build_graph_index(graph),
        )

        mentor_1 = signals["mentor-1"]

        self.assertEqual(mentor_1["meta_path_breakdown"]["interest_path_score"], 0.6)
        self.assertEqual(mentor_1["meta_path_breakdown"]["complementarity_path_score"], 0.25)
        self.assertEqual(mentor_1["meta_path_breakdown"]["advising_path_score"], 2.0)
        self.assertEqual(mentor_1["personalized_proximity"], 0.85)
        self.assertEqual(
            mentor_1["top_evidence_paths"],
            [
                "student -> shared_interest -> student -> advising <- mentor",
                "student -> skill_complementarity -> student -> advising <- mentor",
            ],
        )

    def test_trust_signals_helper_builds_index_and_preserves_default_shape(self):
        graph = {
            "nodes": {
                "student": [{"student_id": "student-1"}],
                "project": [{"project_id": "project-1"}],
                "mentor": [{"mentor_id": "mentor-1"}],
            },
            "edges": [
                {
                    "type": "project_participation",
                    "source": {"type": "student", "id": "student-1"},
                    "target": {"type": "project", "id": "project-1"},
                },
                {
                    "type": "project_leads",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "project", "id": "project-1"},
                },
            ],
        }

        signals = trust_signals_for_candidates("student-1", ["mentor-1"], graph)

        self.assertGreater(signals["mentor-1"]["personalized_proximity"], 0.0)
        self.assertEqual(
            signals["mentor-1"]["top_evidence_paths"],
            ["student -> project_participation -> project -> project_leads -> mentor"],
        )
        self.assertEqual(
            trust_signals_for_candidates("student-1", ["mentor-1"], None)["mentor-1"],
            {
                "personalized_proximity": 0.0,
                "meta_path_breakdown": {
                    "interest_path_score": 0.0,
                    "complementarity_path_score": 0.0,
                    "project_path_score": 0.0,
                    "advising_path_score": 0.0,
                },
                "top_evidence_paths": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
