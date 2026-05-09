import unittest
from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


class RetrievalTest(unittest.TestCase):
    def test_returns_ranked_topic_candidates(self):
        repo_root = Path(__file__).resolve().parents[1]
        resources = load_standardized_resources(repo_root)
        result = rank_mentors_for_student(resources.students[0], resources.mentors, top_k=5)
        self.assertEqual(len(result), 5)
        self.assertGreaterEqual(result[0].topic_score, result[-1].topic_score)
