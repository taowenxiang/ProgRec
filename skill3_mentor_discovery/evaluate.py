from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from skill3_mentor_discovery.graph_features import prepare_graph_for_ranking
from skill3_mentor_discovery.graph_index import get_edge_trust_tier
from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.profile_utils import mentor_topic_terms, student_interest_skill_terms
from skill3_mentor_discovery.retrieval import normalize_scores, rank_mentors_for_student

ABLATION_VARIANTS = (
    "topic_only",
    "topic_plus_authority",
    "topic_plus_personalized_graph",
    "topic_plus_personalized_graph_plus_trust",
)


def _validate_variant(variant: str) -> str:
    if variant not in ABLATION_VARIANTS:
        raise ValueError(f"Unsupported evaluation variant: {variant}")
    return variant


def _graph_for_variant(
    graph: dict[str, object] | None,
    variant: str,
    *,
    student_id: str | None = None,
) -> dict[str, object] | None:
    if variant == "topic_only":
        return None
    prepared_graph, _, _ = prepare_graph_for_ranking(graph, student_id=student_id)
    return prepared_graph


def _rescore_candidates_for_variant(candidates, variant: str):
    norm_topic = normalize_scores([candidate.topic_score for candidate in candidates])
    norm_authority = normalize_scores([candidate.mentor_authority for candidate in candidates])
    norm_personalized = normalize_scores([candidate.personalized_proximity for candidate in candidates])
    norm_trust_graph = normalize_scores([candidate.graph_score for candidate in candidates])

    for candidate, topic_score, authority_score, personalized_score, trust_graph_score in zip(
        candidates,
        norm_topic,
        norm_authority,
        norm_personalized,
        norm_trust_graph,
    ):
        if variant == "topic_only":
            candidate.final_score = topic_score
        elif variant == "topic_plus_authority":
            candidate.final_score = (0.8 * topic_score) + (0.2 * authority_score)
        elif variant == "topic_plus_personalized_graph":
            candidate.final_score = (
                (0.7 * topic_score)
                + (0.15 * authority_score)
                + (0.15 * personalized_score)
            )
        else:
            candidate.final_score = (
                (0.6 * topic_score)
                + (0.15 * authority_score)
                + (0.1 * personalized_score)
                + (0.15 * trust_graph_score)
            )
    candidates.sort(key=lambda candidate: candidate.final_score, reverse=True)
    return candidates


def _rank_variant_for_student(
    student: dict[str, object],
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None,
    *,
    top_k: int,
    variant: str,
):
    graph = _graph_for_variant(
        graph,
        variant,
        student_id=str(student.get("student_id", "")) or None,
    )
    if variant == "topic_plus_personalized_graph_plus_trust":
        return rank_mentors_for_student(
            student,
            mentors,
            graph=graph,
            top_k=top_k,
        )
    candidates = rank_mentors_for_student(
        student,
        mentors,
        graph=graph,
        top_k=len(mentors),
        candidate_pool_size=len(mentors),
    )
    rescored = _rescore_candidates_for_variant(candidates, variant)
    return rescored[:top_k]


def _sample_students(resources, sample_size: int) -> list[dict[str, object]]:
    return resources.students[:sample_size]


def _load_evaluation_resources(
    repo_root: Path,
    *,
    require_graph: bool,
):
    try:
        resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=False)

    if require_graph and resources.graph is None:
        prepared_graph, graph_status, graph_notice = prepare_graph_for_ranking(resources.graph)
        detail = graph_notice or graph_status or "graph unavailable"
        raise RuntimeError(
            "Graph-aware Skill 3 evaluation requires a usable prepared graph, "
            f"but evaluation could not load one: {detail}"
        )
    return resources


def _copy_graph_with_edges(
    graph: dict[str, object] | None,
    edges: list[dict[str, object]],
) -> dict[str, object] | None:
    if not graph:
        return None
    return {
        "nodes": graph.get("nodes") or {},
        "edges": edges,
    }


def _drop_low_trust_edges(graph: dict[str, object] | None) -> dict[str, object] | None:
    if not graph:
        return None
    kept_edges = [
        edge
        for edge in graph.get("edges") or []
        if get_edge_trust_tier(str(edge.get("type", ""))) != "low"
    ]
    return _copy_graph_with_edges(graph, kept_edges)


def _drop_random_edge_subset(
    graph: dict[str, object] | None,
    *,
    seed: int = 0,
    drop_fraction: float = 0.2,
) -> dict[str, object] | None:
    if not graph:
        return None
    rng = random.Random(seed)
    kept_edges = [
        edge
        for edge in graph.get("edges") or []
        if rng.random() >= drop_fraction
    ]
    return _copy_graph_with_edges(graph, kept_edges)


def _average_top_k_overlap(
    students: list[dict[str, object]],
    mentors: list[dict[str, object]],
    baseline_graph: dict[str, object] | None,
    comparison_graph: dict[str, object] | None,
    *,
    top_k: int,
) -> float:
    if not students:
        return 0.0

    overlaps: list[float] = []
    for student in students:
        baseline_ids = {
            candidate.mentor_id
            for candidate in _rank_variant_for_student(
                student,
                mentors,
                baseline_graph,
                top_k=top_k,
                variant="topic_plus_personalized_graph_plus_trust",
            )
        }
        comparison_ids = {
            candidate.mentor_id
            for candidate in _rank_variant_for_student(
                student,
                mentors,
                comparison_graph,
                top_k=top_k,
                variant="topic_plus_personalized_graph_plus_trust",
            )
        }
        denom = max(min(top_k, len(baseline_ids)), 1)
        overlaps.append(len(baseline_ids & comparison_ids) / denom)
    return sum(overlaps) / len(overlaps)


def evaluate_recall_at_k(
    repo_root: Path,
    top_k: int = 5,
    sample_size: int = 20,
    *,
    variant: str = "topic_plus_personalized_graph_plus_trust",
) -> dict[str, float | int]:
    variant = _validate_variant(variant)
    resources = _load_evaluation_resources(
        repo_root,
        require_graph=variant != "topic_only",
    )
    prepared_graph = resources.graph
    students = _sample_students(resources, sample_size)
    if not students:
        return {"recall_at_k": 0.0, "evaluated_students": 0, "students_with_hits": 0}

    total_hits = 0
    students_with_hits = 0
    for student in students:
        student_terms = student_interest_skill_terms(student)
        ranked = _rank_variant_for_student(
            student,
            resources.mentors,
            prepared_graph,
            top_k=top_k,
            variant=variant,
        )
        has_hit = False
        for candidate in ranked:
            mentor = next(
                mentor
                for mentor in resources.mentors
                if mentor.get("mentor_id") == candidate.mentor_id
            )
            if student_terms & mentor_topic_terms(mentor):
                has_hit = True
                break
        if has_hit:
            students_with_hits += 1
            total_hits += 1
    recall = total_hits / len(students)
    return {
        "recall_at_k": recall,
        "evaluated_students": len(students),
        "students_with_hits": students_with_hits,
    }


def evaluate_ablation_summary(
    repo_root: Path,
    top_k: int = 5,
    sample_size: int = 20,
) -> dict[str, dict[str, float | int]]:
    return {
        variant: evaluate_recall_at_k(
            repo_root,
            top_k=top_k,
            sample_size=sample_size,
            variant=variant,
        )
        for variant in ABLATION_VARIANTS
    }


def evaluate_perturbation_summary(
    repo_root: Path,
    top_k: int = 5,
    sample_size: int = 20,
) -> dict[str, float]:
    resources = _load_evaluation_resources(repo_root, require_graph=True)
    prepared_graph = resources.graph
    students = _sample_students(resources, sample_size)
    low_trust_graph = _drop_low_trust_edges(prepared_graph)
    random_drop_graph = _drop_random_edge_subset(prepared_graph, seed=0)
    return {
        "baseline_top_k_overlap": _average_top_k_overlap(
            students,
            resources.mentors,
            prepared_graph,
            prepared_graph,
            top_k=top_k,
        ),
        "drop_low_trust_edges_top_k_overlap": _average_top_k_overlap(
            students,
            resources.mentors,
            prepared_graph,
            low_trust_graph,
            top_k=top_k,
        ),
        "random_edge_drop_top_k_overlap": _average_top_k_overlap(
            students,
            resources.mentors,
            prepared_graph,
            random_drop_graph,
            top_k=top_k,
        ),
    }


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    print(json.dumps(evaluate_recall_at_k(repo_root), indent=2))
