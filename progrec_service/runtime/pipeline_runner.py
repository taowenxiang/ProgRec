from __future__ import annotations

from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator


def run_pipeline_job(*, repo_root: Path, temp_dir: Path, job_payload: dict[str, object]) -> dict[str, object]:
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    if job_payload["job_type"] == "recommend_existing_student":
        return orchestrator.recommend_for_student_id(
            str(job_payload["student_id"]),
            top_k=int(job_payload.get("top_k", 10)),
        )
    return orchestrator.recommend_for_profile(
        dict(job_payload["student_profile"]),
        top_k=int(job_payload.get("top_k", 10)),
    )
