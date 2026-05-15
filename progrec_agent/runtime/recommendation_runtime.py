from __future__ import annotations

from progrec_agent.config import resolve_resource_config
from progrec_agent.orchestrator import ProgRecOrchestrator
from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


def run_recommendation_for_student_id(*, repo_root, temp_dir, student_id: str, mode: str, top_k: int):
    bundle = resolve_resource_config(mode, repo_root, validate_graph=True)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.recommend_for_student_id(student_id, top_k=top_k, bundle=bundle)


def run_recommendation_for_profile(*, repo_root, temp_dir, profile: dict[str, object], top_k: int):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.recommend_for_profile(standardized, top_k=top_k)


def run_mentor_recommendation_for_profile(*, repo_root, temp_dir, profile: dict[str, object], top_k: int):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.rank_mentors_for_profile(standardized, top_k=top_k)


def _extract_skill4_items(skill4_result: dict[str, object], key: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for bundle in list(skill4_result.get("mentor_project_teammate_recommendations") or []):
        if not isinstance(bundle, dict):
            continue
        for item in list(bundle.get(key) or []):
            if isinstance(item, dict):
                items.append(item)
    return items


def run_project_recommendations_for_profile(
    *,
    repo_root,
    temp_dir,
    profile: dict[str, object],
    top_k: int,
    mentor_result: dict[str, object] | None = None,
):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    payload = orchestrator.expand_projects_and_teammates_for_profile(
        standardized,
        top_k=top_k,
        skill3_result=mentor_result,
    )
    skill4_result = dict(payload.get("skill4_result") or {})
    payload["projects"] = _extract_skill4_items(skill4_result, "project_recommendations")
    return payload


def run_teammate_recommendations_for_profile(
    *,
    repo_root,
    temp_dir,
    profile: dict[str, object],
    top_k: int,
    mentor_result: dict[str, object] | None = None,
):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    payload = orchestrator.expand_projects_and_teammates_for_profile(
        standardized,
        top_k=top_k,
        skill3_result=mentor_result,
    )
    skill4_result = dict(payload.get("skill4_result") or {})
    payload["teammates"] = _extract_skill4_items(skill4_result, "teammate_recommendations")
    return payload
