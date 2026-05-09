import unittest
from pathlib import Path

from skill3_mentor_discovery.evaluate import evaluate_recall_at_k


class EvaluateTest(unittest.TestCase):
    def test_recall_metric_returns_expected_keys(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_recall_at_k(repo_root, top_k=5, sample_size=5)
        self.assertIn("recall_at_k", summary)
        self.assertIn("evaluated_students", summary)
