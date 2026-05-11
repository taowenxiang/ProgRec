from progrec_agent.render import render_mentor_detail, render_summary


def test_render_summary_contains_mode_and_sections() -> None:
    summary = render_summary(
        {
            "mode": "dataset_mode",
            "student_profile": {"student_id": "jamie-taylor-00008"},
            "skill5_result": {
                "recommendations": {
                    "mentors": [{"rank": 1, "mentor_id": "m_001", "final_score": 0.88}],
                    "projects": [{"rank": 1, "project_id": "p_001", "final_score": 0.73}],
                    "teammates": [{"rank": 1, "student_id": "s_015", "final_score": 0.69}],
                }
            },
        }
    )

    assert "dataset_mode" in summary
    assert "Top Mentors" in summary
    assert "Top Projects" in summary
    assert "Top Teammates" in summary


def test_render_mentor_detail_includes_projects_and_teammates() -> None:
    text = render_mentor_detail(
        mentor={
            "mentor_id": "m_001",
            "mentor_name": "Ada",
            "final_score": 0.88,
            "explanation": "Strong topic alignment.",
        },
        skill4_bundle={
            "project_recommendations": [{"project_id": "p_001", "title": "Graph Lab"}],
            "teammate_recommendations": [{"student_id": "s_010", "reason": "Complementary skills"}],
        },
    )

    assert "m_001" in text
    assert "Graph Lab" in text
    assert "s_010" in text
