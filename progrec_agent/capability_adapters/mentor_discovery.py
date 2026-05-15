from __future__ import annotations


def recommend_mentors(*, student_profile_ref, top_k, executor_context):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    return executor_context.recommendation_runtime.run_mentor_recommendation_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        top_k=int(top_k or 5),
    )
