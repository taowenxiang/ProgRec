import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class GraphFeatureTest(unittest.TestCase):
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
