from __future__ import annotations


def recommend_projects(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context=None):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    mentor_payload = mentor_result_ref.get("payload") if isinstance(mentor_result_ref, dict) else None
    return executor_context.recommendation_runtime.run_project_recommendations_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        mentor_result=mentor_payload,
        top_k=int(top_k or 5),
    )


def recommend_teammates(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context=None):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    mentor_payload = mentor_result_ref.get("payload") if isinstance(mentor_result_ref, dict) else None
    return executor_context.recommendation_runtime.run_teammate_recommendations_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        mentor_result=mentor_payload,
        top_k=int(top_k or 5),
    )
