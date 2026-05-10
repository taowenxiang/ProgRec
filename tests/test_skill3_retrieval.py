import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class RetrievalTest(unittest.TestCase):
    def test_returns_enriched_ranked_candidates(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        result = rank_mentors_for_student(
            resources.students[0],
            resources.mentors,
            graph=resources.graph,
            top_k=5,
        )

        self.assertEqual(len(result), 5)
        self.assertGreaterEqual(result[0].final_score, result[-1].final_score)
        self.assertIsInstance(result[0].meta_path_breakdown, dict)
        self.assertIn("interest_path_score", result[0].meta_path_breakdown)
        self.assertGreaterEqual(result[0].graph_confidence, 0.0)

    def test_accepts_candidate_pool_size_and_returns_top_k(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)

        result = rank_mentors_for_student(
            resources.students[0],
            resources.mentors,
            graph=resources.graph,
            top_k=4,
            candidate_pool_size=7,
        )

        self.assertEqual(len(result), 4)
