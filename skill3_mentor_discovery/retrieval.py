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


def rank_mentors_for_student(
    student: dict[str, object],
    mentors: list[dict[str, object]],
    graph: dict[str, object] | None = None,
    top_k: int = 10,
):
    student_counter = build_student_counter(student)
    student_terms = student_interest_skill_terms(student)
    mentor_graph_features = graph_features_for_mentors(mentors, graph)
    ranked: list[MentorCandidate] = []
    for mentor in mentors:
        mentor_counter = build_mentor_counter(mentor)
        mentor_terms = mentor_topic_terms(mentor)
        semantic = cosine_counter(student_counter, mentor_counter)
        overlap = len(student_terms & mentor_terms) / max(len(student_terms), 1)
        topic_score = (0.8 * semantic) + (0.2 * overlap)
        mentor_id = str(mentor.get("mentor_id", ""))
        graph_feature = mentor_graph_features.get(mentor_id, {})
        centrality_score = float(graph_feature.get("centrality_score", 0.0))
        network_proximity = float(graph_feature.get("network_proximity", 0.0))
        activity_score = float(graph_feature.get("activity_score", 0.0))
        graph_score = (0.7 * centrality_score) + (0.3 * network_proximity)
        final_score = (0.60 * topic_score) + (0.25 * graph_score) + (0.15 * activity_score)
        overlap_terms = student_terms & mentor_terms
        ranked.append(
            MentorCandidate(
                mentor_id=mentor_id,
                mentor_name=str(mentor.get("name", "")),
                topic_score=topic_score,
                graph_score=graph_score,
                activity_score=activity_score,
                centrality_score=centrality_score,
                network_proximity=network_proximity,
                community_id=str(graph_feature.get("community_id", "community_unknown")),
                final_score=final_score,
                reasons=build_reasons(
                    mentor,
                    overlap_terms=overlap_terms,
                    community_id=str(graph_feature.get("community_id", "community_unknown")),
                    activity_score=activity_score,
                ),
            )
        )
    ranked.sort(key=lambda item: item.final_score, reverse=True)
    return ranked[:top_k]
