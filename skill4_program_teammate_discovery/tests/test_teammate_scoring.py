from __future__ import annotations

from pathlib import Path

from skill.skill2_adapter import build_edge_index, load_academic_graph
from skill.teammate_scoring import (
    compute_graph_relation_score,
    compute_teammate_score,
    edges_between_students,
)


def test_teammate_score_bounds() -> None:
    s = compute_teammate_score(0.5, 0.5, 0.7, graph_relation_score=0.0, has_graph_signal=False)
    assert 0.0 <= s <= 1.0
    s2 = compute_teammate_score(0.5, 0.5, 0.7, graph_relation_score=0.8, has_graph_signal=True)
    assert 0.0 <= s2 <= 1.0


def test_graph_relation_from_edges() -> None:
    edges = [{"edge_type": "shared_interest", "weight": 1.0}]
    assert compute_graph_relation_score(edges) > 0.5


def test_edges_between_students_mock_index() -> None:
    g = load_academic_graph(Path(__file__).resolve().parents[1] / "data" / "mock_academic_graph.json")
    assert g
    ctx = {"edge_index": build_edge_index(g)}
    e = edges_between_students(ctx, "student_a", "student_b")
    assert len(e) >= 1
