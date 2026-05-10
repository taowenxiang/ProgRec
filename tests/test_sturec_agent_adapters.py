from pathlib import Path

from sturec_agent.adapters.skill1_adapter import normalize_manual_profile
from sturec_agent.adapters.skill2_adapter import resolve_skill2_resources


def test_normalize_manual_profile_splits_lists_and_adds_temp_id() -> None:
    profile = normalize_manual_profile(
        {
            "grade": "Senior",
            "major": "Computer Science",
            "skills": "python, data analysis, python",
            "interests": "nlp, social computing",
            "experience_summary": "Built a chatbot for class.",
            "availability": "High",
            "resume_text": "",
        }
    )

    assert profile["student_id"].startswith("cli-custom-")
    assert profile["skills"] == ["python", "data analysis"]
    assert profile["interests"] == ["nlp", "social computing"]
    assert profile["availability"] == "high"


def test_resolve_skill2_resources_prefers_outputs_bundle() -> None:
    root = Path(__file__).resolve().parents[1]

    resources = resolve_skill2_resources(root)

    assert resources["students_path"].name == "student_profiles_standard.json"
    assert resources["mentors_path"].name == "mentor_profiles_standard.json"
    assert resources["resource_mode"] in {"outputs_bundle", "regenerate_bundle", "processed_bundle"}
