import unittest
from pathlib import Path

from skill3_mentor_discovery.evaluate import (
    _graph_for_variant,
    _drop_random_edge_subset,
    evaluate_ablation_summary,
    evaluate_perturbation_summary,
    evaluate_recall_at_k,
)


class EvaluateTest(unittest.TestCase):
    def test_random_edge_drop_is_seeded(self):
        graph = {
            "nodes": {},
            "edges": [
                {
                    "type": f"edge_{index}",
                    "source": {"type": "mentor", "id": f"m{index}"},
                    "target": {"type": "mentor", "id": f"m{index + 1}"},
                }
                for index in range(10)
            ],
        }

        first = _drop_random_edge_subset(graph, seed=7)
        second = _drop_random_edge_subset(graph, seed=7)

        self.assertEqual(first, second)
        self.assertLess(len(first["edges"]), len(graph["edges"]))

    def test_recall_metric_returns_expected_keys(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_recall_at_k(repo_root, top_k=5, sample_size=5)
        self.assertIn("recall_at_k", summary)
        self.assertIn("evaluated_students", summary)

    def test_ablation_summary_contains_expected_variants(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_ablation_summary(repo_root, top_k=5, sample_size=5)
        self.assertEqual(
            set(summary),
            {
                "topic_only",
                "topic_plus_authority",
                "topic_plus_personalized_graph",
                "topic_plus_personalized_graph_plus_trust",
            },
        )

    def test_perturbation_summary_contains_expected_variants(self):
        repo_root = Path(__file__).resolve().parents[1]
        summary = evaluate_perturbation_summary(repo_root, top_k=5, sample_size=5)
        self.assertEqual(
            set(summary),
            {
                "baseline_top_k_overlap",
                "drop_low_trust_edges_top_k_overlap",
                "random_edge_drop_top_k_overlap",
            },
        )

    def test_graph_variant_preparation_preserves_student_local_trust_slice(self):
        graph = {
            "nodes": {
                "mentor": [{"mentor_id": "m_1"}, {"mentor_id": "m_2"}],
                "student": [{"student_id": "s_target"}, {"student_id": "s_peer"}],
                "project": [{"project_id": "p_1"}],
            },
            "edges": [
                {
                    "type": "collaboration",
                    "source": {"type": "mentor", "id": "m_1"},
                    "target": {"type": "mentor", "id": "m_2"},
                },
                {
                    "type": "project_participation",
                    "source": {"type": "student", "id": "s_target"},
                    "target": {"type": "project", "id": "p_1"},
                },
                {
                    "type": "project_leads",
                    "source": {"type": "mentor", "id": "m_1"},
                    "target": {"type": "project", "id": "p_1"},
                },
                {
                    "type": "shared_interest",
                    "source": {"type": "student", "id": "s_target"},
                    "target": {"type": "student", "id": "s_peer"},
                },
                {
                    "type": "advising",
                    "source": {"type": "mentor", "id": "m_2"},
                    "target": {"type": "student", "id": "s_peer"},
                },
            ],
        }

        prepared_graph = _graph_for_variant(
            graph,
            "topic_plus_personalized_graph_plus_trust",
            student_id="s_target",
        )

        self.assertIsNotNone(prepared_graph)
        edge_types = [edge["type"] for edge in prepared_graph["edges"]]
        self.assertIn("project_participation", edge_types)
        self.assertIn("project_leads", edge_types)
        self.assertIn("shared_interest", edge_types)
        self.assertIn("advising", edge_types)
