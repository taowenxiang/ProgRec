from __future__ import annotations

from progrec_agent.runtime import validation_runtime

def validate_graph_resources(*, mode, executor_context):
    return validation_runtime.validate_resources(repo_root=executor_context.repo_root, mode=str(mode))
