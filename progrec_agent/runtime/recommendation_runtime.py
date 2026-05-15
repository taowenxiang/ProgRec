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
