from __future__ import annotations

from math import sqrt

from skill3_mentor_discovery.explanations import build_reasons
from skill3_mentor_discovery.graph_features import graph_features_for_mentors
from skill3_mentor_discovery.models import MentorCandidate
from skill3_mentor_discovery.profile_utils import (
    build_mentor_counter,
    build_student_counter,
    mentor_topic_terms,
    student_interest_skill_terms,
)


def cosine_counter(a, b) -> float:
    numer = sum(a[token] * b[token] for token in set(a) & set(b))
    denom = sqrt(sum(v * v for v in a.values())) * sqrt(sum(v * v for v in b.values()))
    return 0.0 if denom == 0 else numer / denom


def normalize_scores(values: list[float]) -> list[float]:
    if not values:
        return []
    min_value = min(values)
    max_value = max(values)
    if max_value == min_value:
        return [1.0 if max_value > 0.0 else 0.0 for _ in values]
    span = max_value - min_value
    return [(value - min_value) / span for value in values]


def rank_mentors_for_student(
    student: dict[str, object],
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None = None,
    top_k: int = 10,
    candidate_pool_size: int = 30,
):
    student_counter = build_student_counter(student)
    student_terms = student_interest_skill_terms(student)

    topic_ranked: list[dict[str, object]] = []
    for mentor in mentors:
        mentor_counter = build_mentor_counter(mentor)
        mentor_terms = mentor_topic_terms(mentor)
        semantic = cosine_counter(student_counter, mentor_counter)
        overlap = len(student_terms & mentor_terms) / max(len(student_terms), 1)
        topic_score = (0.8 * semantic) + (0.2 * overlap)
        topic_ranked.append(
            {
                "mentor": mentor,
                "topic_score": topic_score,
                "overlap_terms": student_terms & mentor_terms,
            }
        )

    topic_ranked.sort(key=lambda item: float(item["topic_score"]), reverse=True)
    candidate_count = min(len(topic_ranked), max(top_k, candidate_pool_size))
    candidate_pool = topic_ranked[:candidate_count]
    mentor_graph_features = graph_features_for_mentors(
        [item["mentor"] for item in candidate_pool],
        graph,
        student_id=str(student.get("student_id", "")) or None,
    )

    raw_graph_scores: list[float] = []
    activity_scores: list[float] = []
    for item in candidate_pool:
        mentor = item["mentor"]
        mentor_id = str(mentor.get("mentor_id", ""))
        graph_feature = mentor_graph_features.get(mentor_id, {})
        meta_path_breakdown = dict(graph_feature.get("meta_path_breakdown") or {})
        meta_path_total = sum(float(score) for score in meta_path_breakdown.values())
        mentor_authority = float(graph_feature.get("mentor_authority", 0.0))
        personalized_proximity = float(graph_feature.get("personalized_proximity", 0.0))
        raw_graph_score = (
            (0.5 * personalized_proximity)
            + (0.3 * meta_path_total)
            + (0.2 * mentor_authority)
        )
        item["raw_graph_score"] = raw_graph_score
        item["activity_score"] = float(graph_feature.get("activity_score", 0.0))
        raw_graph_scores.append(raw_graph_score)
        activity_scores.append(float(item["activity_score"]))

    normalized_topic_scores = normalize_scores(
        [float(item["topic_score"]) for item in candidate_pool]
    )
    normalized_graph_scores = normalize_scores(raw_graph_scores)
    normalized_activity_scores = normalize_scores(activity_scores)

    ranked: list[MentorCandidate] = []
    for item, norm_topic, norm_graph, norm_activity in zip(
        candidate_pool,
        normalized_topic_scores,
        normalized_graph_scores,
        normalized_activity_scores,
    ):
        mentor = item["mentor"]
        mentor_id = str(mentor.get("mentor_id", ""))
        graph_feature = mentor_graph_features.get(mentor_id, {})
        activity_score = float(item["activity_score"])
        graph_confidence = float(graph_feature.get("graph_confidence", 0.0))
        effective_graph_score = graph_confidence * float(item["raw_graph_score"])
        effective_graph_component = graph_confidence * norm_graph
        ranked.append(
            MentorCandidate(
                mentor_id=mentor_id,
                mentor_name=str(mentor.get("name", "")),
                topic_score=float(item["topic_score"]),
                graph_score=effective_graph_score,
                activity_score=activity_score,
                centrality_score=float(graph_feature.get("centrality_score", 0.0)),
                network_proximity=float(graph_feature.get("network_proximity", 0.0)),
                personalized_proximity=float(graph_feature.get("personalized_proximity", 0.0)),
                graph_confidence=graph_confidence,
                mentor_authority=float(graph_feature.get("mentor_authority", 0.0)),
                meta_path_breakdown=dict(graph_feature.get("meta_path_breakdown") or {}),
                top_evidence_paths=list(graph_feature.get("top_evidence_paths") or []),
                community_id=str(graph_feature.get("community_id", "community_unknown")),
                final_score=(0.60 * norm_topic) + (0.25 * effective_graph_component) + (0.15 * norm_activity),
                reasons=build_reasons(
                    mentor,
                    overlap_terms=set(item["overlap_terms"]),
                    community_id=str(graph_feature.get("community_id", "community_unknown")),
                    activity_score=activity_score,
                    meta_path_breakdown=dict(graph_feature.get("meta_path_breakdown") or {}),
                    graph_confidence=graph_confidence,
                    top_evidence_paths=list(graph_feature.get("top_evidence_paths") or []),
                ),
            )
        )
    ranked.sort(key=lambda item: item.final_score, reverse=True)
    return ranked[:top_k]
