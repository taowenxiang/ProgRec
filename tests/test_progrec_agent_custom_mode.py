from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator


def test_custom_profile_mode_returns_results_without_existing_student_id(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=tmp_path)

    result = orchestrator.recommend_for_profile(
        {
            "student_id": "cli-custom-001",
            "grade": "Junior",
            "major": "Computer Science",
            "skills": ["python", "network analysis"],
            "interests": ["social computing", "mentoring systems"],
            "experience_summary": "Built data and recommendation course projects.",
            "availability": "moderate",
            "resume_text": "",
        },
        top_k=3,
    )

    assert result["mode"] == "custom_profile_mode"
    assert result["student_profile"]["student_id"] == "cli-custom-001"
    assert result["skill3_result"]["mentor_candidates"]
    assert result["skill4_result"]["mentor_project_teammate_recommendations"]
    assert result["skill5_result"]["recommendations"]["mentors"]
