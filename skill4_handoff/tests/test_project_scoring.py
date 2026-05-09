from __future__ import annotations

from skill.project_scoring import (
    compute_difficulty_match_score,
    compute_project_fit_score,
    compute_skill_gap,
    compute_skill_match_score,
    compute_topic_match_score,
    jaccard_similarity,
)


def test_jaccard() -> None:
    assert jaccard_similarity(["a", "b"], ["b", "c"]) == 1 / 3


def test_skill_gap() -> None:
    g = compute_skill_gap(["python"], ["python", "rust", "go"])
    assert set(g) == {"go", "rust"}


def test_project_fit_in_unit_interval() -> None:
    t = compute_topic_match_score(["ml"], ["ml", "nlp"])
    s = compute_skill_match_score(["python"], ["python", "c++"])
    d = compute_difficulty_match_score("Senior", "medium")
    f = compute_project_fit_score(t, s, d, 1.0)
    assert 0.0 <= f <= 1.0


def test_difficulty_rules() -> None:
    assert compute_difficulty_match_score("Senior", "easy") == 1.0
    assert compute_difficulty_match_score("Sophomore", "medium") == 1.0
    assert compute_difficulty_match_score("Freshman", "medium") == 0.7
    assert compute_difficulty_match_score("Freshman", "hard") == 0.4
