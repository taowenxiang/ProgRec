from __future__ import annotations

from progrec_agent.config import resolve_resource_config


def validate_resources(*, repo_root, mode: str):
    bundle = resolve_resource_config(mode, repo_root, validate_graph=(mode == "graph"))
    return {
        "mode": mode,
        "students_path": str(bundle.skill2_students),
        "mentors_path": str(bundle.skill2_mentors),
        "graph_path": str(bundle.skill2_graph) if bundle.skill2_graph else "",
    }
