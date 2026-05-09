"""Lightweight typed shapes for Skill 4 (plain dicts in/out; no strict runtime validation)."""

from __future__ import annotations

from typing import Any, TypedDict


class DataSources(TypedDict, total=False):
    student_profiles: str | None
    academic_graph: str | None
    mentor_candidates: str | None
    project_source: str


class ProjectRec(TypedDict, total=False):
    project_id: str
    title: str
    fit_score: float
    topic_match_score: float
    skill_match_score: float
    difficulty_match_score: float
    matched_interests: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    reason: str


class TeammateRec(TypedDict, total=False):
    student_id: str
    teammate_score: float
    shared_interest_score: float
    complementarity_score: float
    availability_score: float
    graph_relation_score: float
    shared_interests: list[str]
    complementary_skills: list[str]
    availability: str
    reason: str


class MentorBundle(TypedDict, total=False):
    mentor_id: str
    mentor_base_score: float
    topic_score: float
    graph_score: float
    community_id: str | None
    activity_score: float
    centrality_score: float
    network_proximity: float
    mentor_name: str
    skill3_rank: int
    mentor_skill3_reasons: list[str]
    matched_topics: list[str]
    mentor_profile: dict[str, Any]
    project_recommendations: list[ProjectRec]
    teammate_recommendations: list[TeammateRec]
    reason_paths: list[list[str]]


class Skill4Output(TypedDict, total=False):
    target_student_id: str
    target_student_profile: dict[str, Any]
    data_sources: DataSources
    mentor_project_teammate_recommendations: list[MentorBundle]
    reason_graphs: list[dict[str, Any]]


NormalizedProject = dict[str, Any]
