from __future__ import annotations

from pathlib import Path

from skill.discovery import discover_projects_and_teammates
from skill.skill3_adapter import load_mentor_candidates


def test_pipeline_non_empty_with_mock_graph() -> None:
    root = Path(__file__).resolve().parents[1]
    graph_path = root / "data" / "mock_academic_graph.json"
    mock_projects = root / "data" / "mock_projects.json"
    mc = load_mentor_candidates(root / "data" / "mock_mentor_candidates.json")
    assert mc

    from skill.skill2_adapter import load_academic_graph

    graph = load_academic_graph(graph_path)
    assert graph

    students = [
        {
            "student_id": "student_a",
            "grade": "Senior",
            "major": "CS",
            "skills": ["python", "data analysis"],
            "interests": ["social network analysis"],
            "availability": "high",
        },
        {
            "student_id": "student_b",
            "grade": "Junior",
            "major": "Bio",
            "skills": ["statistics", "network analysis"],
            "interests": ["ecology", "social network analysis"],
            "availability": "moderate",
        },
    ]
    target = students[0]
    out = discover_projects_and_teammates(
        target_student_id=target["student_id"],
        target_student_profile=target,
        all_student_profiles=students,
        mentor_candidates=mc,
        graph=graph,
        mock_projects_path=mock_projects,
        top_n_projects=2,
        top_n_teammates=2,
        max_candidate_teammates=10,
        data_sources={"student_profiles": "test"},
    )
    assert out["target_student_id"] == "student_a"
    assert out["mentor_project_teammate_recommendations"]
    first = out["mentor_project_teammate_recommendations"][0]
    assert first.get("project_recommendations") is not None
    assert first.get("teammate_recommendations") is not None
    assert first["mentor_id"] == "m_001"
    assert first["mentor_base_score"] == 0.79
    assert first["topic_score"] == 0.82
    assert first["graph_score"] == 0.71
