# ProgRec CLI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI-first ProgRec agent that orchestrates Skills 1-5 for dataset-backed and manual student profiles, supports a small REPL command set, and returns explainable mentor/project/teammate recommendations.

**Architecture:** Add a new `progrec_agent/` package that owns REPL flow, session state, rendering, and orchestration while preserving the five existing skills as separate modules. Prefer direct Python integration for Skill 3 and Skill 4, lightweight adapters for Skill 1 and Skill 2, and a subprocess wrapper for Skill 5's final ranking script.

**Tech Stack:** Python 3, `pytest`, `dataclasses` / `TypedDict`, existing Skill 3 and Skill 4 Python modules, existing Skill 5 CLI script, JSON temp files under the repo workspace.

---

### Task 1: Scaffold agent package, shared models, and session state

**Files:**
- Create: `progrec_agent/__init__.py`
- Create: `progrec_agent/models.py`
- Create: `progrec_agent/session.py`
- Test: `tests/test_progrec_agent_session.py`

- [ ] **Step 1: Write the failing session-state tests**

```python
from pathlib import Path

from progrec_agent.session import AgentSession


def test_session_starts_empty(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)

    assert session.mode is None
    assert session.student_profile is None
    assert session.skill5_result is None
    assert session.has_results is False


def test_session_stores_pipeline_results(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)
    payload = {
        "student_id": "s_002",
        "recommendations": {"mentors": [{"mentor_id": "m_001", "rank": 1}]},
    }

    session.set_student_profile({"student_id": "s_002", "major": "CS"})
    session.set_mode("dataset_mode")
    session.set_results(
        skill3_result={"mentor_candidates": [{"mentor_id": "m_001"}]},
        skill4_result={"mentor_project_teammate_recommendations": []},
        skill5_result=payload,
        temporary_paths=[],
    )

    assert session.mode == "dataset_mode"
    assert session.student_profile["student_id"] == "s_002"
    assert session.skill5_result == payload
    assert session.has_results is True


def test_restart_clears_results_and_temp_files(tmp_path: Path) -> None:
    session = AgentSession(temp_dir=tmp_path)
    temp_file = tmp_path / "skill3.json"
    temp_file.write_text("{}", encoding="utf-8")
    session.set_student_profile({"student_id": "s_002"})
    session.set_mode("dataset_mode")
    session.set_results(
        skill3_result={},
        skill4_result={},
        skill5_result={"student_id": "s_002"},
        temporary_paths=[temp_file],
    )

    session.reset()

    assert session.mode is None
    assert session.student_profile is None
    assert session.skill3_result is None
    assert session.skill4_result is None
    assert session.skill5_result is None
    assert not temp_file.exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_session.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent'`

- [ ] **Step 3: Write the minimal package, models, and session implementation**

```python
# progrec_agent/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Mode = Literal["dataset_mode", "custom_profile_mode"]
JsonDict = dict[str, Any]


@dataclass
class PipelineArtifacts:
    skill3_result: JsonDict | None = None
    skill4_result: JsonDict | None = None
    skill5_result: JsonDict | None = None
    temporary_paths: list[Path] = field(default_factory=list)
```

```python
# progrec_agent/session.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from progrec_agent.models import JsonDict, Mode, PipelineArtifacts


@dataclass
class AgentSession:
    temp_dir: Path
    mode: Mode | None = None
    student_profile: JsonDict | None = None
    resource_context: JsonDict | None = None
    skill3_result: JsonDict | None = None
    skill4_result: JsonDict | None = None
    skill5_result: JsonDict | None = None
    temporary_paths: list[Path] = field(default_factory=list)

    @property
    def has_results(self) -> bool:
        return self.skill5_result is not None

    def set_mode(self, mode: Mode) -> None:
        self.mode = mode

    def set_student_profile(self, profile: JsonDict) -> None:
        self.student_profile = dict(profile)

    def set_resource_context(self, resource_context: JsonDict) -> None:
        self.resource_context = dict(resource_context)

    def set_results(
        self,
        *,
        skill3_result: JsonDict,
        skill4_result: JsonDict,
        skill5_result: JsonDict,
        temporary_paths: list[Path],
    ) -> None:
        self.skill3_result = skill3_result
        self.skill4_result = skill4_result
        self.skill5_result = skill5_result
        self.temporary_paths = list(temporary_paths)

    def reset(self) -> None:
        for path in self.temporary_paths:
            if path.exists():
                path.unlink()
        self.mode = None
        self.student_profile = None
        self.resource_context = None
        self.skill3_result = None
        self.skill4_result = None
        self.skill5_result = None
        self.temporary_paths = []
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_progrec_agent_session.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/__init__.py progrec_agent/models.py progrec_agent/session.py tests/test_progrec_agent_session.py
git commit -m "feat: add ProgRec agent session scaffolding"
```

### Task 2: Implement Skill 1 and Skill 2 adapters

**Files:**
- Create: `progrec_agent/adapters/__init__.py`
- Create: `progrec_agent/adapters/skill1_adapter.py`
- Create: `progrec_agent/adapters/skill2_adapter.py`
- Test: `tests/test_progrec_agent_adapters.py`

- [ ] **Step 1: Write failing adapter tests**

```python
from pathlib import Path

from progrec_agent.adapters.skill1_adapter import normalize_manual_profile
from progrec_agent.adapters.skill2_adapter import resolve_skill2_resources


def test_normalize_manual_profile_splits_lists_and_adds_temp_id() -> None:
    profile = normalize_manual_profile(
        {
            "grade": "Senior",
            "major": "Computer Science",
            "skills": "python, data analysis, python",
            "interests": "nlp, social computing",
            "experience_summary": "Built a chatbot for class.",
            "availability": "High",
            "resume_text": "",
        }
    )

    assert profile["student_id"].startswith("cli-custom-")
    assert profile["skills"] == ["python", "data analysis"]
    assert profile["interests"] == ["nlp", "social computing"]
    assert profile["availability"] == "high"


def test_resolve_skill2_resources_prefers_outputs_bundle() -> None:
    root = Path(__file__).resolve().parents[1]

    resources = resolve_skill2_resources(root)

    assert resources["students_path"].name == "student_profiles_standard.json"
    assert resources["mentors_path"].name == "mentor_profiles_standard.json"
    assert resources["resource_mode"] in {"outputs_bundle", "regenerate_bundle", "processed_bundle"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_adapters.py -q`

Expected: FAIL with `ModuleNotFoundError` for the adapter modules

- [ ] **Step 3: Write the minimal adapters**

```python
# progrec_agent/adapters/skill1_adapter.py
from __future__ import annotations

from datetime import datetime


def _split_tags(value: str) -> list[str]:
    seen: set[str] = set()
    tags: list[str] = []
    for part in value.split(","):
        tag = part.strip().lower()
        if tag and tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def normalize_manual_profile(raw: dict[str, str]) -> dict[str, object]:
    return {
        "student_id": f"cli-custom-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "grade": raw.get("grade", "").strip() or "unknown",
        "major": raw.get("major", "").strip() or "unknown",
        "skills": _split_tags(raw.get("skills", "")),
        "interests": _split_tags(raw.get("interests", "")),
        "experience_summary": raw.get("experience_summary", "").strip(),
        "availability": raw.get("availability", "moderate").strip().lower() or "moderate",
        "resume_text": raw.get("resume_text", "").strip(),
    }
```

```python
# progrec_agent/adapters/skill2_adapter.py
from __future__ import annotations

from pathlib import Path


def resolve_skill2_resources(repo_root: Path) -> dict[str, object]:
    candidates = [
        (
            "outputs_bundle",
            repo_root / "skill2_handoff/outputs/student_profiles_standard.json",
            repo_root / "skill2_handoff/outputs/mentor_profiles_standard.json",
            repo_root / "skill2_handoff/outputs/academic_graph.json",
        ),
        (
            "regenerate_bundle",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/student_profiles_standard.json",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/mentor_profiles_standard.json",
            repo_root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json",
        ),
        (
            "processed_bundle",
            repo_root / "data/processed/student_profiles_standard.json",
            repo_root / "data/processed/mentor_profiles_standard.json",
            repo_root / "data/processed/academic_graph.json",
        ),
    ]
    for mode, students_path, mentors_path, graph_path in candidates:
        if students_path.is_file() and mentors_path.is_file():
            return {
                "resource_mode": mode,
                "students_path": students_path,
                "mentors_path": mentors_path,
                "graph_path": graph_path if graph_path.is_file() else None,
            }
    raise FileNotFoundError("Could not resolve Skill 2 resource bundle")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_progrec_agent_adapters.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/adapters/__init__.py progrec_agent/adapters/skill1_adapter.py progrec_agent/adapters/skill2_adapter.py tests/test_progrec_agent_adapters.py
git commit -m "feat: add ProgRec agent skill adapters"
```

### Task 3: Implement Skill 3, Skill 4, and Skill 5 wrappers plus dataset-mode orchestration

**Files:**
- Create: `progrec_agent/adapters/skill3_adapter.py`
- Create: `progrec_agent/adapters/skill4_adapter.py`
- Create: `progrec_agent/adapters/skill5_adapter.py`
- Create: `progrec_agent/orchestrator.py`
- Test: `tests/test_progrec_agent_orchestrator.py`

- [ ] **Step 1: Write the failing dataset-mode orchestration tests**

```python
from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator


def test_dataset_mode_returns_ranked_results(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=tmp_path)

    result = orchestrator.recommend_for_student_id("s_002", top_k=3)

    assert result["mode"] == "dataset_mode"
    assert result["student_profile"]["student_id"] == "s_002"
    assert len(result["skill3_result"]["mentor_candidates"]) == 3
    assert result["skill4_result"]["mentor_project_teammate_recommendations"]
    assert result["skill5_result"]["recommendations"]["mentors"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_orchestrator.py -q`

Expected: FAIL because `ProgRecOrchestrator` does not exist yet

- [ ] **Step 3: Write the minimal wrappers and dataset-mode orchestrator**

```python
# progrec_agent/adapters/skill3_adapter.py
from __future__ import annotations

from pathlib import Path

from skill3_mentor_discovery.loaders import load_standardized_resources
from skill3_mentor_discovery.retrieval import rank_mentors_for_student


def run_skill3(repo_root: Path, student_profile: dict[str, object], top_k: int) -> dict[str, object]:
    resources = load_standardized_resources(repo_root, rebuild_graph_if_missing=False)
    mentor_candidates = rank_mentors_for_student(
        student_profile,
        resources.mentors,
        graph=resources.graph,
        top_k=top_k,
    )
    return {
        "student_id": str(student_profile.get("student_id", "")),
        "mentor_candidates": [candidate.to_dict() for candidate in mentor_candidates],
    }
```

```python
# progrec_agent/adapters/skill4_adapter.py
from __future__ import annotations

from pathlib import Path

from skill4_handoff.skill.discovery import run_pipeline_from_cli_config


def run_skill4_dataset_mode(
    *,
    repo_root: Path,
    student_id: str,
    skill3_path: Path,
    output_path: Path,
) -> dict[str, object]:
    cfg = {
        "target_student_id": student_id,
        "skill1_profiles_path": str(repo_root / "skill1_handoff/student_profiles_normalized.jsonl"),
        "skill2_graph_path": "",
        "skill2_students_path": "",
        "skill2_mentors_path": "",
        "mentor_candidates_path": str(skill3_path),
        "skill3_output_path": str(skill3_path),
        "mock_projects_path": str(repo_root / "skill4_handoff/data/mock_projects.json"),
        "mock_mentor_candidates_path": str(repo_root / "skill4_handoff/data/mock_mentor_candidates.json"),
        "output_path": str(output_path),
        "top_n_projects": 3,
        "top_n_teammates": 3,
        "max_candidate_teammates": 120,
        "fallback_mentor_top_k": 10,
        "strict_target_student": False,
        "allow_target_fallback_with_skill3": False,
        "_embedding_context": None,
    }
    return run_pipeline_from_cli_config(cfg)
```

```python
# progrec_agent/adapters/skill5_adapter.py
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_skill5(
    *,
    repo_root: Path,
    skill3_path: Path,
    skill4_path: Path,
    output_path: Path,
    student_id: str,
    top_k: int,
) -> dict[str, object]:
    script = repo_root / "skill5_student-recommendation-ranker/scripts/joint_ranker.py"
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
        str(repo_root / "skill1_handoff/student_profiles_normalized.jsonl"),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(output_path.read_text(encoding="utf-8"))
```

```python
# progrec_agent/orchestrator.py
from __future__ import annotations

import json
from pathlib import Path

from progrec_agent.adapters.skill2_adapter import resolve_skill2_resources
from progrec_agent.adapters.skill3_adapter import run_skill3
from progrec_agent.adapters.skill4_adapter import run_skill4_dataset_mode
from progrec_agent.adapters.skill5_adapter import run_skill5


class ProgRecOrchestrator:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir

    def recommend_for_student_id(self, student_id: str, top_k: int = 5) -> dict[str, object]:
        resources = resolve_skill2_resources(self.repo_root)
        students_payload = json.loads(Path(resources["students_path"]).read_text(encoding="utf-8"))
        student_profile = next(
            student for student in students_payload["students"] if student["student_id"] == student_id
        )
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        skill5_path = self.temp_dir / "skill5.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_dataset_mode(
            repo_root=self.repo_root,
            student_id=student_id,
            skill3_path=skill3_path,
            output_path=skill4_path,
        )
        skill4_path.write_text(json.dumps(skill4_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill5_result = run_skill5(
            repo_root=self.repo_root,
            skill3_path=skill3_path,
            skill4_path=skill4_path,
            output_path=skill5_path,
            student_id=student_id,
            top_k=top_k,
        )
        return {
            "mode": "dataset_mode",
            "student_profile": student_profile,
            "resource_context": resources,
            "skill3_result": skill3_result,
            "skill4_result": skill4_result,
            "skill5_result": skill5_result,
            "temporary_paths": [skill3_path, skill4_path, skill5_path],
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_progrec_agent_orchestrator.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/adapters/skill3_adapter.py progrec_agent/adapters/skill4_adapter.py progrec_agent/adapters/skill5_adapter.py progrec_agent/orchestrator.py tests/test_progrec_agent_orchestrator.py
git commit -m "feat: add dataset-mode ProgRec orchestration"
```

### Task 4: Add custom-profile mode and shared recommendation entrypoint

**Files:**
- Modify: `progrec_agent/adapters/skill4_adapter.py`
- Modify: `progrec_agent/orchestrator.py`
- Test: `tests/test_progrec_agent_custom_mode.py`

- [ ] **Step 1: Write the failing custom-profile orchestration tests**

```python
from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator


def test_custom_profile_mode_returns_results_without_existing_student_id(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=tmp_path)

    result = orchestrator.recommend_for_profile(
        {
            "student_id": "cli-custom-001",
            "grade": "Junior",
            "major": "Computer Science",
            "skills": ["python", "network analysis"],
            "interests": ["social computing", "mentoring systems"],
            "experience_summary": "Built data and recommendation course projects.",
            "availability": "moderate",
            "resume_text": "",
        },
        top_k=3,
    )

    assert result["mode"] == "custom_profile_mode"
    assert result["student_profile"]["student_id"] == "cli-custom-001"
    assert result["skill3_result"]["mentor_candidates"]
    assert result["skill4_result"]["mentor_project_teammate_recommendations"]
    assert result["skill5_result"]["recommendations"]["mentors"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_custom_mode.py -q`

Expected: FAIL because `recommend_for_profile` does not exist yet

- [ ] **Step 3: Extend Skill 4 adapter and orchestrator for custom profiles**

```python
# progrec_agent/adapters/skill4_adapter.py
from __future__ import annotations

import json
from pathlib import Path

from skill4_handoff.skill.discovery import discover_projects_and_teammates
from skill4_handoff.skill.skill2_adapter import load_academic_graph


def run_skill4_custom_mode(
    *,
    repo_root: Path,
    student_profile: dict[str, object],
    skill3_result: dict[str, object],
    output_path: Path,
) -> dict[str, object]:
    students_payload = json.loads(
        (repo_root / "skill2_handoff/outputs/student_profiles_standard.json").read_text(encoding="utf-8")
    )
    all_students = list(students_payload.get("students") or [])
    graph_path = repo_root / "skill2_handoff/regenerate_kit/data/processed/academic_graph.json"
    graph = load_academic_graph(graph_path) if graph_path.is_file() else None
    result = discover_projects_and_teammates(
        target_student_id=str(student_profile["student_id"]),
        target_student_profile=student_profile,
        all_student_profiles=all_students,
        mentor_candidates=list(skill3_result.get("mentor_candidates") or []),
        graph=graph,
        mock_projects_path=repo_root / "skill4_handoff/data/mock_projects.json",
        top_n_projects=3,
        top_n_teammates=3,
        max_candidate_teammates=120,
        data_sources={"mode": "custom_profile_mode"},
    )
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
```

```python
# progrec_agent/orchestrator.py
    def recommend_for_profile(self, student_profile: dict[str, object], top_k: int = 5) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        skill5_path = self.temp_dir / "skill5.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_custom_mode(
            repo_root=self.repo_root,
            student_profile=student_profile,
            skill3_result=skill3_result,
            output_path=skill4_path,
        )
        skill5_result = run_skill5(
            repo_root=self.repo_root,
            skill3_path=skill3_path,
            skill4_path=skill4_path,
            output_path=skill5_path,
            student_id=str(student_profile["student_id"]),
            top_k=top_k,
        )
        return {
            "mode": "custom_profile_mode",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_mode"},
            "skill3_result": skill3_result,
            "skill4_result": skill4_result,
            "skill5_result": skill5_result,
            "temporary_paths": [skill3_path, skill4_path, skill5_path],
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_progrec_agent_custom_mode.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/adapters/skill4_adapter.py progrec_agent/orchestrator.py tests/test_progrec_agent_custom_mode.py
git commit -m "feat: add custom-profile ProgRec orchestration"
```

### Task 5: Add terminal rendering and REPL commands

**Files:**
- Create: `progrec_agent/render.py`
- Create: `progrec_agent/repl.py`
- Test: `tests/test_progrec_agent_repl.py`

- [ ] **Step 1: Write the failing rendering and REPL tests**

```python
from pathlib import Path

from progrec_agent.render import render_mentor_detail, render_summary


def test_render_summary_contains_mode_and_sections() -> None:
    summary = render_summary(
        {
            "mode": "dataset_mode",
            "student_profile": {"student_id": "s_002"},
            "skill5_result": {
                "recommendations": {
                    "mentors": [{"rank": 1, "mentor_id": "m_001", "final_score": 0.88}],
                    "projects": [{"rank": 1, "project_id": "p_001", "final_score": 0.73}],
                    "teammates": [{"rank": 1, "student_id": "s_015", "final_score": 0.69}],
                }
            },
        }
    )

    assert "dataset_mode" in summary
    assert "Top Mentors" in summary
    assert "Top Projects" in summary
    assert "Top Teammates" in summary


def test_render_mentor_detail_includes_projects_and_teammates() -> None:
    text = render_mentor_detail(
        mentor={"mentor_id": "m_001", "mentor_name": "Ada", "final_score": 0.88, "explanation": "Strong topic alignment."},
        skill4_bundle={
            "project_recommendations": [{"project_id": "p_001", "title": "Graph Lab"}],
            "teammate_recommendations": [{"student_id": "s_010", "reason": "Complementary skills"}],
        },
    )

    assert "m_001" in text
    assert "Graph Lab" in text
    assert "s_010" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_repl.py -q`

Expected: FAIL because `render.py` and `repl.py` do not exist yet

- [ ] **Step 3: Write the minimal renderer and REPL**

```python
# progrec_agent/render.py
from __future__ import annotations


def render_summary(result: dict[str, object]) -> str:
    skill5 = result["skill5_result"]
    recs = skill5["recommendations"]
    lines = [
        f"Mode: {result['mode']}",
        f"Student: {result['student_profile']['student_id']}",
        "Top Mentors:",
    ]
    for mentor in recs["mentors"][:3]:
        lines.append(f"  {mentor['rank']}. {mentor['mentor_id']} ({mentor['final_score']:.3f})")
    lines.append("Top Projects:")
    for project in recs["projects"][:3]:
        lines.append(f"  {project['rank']}. {project['project_id']} ({project['final_score']:.3f})")
    lines.append("Top Teammates:")
    for teammate in recs["teammates"][:3]:
        lines.append(f"  {teammate['rank']}. {teammate['student_id']} ({teammate['final_score']:.3f})")
    return "\n".join(lines)


def render_mentor_detail(mentor: dict[str, object], skill4_bundle: dict[str, object]) -> str:
    projects = skill4_bundle.get("project_recommendations") or []
    teammates = skill4_bundle.get("teammate_recommendations") or []
    lines = [
        f"Mentor: {mentor.get('mentor_name') or mentor.get('mentor_id')}",
        f"ID: {mentor.get('mentor_id')}",
        f"Final score: {mentor.get('final_score')}",
        f"Explanation: {mentor.get('explanation', '')}",
        "Projects:",
    ]
    for project in projects[:3]:
        lines.append(f"  - {project.get('project_id')}: {project.get('title', '')}")
    lines.append("Teammates:")
    for teammate in teammates[:3]:
        lines.append(f"  - {teammate.get('student_id')}: {teammate.get('reason', '')}")
    return "\n".join(lines)
```

```python
# progrec_agent/repl.py
from __future__ import annotations

from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator
from progrec_agent.render import render_mentor_detail, render_summary
from progrec_agent.session import AgentSession


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".progrec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    session = AgentSession(temp_dir=temp_dir)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    print("ProgRec Agent CLI")
    print("Commands: recommend, show mentor <id>, show profile, restart, help, exit")
    while True:
        command = input("> ").strip()
        if command == "exit":
            return 0
        if command == "help":
            print("Commands: recommend, show mentor <id>, show profile, restart, help, exit")
            continue
        if command == "restart":
            session.reset()
            print("Session cleared.")
            continue
        if command == "show profile":
            print(session.student_profile or "No active profile.")
            continue
        if command.startswith("show mentor "):
            mentor_id = command.removeprefix("show mentor ").strip()
            if not session.skill5_result:
                print("Run recommend first.")
                continue
            mentors = session.skill5_result["recommendations"]["mentors"]
            mentor = next((item for item in mentors if item["mentor_id"] == mentor_id), None)
            bundles = session.skill4_result["mentor_project_teammate_recommendations"]
            bundle = next((item for item in bundles if item["mentor_id"] == mentor_id), {})
            print(render_mentor_detail(mentor, bundle) if mentor else "Mentor not found.")
            continue
        if command == "recommend":
            print("1) existing student_id")
            print("2) manual profile")
            choice = input("Select mode: ").strip()
            if choice == "1":
                student_id = input("student_id: ").strip()
                result = orchestrator.recommend_for_student_id(student_id)
            else:
                profile = {
                    "student_id": input("student_id (or blank for temp id): ").strip() or "cli-custom-manual",
                    "grade": input("grade: ").strip(),
                    "major": input("major: ").strip(),
                    "skills": [part.strip().lower() for part in input("skills: ").split(",") if part.strip()],
                    "interests": [part.strip().lower() for part in input("interests: ").split(",") if part.strip()],
                    "experience_summary": input("experience_summary: ").strip(),
                    "availability": input("availability: ").strip().lower() or "moderate",
                    "resume_text": input("resume_text (optional): ").strip(),
                }
                result = orchestrator.recommend_for_profile(profile)
            session.set_mode(result["mode"])
            session.set_student_profile(result["student_profile"])
            session.set_resource_context(result["resource_context"])
            session.set_results(
                skill3_result=result["skill3_result"],
                skill4_result=result["skill4_result"],
                skill5_result=result["skill5_result"],
                temporary_paths=result["temporary_paths"],
            )
            print(render_summary(result))
            continue
        print("Unknown command. Type 'help' for supported commands.")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/test_progrec_agent_repl.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/render.py progrec_agent/repl.py tests/test_progrec_agent_repl.py
git commit -m "feat: add ProgRec CLI interaction layer"
```

### Task 6: Add README usage notes and full verification coverage

**Files:**
- Modify: `README.md`
- Test: `tests/test_progrec_agent_integration.py`

- [ ] **Step 1: Write the failing integration and smoke tests**

```python
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
```

```markdown
## ProgRec Agent CLI

Run the interactive agent from the repository root:

```bash
python3 -m progrec_agent.repl
```

Supported commands:
- `recommend`
- `show mentor <id>`
- `show profile`
- `restart`
- `help`
- `exit`
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/test_progrec_agent_integration.py -q`

Expected: FAIL because the REPL module is incomplete or not yet wired into the repo

- [ ] **Step 3: Update README and close the remaining gaps**

```python
# tests/test_progrec_agent_integration.py
def test_dataset_mode_recommend_command_smoke() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [sys.executable, "-m", "progrec_agent.repl"]
    completed = subprocess.run(
        cmd,
        input="recommend\n1\ns_002\nexit\n",
        text=True,
        capture_output=True,
        cwd=repo_root,
    )

    assert completed.returncode == 0
    assert "Top Mentors" in completed.stdout
```

```markdown
# README.md

Add one new section near Quick Start documenting:
- the `python3 -m progrec_agent.repl` entrypoint
- the two input modes
- the fixed command set
- the fact that manual profile mode is approximate and labeled `custom_profile_mode`
```

- [ ] **Step 4: Run the full verification suite**

Run: `python3 -m pytest tests/test_progrec_agent_session.py tests/test_progrec_agent_adapters.py tests/test_progrec_agent_orchestrator.py tests/test_progrec_agent_custom_mode.py tests/test_progrec_agent_repl.py tests/test_progrec_agent_integration.py -q`

Expected: PASS

Run: `python3 -m pytest tests/test_skill3_cli.py skill4_handoff/tests/test_pipeline.py -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_progrec_agent_integration.py
git commit -m "docs: document ProgRec CLI agent usage"
```

## Self-Review

### Spec coverage

- REPL architecture is covered in Task 5.
- Session persistence and restart behavior are covered in Task 1.
- Skill 1 normalization and Skill 2 resource resolution are covered in Task 2.
- Dataset-backed Skill 3 → Skill 4 → Skill 5 orchestration is covered in Task 3.
- Manual custom-profile flow is covered in Task 4.
- Rendering, drill-down behavior, smoke tests, and README updates are covered in Tasks 5 and 6.

### Placeholder scan

- No `TBD`, `TODO`, or deferred "implement later" steps remain.
- Each task includes concrete file paths, test names, code snippets, and exact commands.

### Type consistency

- Session fields use `skill3_result`, `skill4_result`, `skill5_result` consistently across tests and implementation.
- The mode strings remain `dataset_mode` and `custom_profile_mode` throughout the plan.
- The orchestrator returns `temporary_paths`, which matches `AgentSession.set_results(...)`.

