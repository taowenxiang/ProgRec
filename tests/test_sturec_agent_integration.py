import subprocess
import sys
from pathlib import Path


def test_repl_help_command_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "sturec_agent.repl"]
    completed = subprocess.run(
        cmd,
        input="help\nexit\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
    )

    assert completed.returncode == 0
    assert "StuRec Agent CLI" in completed.stdout
    assert "recommend" in completed.stdout


def test_dataset_mode_recommend_command_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "sturec_agent.repl"]
    completed = subprocess.run(
        cmd,
        input="recommend\n1\njamie-taylor-00008\nexit\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
    )

    assert completed.returncode == 0
    assert "Top Mentors" in completed.stdout
    assert "show mentor" in completed.stdout
