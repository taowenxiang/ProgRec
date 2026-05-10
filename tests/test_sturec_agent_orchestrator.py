from pathlib import Path

from sturec_agent.orchestrator import StuRecOrchestrator


def test_dataset_mode_returns_ranked_results(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    orchestrator = StuRecOrchestrator(repo_root=repo_root, temp_dir=tmp_path)

    result = orchestrator.recommend_for_student_id("jamie-taylor-00008", top_k=3)

    assert result["mode"] == "dataset_mode"
    assert result["student_profile"]["student_id"] == "jamie-taylor-00008"
    assert len(result["skill3_result"]["mentor_candidates"]) == 3
    assert result["skill4_result"]["mentor_project_teammate_recommendations"]
    assert result["skill5_result"]["recommendations"]["mentors"]
