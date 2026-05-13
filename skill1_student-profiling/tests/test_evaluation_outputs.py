"""Tests for report-facing evaluation output helpers."""

from importlib.resources import files

from student_profiling.evaluation_helpers import build_ablation_payload


def test_build_ablation_payload_has_expected_shape():
    payload = build_ablation_payload(
        {
            "Baseline": {"avg_skills": 1.0, "unique_skill_terms": 70},
            "+ Taxonomy": {"avg_skills": 4.0, "unique_skill_terms": 183},
            "+ UQ": {"avg_skills": 5.2, "unique_skill_terms": 322},
            "Full Pipeline": {"avg_skills": 5.5, "unique_skill_terms": 446},
        },
        n_records=500,
    )

    assert payload["config_order"] == ["Baseline", "+ Taxonomy", "+ UQ", "Full Pipeline"]
    assert payload["n_records"] == 500
    assert "avg_skills" in payload["metrics"]["Full Pipeline"]
    assert "unique_skill_terms" in payload["metrics"]["Full Pipeline"]


def test_taxonomy_package_data_is_available():
    data_dir = files("student_profiling").joinpath("taxonomy", "data")
    assert data_dir.joinpath("major_skills.json").is_file()
    assert data_dir.joinpath("hobby_interests.json").is_file()
    assert data_dir.joinpath("uq_mapping.json").is_file()
