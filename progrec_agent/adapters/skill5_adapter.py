from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from progrec_agent.config import skill1_profiles_path


def run_skill5(
    *,
    repo_root: Path,
    skill3_path: Path,
    skill4_path: Path,
    output_path: Path,
    student_id: str,
    top_k: int,
) -> dict[str, object]:
    script = repo_root / "skill5_student_recommendation_ranker/scripts/joint_ranker.py"
    cmd = [
        sys.executable,
        str(script),
        "--skill3",
        str(skill3_path),
        "--skill4",
        str(skill4_path),
        "--output",
        str(output_path),
        "--student-id",
        student_id,
        "--top-k",
        str(top_k),
        "--students",
        str(skill1_profiles_path(repo_root)),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(output_path.read_text(encoding="utf-8"))
