from __future__ import annotations

from skill.explanation import build_reason_paths


def test_complemented_by_only_when_teammate_has_skill() -> None:
    teammates = [
        {
            "student_id": "bob",
            "complementary_skills": ["python"],
        }
    ]
    paths = build_reason_paths(
        "alice",
        "m_1",
        "p_1",
        ["ml"],
        ["python", "rust"],
        teammates,
    )
    assert any(
        p == ["project", "requires_skill", "python", "complemented_by", "bob"] for p in paths
    )
    assert any(
        p == ["project", "requires_skill", "rust", "gap_for", "target_student"] for p in paths
    )


def test_no_complemented_by_when_complementary_empty() -> None:
    teammates = [{"student_id": "bob", "complementary_skills": []}]
    paths = build_reason_paths("a", "m", "p", [], ["go"], teammates)
    assert all("complemented_by" not in p for p in paths if "requires_skill" in p)
