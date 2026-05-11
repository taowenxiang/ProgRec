import subprocess
import sys
from pathlib import Path


def test_repl_help_command_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "progrec_agent.repl"]
    completed = subprocess.run(
        cmd,
        input="help\nexit\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
    )

    assert completed.returncode == 0
    assert "ProgRec Agent CLI" in completed.stdout
    assert "recommend" in completed.stdout


def test_dataset_mode_recommend_command_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "progrec_agent.repl"]
    completed = subprocess.run(
        cmd,
        input="I want an NLP mentor\nexit\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
        timeout=20,
    )

    assert completed.returncode == 0
    assert "Goal: I want an NLP mentor" in completed.stdout
    assert "Decision Trace:" in completed.stdout
