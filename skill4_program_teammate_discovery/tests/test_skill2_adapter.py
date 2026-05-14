from __future__ import annotations

from pathlib import Path

from skill.skill2_adapter import (
    build_edge_index,
    extract_projects_for_mentor,
    load_academic_graph,
    standardize_project_record,
)


def _mock_graph_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "mock_academic_graph.json"


def test_load_academic_graph() -> None:
    g = load_academic_graph(_mock_graph_path())
    assert g is not None
    assert len(g["nodes"]["mentor"]) == 2


def test_build_edge_index_counts() -> None:
    g = load_academic_graph(_mock_graph_path())
    assert g
    idx = build_edge_index(g)
    assert "project_leads" in idx["edges_by_type"]
    assert len(idx["edges_by_type"]["project_leads"]) == 2
    mkey = "mentor:m_001"
    out = idx["outgoing_by_source"].get(mkey, [])
    assert any(e["edge_type"] == "project_leads" for e in out)


def test_extract_projects_for_mentor_both_directions() -> None:
    g = load_academic_graph(_mock_graph_path())
    assert g
    p1 = extract_projects_for_mentor(g, "m_001")
    ids1 = {x["project_id"] for x in p1}
    assert "p_001" in ids1
    p2 = extract_projects_for_mentor(g, "m_002")
    ids2 = {x["project_id"] for x in p2}
    assert "p_003" in ids2


def test_standardize_project_resolves_topic_ids() -> None:
    g = load_academic_graph(_mock_graph_path())
    assert g
    row = next(p for p in g["nodes"]["project"] if p["project_id"] == "p_001")
    std = standardize_project_record(g, row, "m_001")
    assert "social network analysis" in std["topic_tags"]
