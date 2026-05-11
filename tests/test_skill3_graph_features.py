import unittest
from pathlib import Path

from skill3_mentor_discovery.graph_features import (
    compute_mentor_authority,
    graph_features_for_mentors,
)
from skill3_mentor_discovery.graph_index import (
    build_graph_index,
    get_edge_trust_tier,
    get_edge_trust_weight,
)
from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.models import MentorCandidate
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class GraphFeatureTest(unittest.TestCase):
    def test_connected_mentors_receive_non_negative_authority(self):
        adjacency = {
            "mentor-1": {"mentor-2": 1.0},
            "mentor-2": {"mentor-1": 1.0, "mentor-3": 0.5},
            "mentor-3": {"mentor-2": 0.5},
        }

        authority = compute_mentor_authority(adjacency)

        self.assertIn("mentor-1", authority)
        self.assertGreaterEqual(authority["mentor-1"], 0.0)
        self.assertGreaterEqual(authority["mentor-2"], authority["mentor-3"])

    def test_graph_features_include_student_aware_fields_when_student_id_supplied(self):
        mentors = [
            {
                "mentor_id": "mentor-1",
                "name": "Mentor One",
                "department": "CS",
                "h_index": 20,
                "available_projects": [{"project_id": "project-1"}],
            },
            {
                "mentor_id": "mentor-2",
                "name": "Mentor Two",
                "department": "Math",
                "h_index": 5,
                "available_projects": [],
            },
        ]
        graph = {
            "nodes": {
                "student": [{"student_id": "student-1"}],
                "project": [{"project_id": "project-1"}],
                "mentor": mentors,
            },
            "edges": [
                {
                    "type": "collaboration",
                    "source": {"type": "mentor", "id": "mentor-1"},
                    "target": {"type": "mentor", "id": "mentor-2"},
                    "weight": 1.0,
                },
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

        features = graph_features_for_mentors(mentors, graph, student_id="student-1")

        mentor_1 = features["mentor-1"]
        mentor_2 = features["mentor-2"]
        self.assertIn("graph_confidence", mentor_1)
        self.assertIn("personalized_proximity", mentor_1)
        self.assertGreater(mentor_1["personalized_proximity"], 0.0)
        self.assertGreater(mentor_1["graph_confidence"], 0.0)
        self.assertEqual(mentor_1["network_proximity"], 0.0)
        self.assertEqual(mentor_1["centrality_score"], mentor_1["mentor_authority"])
        self.assertEqual(mentor_2["personalized_proximity"], 0.0)
        self.assertEqual(mentor_2["meta_path_breakdown"]["project_path_score"], 0.0)
        self.assertEqual(mentor_2["top_evidence_paths"], [])

    def test_build_graph_index_records_typed_adjacency_and_trust_lookup(self):
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

        index = build_graph_index(graph)

        self.assertEqual(
            index.forward_neighbors[("student", "student-1")]["project_participation"],
            [("project", "project-1")],
        )
        self.assertEqual(
            index.reverse_neighbors[("project", "project-1")]["project_leads"],
            [("mentor", "mentor-1")],
        )
        self.assertEqual(get_edge_trust_tier("project_participation"), "high")
        self.assertEqual(get_edge_trust_weight("project_participation"), 1.0)
        self.assertEqual(get_edge_trust_tier("skill_complementarity"), "low")
        self.assertEqual(get_edge_trust_weight("skill_complementarity"), 0.25)
        self.assertIsNone(get_edge_trust_tier("unknown_edge"))
        self.assertEqual(get_edge_trust_weight("unknown_edge"), 0.0)
        self.assertEqual(index.mentor_ids, {"mentor-1"})

    def test_ranked_candidates_include_graph_fields_and_reasons(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        mentor_ids = [mentor["mentor_id"] for mentor in resources.mentors[:3]]
        graph = {
            "nodes": {"mentor": resources.mentors[:3]},
            "edges": [
                {
                    "type": "collaboration",
                    "source": {"type": "mentor", "id": mentor_ids[0]},
                    "target": {"type": "mentor", "id": mentor_ids[1]},
                    "weight": 1.0,
                    "metadata": {},
                },
                {
                    "type": "topic_similarity",
                    "source": {"type": "mentor", "id": mentor_ids[1]},
                    "target": {"type": "mentor", "id": mentor_ids[2]},
                    "weight": 0.5,
                    "metadata": {},
                },
            ],
        }
        ranked = rank_mentors_for_student(
            resources.students[0],
            resources.mentors[:3],
            graph=graph,
            top_k=3,
        )
        first = ranked[0]
        self.assertIn("community_", first.community_id)
        self.assertGreaterEqual(first.final_score, 0.0)
        self.assertGreaterEqual(len(first.reasons), 1)
        self.assertTrue(first.reason_text)

    def test_mentor_candidate_to_dict_includes_trust_aware_fields(self):
        candidate = MentorCandidate(
            mentor_id="mentor-123",
            topic_score=0.9,
            graph_score=0.6,
            personalized_proximity=0.4,
            graph_confidence=0.8,
            mentor_authority=0.7,
            meta_path_breakdown={"shared_topic": 0.5, "collaboration": 0.3},
            top_evidence_paths=["student->topic->mentor", "student->peer->mentor"],
        )

        payload = candidate.to_dict()

        self.assertEqual(payload["personalized_proximity"], 0.4)
        self.assertEqual(payload["graph_confidence"], 0.8)
        self.assertEqual(payload["mentor_authority"], 0.7)
        self.assertEqual(
            payload["meta_path_breakdown"],
            {"shared_topic": 0.5, "collaboration": 0.3},
        )
        self.assertEqual(
            payload["top_evidence_paths"],
            ["student->topic->mentor", "student->peer->mentor"],
        )
        self.assertEqual(payload["reason_text"], "")
