from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def run_pipeline_job_via_cli(*, repo_root: Path, job_payload: dict[str, object]) -> dict[str, object]:
    if job_payload["job_type"] != "recommend_existing_student":
        raise RuntimeError("CLI fallback currently supports dataset-mode student_id jobs only")
    with tempfile.TemporaryDirectory(prefix="progrec_cli_job_") as tmp_dir:
        output_path = Path(tmp_dir) / "final.json"
        command = [
            "python3",
            "progrec_agent/run_agent.py",
            "--mode",
            str(job_payload.get("mode", "graph")),
            "--student-id",
            str(job_payload["student_id"]),
            "--output",
            str(output_path),
        ]
        subprocess.run(command, cwd=repo_root, check=True, capture_output=True, text=True)
        return json.loads(output_path.read_text(encoding="utf-8"))
