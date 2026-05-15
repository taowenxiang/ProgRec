# Semi-Autonomous Skill Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hard-coded chat pipeline with a semi-autonomous LLM agent that selects and executes only the ProgRec skills needed for the user's current goal.

**Architecture:** The new chat runtime uses an LLM action planner, a backend action validator, a target-specific tool executor, and an LLM response composer with deterministic fallback. The old slot-first flow (`QUESTION_BANK`, `TASK_REQUIRED_SLOTS`, `planner_v2`, and full-pipeline-by-default chat execution) is removed from the default `/agent` chat path.

**Tech Stack:** Python dataclasses, unittest/pytest, existing `LLMClient.complete_json`, FastAPI SSE chat route, ProgRec skill adapters, existing recommendation runtime helpers.

---

## File Structure

- Create `progrec_agent/agent_actions.py`: Planner action dataclasses, validation, JSON parsing, and repair-safe error objects.
- Create `progrec_agent/chat_tool_registry.py`: Registered chat tool schemas and target gating metadata.
- Create `progrec_agent/runtime/chat_tool_executor.py`: Executes registered chat tools and returns normalized tool results plus skill trace entries.
- Create `progrec_agent/agent_planner.py`: Builds the planner prompt and parses one LLM action at a time.
- Create `progrec_agent/response/composer.py`: Builds final user-facing replies from state, planner actions, and tool results.
- Modify `progrec_agent/dialog/state.py`: Add goal targets, profile context, planner actions, suggested actions, and tool result summaries.
- Modify `progrec_agent/runtime/recommendation_runtime.py`: Add mentor-only and project/teammate-specific runtime functions.
- Modify `progrec_agent/orchestrator.py`: Add mentor-only methods that call Skill 3 without Skill 4/5.
- Rewrite `progrec_agent/agent_core_v2.py`: Replace the hard-flow implementation with the semi-autonomous loop.
- Modify `progrec_service/runtime/agent_v2_runner.py`: Preserve API shape while exposing planner actions, suggested next actions, and target-specific results.
- Modify `progrec_service/services/sse.py`: Keep existing stages but map semi-autonomous turn types cleanly.
- Delete or decommission default-path use of `progrec_agent/policy/clarification.py`, `progrec_agent/dialog/slots.py`, and `progrec_agent/planning/planner_v2.py`.
- Update tests under `progrec_agent/tests/` and `progrec_service/tests/` to assert behavior rather than fixed clarification templates.

---

### Task 1: Add Planner Action Schema And Validation

**Files:**
- Create: `progrec_agent/agent_actions.py`
- Test: `progrec_agent/tests/test_agent_actions.py`

- [ ] **Step 1: Write failing validation tests**

Create `progrec_agent/tests/test_agent_actions.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.agent_actions import PlannerAction, parse_planner_action


class TestAgentActions(unittest.TestCase):
    def test_parse_ask_user_action(self) -> None:
        action = parse_planner_action(
            {
                "action": "ask_user",
                "message": "Tell me about your research background.",
                "reasoning_summary": "Need profile context.",
            },
            allowed_tools={"/mentor-discovery.rank_mentors"},
        )

        self.assertEqual(action.action, "ask_user")
        self.assertEqual(action.message, "Tell me about your research background.")
        self.assertEqual(action.reasoning_summary, "Need profile context.")

    def test_rejects_unknown_action(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_planner_action({"action": "dance"}, allowed_tools=set())

        self.assertIn("Unknown planner action", str(ctx.exception))

    def test_rejects_unknown_tool(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            parse_planner_action(
                {"action": "call_tool", "tool_name": "/unknown.run", "arguments": {}},
                allowed_tools={"/mentor-discovery.rank_mentors"},
            )

        self.assertIn("Unknown chat tool", str(ctx.exception))

    def test_call_tool_defaults_arguments(self) -> None:
        action = parse_planner_action(
            {"action": "call_tool", "tool_name": "/mentor-discovery.rank_mentors"},
            allowed_tools={"/mentor-discovery.rank_mentors"},
        )

        self.assertEqual(action.action, "call_tool")
        self.assertEqual(action.tool_name, "/mentor-discovery.rank_mentors")
        self.assertEqual(action.arguments, {})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_agent_actions.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.agent_actions'`.

- [ ] **Step 3: Implement action schema**

Create `progrec_agent/agent_actions.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


VALID_ACTIONS = {
    "ask_user",
    "call_tool",
    "answer_from_context",
    "suggest_next_steps",
    "stop",
}


@dataclass
class PlannerAction:
    action: str
    message: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    suggested_next_actions: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""


def parse_planner_action(payload: dict[str, Any], *, allowed_tools: set[str]) -> PlannerAction:
    action = str(payload.get("action") or "").strip()
    if action not in VALID_ACTIONS:
        raise ValueError(f"Unknown planner action {action!r}. Expected one of {sorted(VALID_ACTIONS)}.")

    tool_name = str(payload.get("tool_name") or "").strip()
    if action == "call_tool" and tool_name not in allowed_tools:
        raise ValueError(f"Unknown chat tool {tool_name!r}. Expected one of {sorted(allowed_tools)}.")

    raw_arguments = payload.get("arguments") or {}
    if not isinstance(raw_arguments, dict):
        raise ValueError("Planner action arguments must be a JSON object.")

    raw_suggestions = payload.get("suggested_next_actions") or []
    if not isinstance(raw_suggestions, list):
        raise ValueError("suggested_next_actions must be a JSON array.")

    return PlannerAction(
        action=action,
        message=str(payload.get("message") or "").strip(),
        tool_name=tool_name,
        arguments=dict(raw_arguments),
        suggested_next_actions=[item for item in raw_suggestions if isinstance(item, dict)],
        reasoning_summary=str(payload.get("reasoning_summary") or "").strip(),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_agent_actions.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/agent_actions.py progrec_agent/tests/test_agent_actions.py
git commit -m "feat: add chat planner action schema"
```

---

### Task 2: Add Chat Tool Registry

**Files:**
- Create: `progrec_agent/chat_tool_registry.py`
- Test: `progrec_agent/tests/test_chat_tool_registry.py`

- [ ] **Step 1: Write failing registry tests**

Create `progrec_agent/tests/test_chat_tool_registry.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.chat_tool_registry import get_chat_tool, list_chat_tools, planner_tool_context


class TestChatToolRegistry(unittest.TestCase):
    def test_lists_target_specific_tools(self) -> None:
        tool_names = [tool.name for tool in list_chat_tools()]

        self.assertIn("/student-profiling.build_temporary_profile", tool_names)
        self.assertIn("/mentor-discovery.rank_mentors", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_projects", tool_names)
        self.assertIn("/project-teammate-discovery.recommend_teammates", tool_names)

    def test_mentor_tool_is_gated_to_mentor_target(self) -> None:
        tool = get_chat_tool("/mentor-discovery.rank_mentors")

        self.assertEqual(tool.skill_id, "/mentor-discovery")
        self.assertEqual(tool.allowed_targets, ["mentor"])
        self.assertIn("profile", tool.required_arguments)

    def test_planner_context_mentions_no_extra_categories(self) -> None:
        context = planner_tool_context()

        self.assertIn("/mentor-discovery.rank_mentors", context)
        self.assertIn("Do not call this for project or teammate recommendations", context)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_chat_tool_registry.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.chat_tool_registry'`.

- [ ] **Step 3: Implement chat tool registry**

Create `progrec_agent/chat_tool_registry.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChatTool:
    name: str
    skill_id: str
    description: str
    required_arguments: list[str]
    optional_arguments: list[str] = field(default_factory=list)
    allowed_targets: list[str] = field(default_factory=list)
    planner_notes: str = ""


CHAT_TOOLS: dict[str, ChatTool] = {
    "/student-profiling.build_temporary_profile": ChatTool(
        name="/student-profiling.build_temporary_profile",
        skill_id="/student-profiling",
        description="Build a normalized temporary student profile from the conversation context.",
        required_arguments=["profile_context"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this before discovery tools when the chat does not already have a usable profile.",
    ),
    "/student-profiling.update_profile_context": ChatTool(
        name="/student-profiling.update_profile_context",
        skill_id="/student-profiling",
        description="Merge new user-provided profile details into the current profile context.",
        required_arguments=["profile_context"],
        optional_arguments=[],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this when the user answers a profile clarification question.",
    ),
    "/mentor-discovery.rank_mentors": ChatTool(
        name="/mentor-discovery.rank_mentors",
        skill_id="/mentor-discovery",
        description="Rank mentor candidates for the current student profile.",
        required_arguments=["profile"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor"],
        planner_notes="Do not call this for project or teammate recommendations.",
    ),
    "/project-teammate-discovery.recommend_projects": ChatTool(
        name="/project-teammate-discovery.recommend_projects",
        skill_id="/project-teammate-discovery",
        description="Recommend projects after a user requests projects or accepts a project follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["project"],
        planner_notes="Only call after the user requests projects or accepts a project suggestion.",
    ),
    "/project-teammate-discovery.recommend_teammates": ChatTool(
        name="/project-teammate-discovery.recommend_teammates",
        skill_id="/project-teammate-discovery",
        description="Recommend teammates after a user requests teammates or accepts a teammate follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["teammate"],
        planner_notes="Only call after the user requests teammates or accepts a teammate suggestion.",
    ),
    "/social-ranking.rerank_candidates": ChatTool(
        name="/social-ranking.rerank_candidates",
        skill_id="/social-ranking",
        description="Rerank a mixed set of mentors, projects, and teammates when the user asks for a combined package.",
        required_arguments=["skill3_result", "skill4_result"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Do not call for mentor-only requests.",
    ),
}


def list_chat_tools() -> list[ChatTool]:
    return list(CHAT_TOOLS.values())


def get_chat_tool(name: str) -> ChatTool:
    if name not in CHAT_TOOLS:
        raise KeyError(f"Unknown chat tool {name!r}. Known tools: {sorted(CHAT_TOOLS)}")
    return CHAT_TOOLS[name]


def allowed_tool_names() -> set[str]:
    return set(CHAT_TOOLS)


def planner_tool_context() -> str:
    lines: list[str] = []
    for tool in list_chat_tools():
        lines.append(
            "\n".join(
                [
                    f"tool: {tool.name}",
                    f"skill_id: {tool.skill_id}",
                    f"description: {tool.description}",
                    f"required_arguments: {', '.join(tool.required_arguments)}",
                    f"optional_arguments: {', '.join(tool.optional_arguments) or 'none'}",
                    f"allowed_targets: {', '.join(tool.allowed_targets) or 'any'}",
                    f"notes: {tool.planner_notes}",
                ]
            )
        )
    return "\n\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_chat_tool_registry.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/chat_tool_registry.py progrec_agent/tests/test_chat_tool_registry.py
git commit -m "feat: register target-specific chat tools"
```

---

### Task 3: Add Mentor-Only Runtime Execution

**Files:**
- Modify: `progrec_agent/orchestrator.py`
- Modify: `progrec_agent/runtime/recommendation_runtime.py`
- Test: `progrec_agent/tests/test_recommendation_runtime_targets.py`

- [ ] **Step 1: Write failing runtime tests**

Create `progrec_agent/tests/test_recommendation_runtime_targets.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from progrec_agent.runtime import recommendation_runtime


class TestRecommendationRuntimeTargets(unittest.TestCase):
    def test_mentor_only_profile_does_not_run_skill4_or_skill5(self) -> None:
        profile = {
            "student_id": "chat-temp-1",
            "grade": "undergraduate",
            "major": "computer science",
            "skills": ["nlp"],
            "interests": ["trustworthy ai"],
            "experience_summary": "medium experience",
            "availability": "summer research",
        }

        with tempfile.TemporaryDirectory() as td:
            fake_orchestrator = Mock()
            fake_orchestrator.rank_mentors_for_profile.return_value = {
                "mode": "custom_profile_mode",
                "student_profile": profile,
                "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
            }
            with patch(
                "progrec_agent.runtime.recommendation_runtime.ProgRecOrchestrator",
                return_value=fake_orchestrator,
            ):
                result = recommendation_runtime.run_mentor_recommendation_for_profile(
                    repo_root=Path("."),
                    temp_dir=Path(td),
                    profile=profile,
                    top_k=5,
                )

        fake_orchestrator.rank_mentors_for_profile.assert_called_once()
        self.assertIn("skill3_result", result)
        self.assertNotIn("skill4_result", result)
        self.assertNotIn("skill5_result", result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_recommendation_runtime_targets.py -q
```

Expected: FAIL with `AttributeError` for missing `run_mentor_recommendation_for_profile`.

- [ ] **Step 3: Add mentor-only orchestrator method**

Modify `progrec_agent/orchestrator.py` by adding this method inside `ProgRecOrchestrator`:

```python
    def rank_mentors_for_profile(self, student_profile: dict[str, object], top_k: int = 5) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill3_result = run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(skill3_result, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "mode": "custom_profile_mentor_only",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_mentor_only"},
            "skill3_result": skill3_result,
            "temporary_paths": [skill3_path],
        }
```

- [ ] **Step 4: Add mentor-only recommendation runtime**

Modify `progrec_agent/runtime/recommendation_runtime.py`:

```python
def run_mentor_recommendation_for_profile(*, repo_root, temp_dir, profile: dict[str, object], top_k: int):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.rank_mentors_for_profile(standardized, top_k=top_k)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_recommendation_runtime_targets.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/orchestrator.py progrec_agent/runtime/recommendation_runtime.py progrec_agent/tests/test_recommendation_runtime_targets.py
git commit -m "feat: add mentor-only recommendation runtime"
```

---

### Task 4: Add Chat Tool Executor

**Files:**
- Create: `progrec_agent/runtime/chat_tool_executor.py`
- Test: `progrec_agent/tests/test_chat_tool_executor.py`

- [ ] **Step 1: Write failing executor tests**

Create `progrec_agent/tests/test_chat_tool_executor.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor


class TestChatToolExecutor(unittest.TestCase):
    def test_build_temporary_profile_records_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/student-profiling.build_temporary_profile",
                {
                    "profile_context": {
                        "research_topic": "NLP and trustworthy AI",
                        "program_type": "undergraduate research",
                        "experience_level": "medium",
                    }
                },
            )

        self.assertEqual(result.skill_id, "/student-profiling")
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.payload["profile"]["interests"], ["NLP and trustworthy AI"])

    def test_rank_mentors_calls_mentor_only_runtime(self) -> None:
        runtime = Mock()
        runtime.run_mentor_recommendation_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/mentor-discovery.rank_mentors",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/mentor-discovery")
        self.assertIn("skill3_result", result.payload)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_chat_tool_executor.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.runtime.chat_tool_executor'`.

- [ ] **Step 3: Implement executor**

Create `progrec_agent/runtime/chat_tool_executor.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from progrec_agent.chat_tool_registry import get_chat_tool
from progrec_agent.runtime import recommendation_runtime as default_recommendation_runtime
from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


@dataclass
class ToolExecutionResult:
    tool_name: str
    skill_id: str
    status: str
    summary: str
    payload: dict[str, Any]

    def to_skill_trace_entry(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "summary": self.summary,
        }


class ChatToolExecutor:
    def __init__(self, *, repo_root: Path, temp_dir: Path, recommendation_runtime=None) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.recommendation_runtime = recommendation_runtime or default_recommendation_runtime

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> ToolExecutionResult:
        tool = get_chat_tool(tool_name)
        for required in tool.required_arguments:
            if required not in arguments:
                raise ValueError(f"Tool {tool_name} requires argument {required!r}.")

        if tool_name == "/student-profiling.build_temporary_profile":
            profile_context = dict(arguments["profile_context"])
            profile = standardize_temporary_profile(profile_context)
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Built a temporary student profile from the conversation context.",
                payload={"profile": profile},
            )

        if tool_name == "/student-profiling.update_profile_context":
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Updated the student profile context from the latest user message.",
                payload={"profile_context": dict(arguments["profile_context"])},
            )

        if tool_name == "/mentor-discovery.rank_mentors":
            payload = self.recommendation_runtime.run_mentor_recommendation_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Ranked mentor candidates for the current student profile.",
                payload=dict(payload),
            )

        raise ValueError(f"Tool {tool_name!r} is registered but has no executor implementation yet.")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_chat_tool_executor.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/runtime/chat_tool_executor.py progrec_agent/tests/test_chat_tool_executor.py
git commit -m "feat: execute registered chat tools"
```

---

### Task 5: Add Project And Teammate Tool Execution

**Files:**
- Modify: `progrec_agent/orchestrator.py`
- Modify: `progrec_agent/runtime/recommendation_runtime.py`
- Modify: `progrec_agent/runtime/chat_tool_executor.py`
- Test: `progrec_agent/tests/test_chat_project_teammate_tools.py`

- [ ] **Step 1: Write failing project/teammate tests**

Create `progrec_agent/tests/test_chat_project_teammate_tools.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor


class TestChatProjectTeammateTools(unittest.TestCase):
    def test_recommend_projects_calls_project_runtime(self) -> None:
        runtime = Mock()
        runtime.run_project_recommendations_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill4_result": {
                "mentor_project_teammate_recommendations": [
                    {"project_recommendations": [{"project_id": "p1"}], "teammate_recommendations": []}
                ]
            },
            "projects": [{"project_id": "p1"}],
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/project-teammate-discovery.recommend_projects",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        runtime.run_project_recommendations_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["projects"], [{"project_id": "p1"}])

    def test_recommend_teammates_calls_teammate_runtime(self) -> None:
        runtime = Mock()
        runtime.run_teammate_recommendations_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill4_result": {
                "mentor_project_teammate_recommendations": [
                    {"project_recommendations": [], "teammate_recommendations": [{"student_id": "s2"}]}
                ]
            },
            "teammates": [{"student_id": "s2"}],
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/project-teammate-discovery.recommend_teammates",
                {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
            )

        runtime.run_teammate_recommendations_for_profile.assert_called_once()
        self.assertEqual(result.skill_id, "/project-teammate-discovery")
        self.assertEqual(result.payload["teammates"], [{"student_id": "s2"}])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_chat_project_teammate_tools.py -q
```

Expected: FAIL because project and teammate chat tools are registered but not executable yet.

- [ ] **Step 3: Add Skill 4-only orchestrator method**

Modify `progrec_agent/orchestrator.py` by adding this method inside `ProgRecOrchestrator`:

```python
    def expand_projects_and_teammates_for_profile(
        self,
        student_profile: dict[str, object],
        top_k: int = 5,
        *,
        skill3_result: dict[str, object] | None = None,
    ) -> dict[str, object]:
        skill3_path = self.temp_dir / "skill3.json"
        skill4_path = self.temp_dir / "skill4.json"
        resolved_skill3 = skill3_result or run_skill3(self.repo_root, student_profile, top_k)
        skill3_path.write_text(json.dumps(resolved_skill3, ensure_ascii=False, indent=2), encoding="utf-8")
        skill4_result = run_skill4_custom_mode(
            repo_root=self.repo_root,
            student_profile=student_profile,
            skill3_result=resolved_skill3,
            output_path=skill4_path,
        )
        assert_agent_student_alignment(
            expected_student_id=str(student_profile["student_id"]),
            skill3_path=skill3_path,
            skill4_path=skill4_path,
        )
        return {
            "mode": "custom_profile_project_teammate_only",
            "student_profile": student_profile,
            "resource_context": {"resource_mode": "custom_profile_project_teammate_only"},
            "skill3_result": resolved_skill3,
            "skill4_result": skill4_result,
            "temporary_paths": [skill3_path, skill4_path],
        }
```

- [ ] **Step 4: Add project/teammate runtime functions**

Modify `progrec_agent/runtime/recommendation_runtime.py`:

```python
def _extract_skill4_items(skill4_result: dict[str, object], key: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for bundle in list(skill4_result.get("mentor_project_teammate_recommendations") or []):
        if not isinstance(bundle, dict):
            continue
        for item in list(bundle.get(key) or []):
            if isinstance(item, dict):
                items.append(item)
    return items


def run_project_recommendations_for_profile(
    *,
    repo_root,
    temp_dir,
    profile: dict[str, object],
    top_k: int,
    mentor_result: dict[str, object] | None = None,
):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    payload = orchestrator.expand_projects_and_teammates_for_profile(
        standardized,
        top_k=top_k,
        skill3_result=mentor_result,
    )
    skill4_result = dict(payload.get("skill4_result") or {})
    payload["projects"] = _extract_skill4_items(skill4_result, "project_recommendations")
    return payload


def run_teammate_recommendations_for_profile(
    *,
    repo_root,
    temp_dir,
    profile: dict[str, object],
    top_k: int,
    mentor_result: dict[str, object] | None = None,
):
    required = {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}
    standardized = dict(profile) if required.issubset(profile) else standardize_temporary_profile(profile)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    payload = orchestrator.expand_projects_and_teammates_for_profile(
        standardized,
        top_k=top_k,
        skill3_result=mentor_result,
    )
    skill4_result = dict(payload.get("skill4_result") or {})
    payload["teammates"] = _extract_skill4_items(skill4_result, "teammate_recommendations")
    return payload
```

- [ ] **Step 5: Implement executor branches**

Modify `ChatToolExecutor.execute` in `progrec_agent/runtime/chat_tool_executor.py`:

```python
        if tool_name == "/project-teammate-discovery.recommend_projects":
            payload = self.recommendation_runtime.run_project_recommendations_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                mentor_result=arguments.get("mentor_result") if isinstance(arguments.get("mentor_result"), dict) else None,
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Recommended projects for the current student profile.",
                payload=dict(payload),
            )

        if tool_name == "/project-teammate-discovery.recommend_teammates":
            payload = self.recommendation_runtime.run_teammate_recommendations_for_profile(
                repo_root=self.repo_root,
                temp_dir=self.temp_dir,
                profile=dict(arguments["profile"]),
                mentor_result=arguments.get("mentor_result") if isinstance(arguments.get("mentor_result"), dict) else None,
                top_k=int(arguments.get("top_k") or 5),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id=tool.skill_id,
                status="succeeded",
                summary="Recommended teammates for the current student profile.",
                payload=dict(payload),
            )
```

- [ ] **Step 6: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_chat_project_teammate_tools.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add progrec_agent/orchestrator.py progrec_agent/runtime/recommendation_runtime.py progrec_agent/runtime/chat_tool_executor.py progrec_agent/tests/test_chat_project_teammate_tools.py
git commit -m "feat: execute project and teammate chat tools"
```

---

### Task 6: Add Backend Target Gating

**Files:**
- Modify: `progrec_agent/agent_actions.py`
- Create: `progrec_agent/target_policy.py`
- Test: `progrec_agent/tests/test_target_policy.py`

- [ ] **Step 1: Write failing target policy tests**

Create `progrec_agent/tests/test_target_policy.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.dialog.state import DialogState
from progrec_agent.target_policy import infer_user_targets, is_tool_allowed_for_state


class TestTargetPolicy(unittest.TestCase):
    def test_infers_mentor_target(self) -> None:
        self.assertEqual(infer_user_targets("Help me find a mentor for NLP"), ["mentor"])

    def test_project_tool_blocked_for_mentor_only_request(self) -> None:
        state = DialogState(goal_targets=["mentor"], active_goal="mentor")

        self.assertFalse(is_tool_allowed_for_state("/project-teammate-discovery.recommend_projects", state))

    def test_project_tool_allowed_after_suggestion_acceptance(self) -> None:
        state = DialogState(
            goal_targets=["mentor"],
            active_goal="mentor",
            suggested_next_actions=[{"target": "project", "accepted": True}],
        )

        self.assertTrue(is_tool_allowed_for_state("/project-teammate-discovery.recommend_projects", state))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_target_policy.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.target_policy'`.

- [ ] **Step 3: Implement target policy**

Create `progrec_agent/target_policy.py`:

```python
from __future__ import annotations

from progrec_agent.chat_tool_registry import get_chat_tool


TARGET_KEYWORDS = {
    "mentor": ("mentor", "advisor", "professor", "supervisor"),
    "project": ("project", "research project", "opportunity"),
    "teammate": ("teammate", "team mate", "collaborator", "peer"),
}


def infer_user_targets(user_text: str) -> list[str]:
    text = user_text.lower()
    targets = [
        target
        for target, keywords in TARGET_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    return targets or ["mentor"]


def _accepted_targets(state) -> set[str]:
    accepted: set[str] = set()
    for item in list(state.suggested_next_actions or []):
        if isinstance(item, dict) and item.get("accepted") is True:
            target = str(item.get("target") or "")
            if target:
                accepted.add(target)
    return accepted


def is_tool_allowed_for_state(tool_name: str, state) -> bool:
    tool = get_chat_tool(tool_name)
    if tool.skill_id == "/student-profiling":
        return True
    allowed_targets = set(tool.allowed_targets)
    requested_targets = set(state.goal_targets or [])
    requested_targets.update(_accepted_targets(state))
    if not allowed_targets:
        return True
    return bool(allowed_targets & requested_targets)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_target_policy.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/target_policy.py progrec_agent/tests/test_target_policy.py
git commit -m "feat: enforce chat tool target gating"
```

---

### Task 7: Add LLM Action Planner

**Files:**
- Create: `progrec_agent/agent_planner.py`
- Test: `progrec_agent/tests/test_agent_planner.py`

- [ ] **Step 1: Write failing planner tests**

Create `progrec_agent/tests/test_agent_planner.py`:

```python
from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.agent_planner import AgentPlanner
from progrec_agent.dialog.state import DialogState


class TestAgentPlanner(unittest.TestCase):
    def test_planner_parses_llm_action(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "action": "ask_user",
            "message": "What kind of research opportunity are you targeting?",
            "reasoning_summary": "Need profile context.",
        }
        planner = AgentPlanner(llm_client=llm)

        action = planner.plan_next_action(DialogState(), "Find me an NLP mentor.")

        self.assertEqual(action.action, "ask_user")
        self.assertIn("research opportunity", action.message)
        prompt = llm.complete_json.call_args.args[0]
        self.assertIn("/mentor-discovery.rank_mentors", prompt)
        self.assertIn("Do not run extra recommendation categories", prompt)

    def test_invalid_llm_action_returns_safe_ask_user(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {"action": "call_tool", "tool_name": "/unknown.run"}
        planner = AgentPlanner(llm_client=llm)

        action = planner.plan_next_action(DialogState(), "Find me an NLP mentor.")

        self.assertEqual(action.action, "ask_user")
        self.assertIn("clarify", action.message.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_agent_planner.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.agent_planner'`.

- [ ] **Step 3: Implement planner**

Create `progrec_agent/agent_planner.py`:

```python
from __future__ import annotations

from dataclasses import asdict

from progrec_agent.agent_actions import PlannerAction, parse_planner_action
from progrec_agent.chat_tool_registry import allowed_tool_names, planner_tool_context


PLANNER_PROMPT = """
You are the semi-autonomous planner for ProgRec chat.
Choose exactly one next action as strict JSON.

Allowed actions:
- ask_user: ask one natural question when required information is missing.
- call_tool: call one registered tool.
- answer_from_context: answer using existing state or tool results.
- suggest_next_steps: offer optional follow-up skills without executing them.
- stop: finish the turn.

Rules:
- Satisfy the user's current target first.
- Do not run extra recommendation categories.
- Do not call project, teammate, or social ranking tools unless the user requested that target or accepted a suggestion.
- Do not invent student IDs, profile facts, mentor facts, or tool outputs.
- Ask the user when required arguments are missing or ambiguous.
- Return only JSON with keys: action, message, tool_name, arguments, suggested_next_actions, reasoning_summary.
""".strip()


class AgentPlanner:
    def __init__(self, *, llm_client) -> None:
        self.llm_client = llm_client

    def plan_next_action(self, state, user_text: str) -> PlannerAction:
        prompt = (
            f"{PLANNER_PROMPT}\n\n"
            f"Registered tools:\n{planner_tool_context()}\n\n"
            f"Dialog state:\n{asdict(state)}\n\n"
            f"Latest user message:\n{user_text}"
        )
        try:
            payload = self.llm_client.complete_json(prompt)
            return parse_planner_action(dict(payload), allowed_tools=allowed_tool_names())
        except Exception:
            return PlannerAction(
                action="ask_user",
                message="Could you clarify your goal and share a little more profile context so I can choose the right recommendation skill?",
                reasoning_summary="Planner action was invalid or unavailable.",
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_agent_planner.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/agent_planner.py progrec_agent/tests/test_agent_planner.py
git commit -m "feat: add semi-autonomous action planner"
```

---

### Task 8: Extend Dialog State For Semi-Autonomous Chat

**Files:**
- Modify: `progrec_agent/dialog/state.py`
- Modify: `progrec_service/runtime/agent_v2_runner.py`
- Test: `progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Write failing state round-trip test**

Add this test to `progrec_service/tests/test_agent_stream.py`:

```python
    def test_runner_preserves_semi_autonomous_state_fields(self) -> None:
        state = agent_v2_runner._dialog_state_from_payload(
            {
                "active_goal": "mentor",
                "goal_targets": ["mentor"],
                "profile_context": {"research_topic": "NLP"},
                "planner_actions": [{"action": "ask_user"}],
                "suggested_next_actions": [{"target": "project"}],
                "tool_results_summary": {"mentor_count": 5},
            }
        )

        self.assertEqual(state.active_goal, "mentor")
        self.assertEqual(state.goal_targets, ["mentor"])
        self.assertEqual(state.profile_context["research_topic"], "NLP")
        self.assertEqual(state.planner_actions[0]["action"], "ask_user")
        self.assertEqual(state.suggested_next_actions[0]["target"], "project")
        self.assertEqual(state.tool_results_summary["mentor_count"], 5)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_service/tests/test_agent_stream.py::TestAgentStream::test_runner_preserves_semi_autonomous_state_fields -q
```

Expected: FAIL with `AttributeError: 'DialogState' object has no attribute 'active_goal'`.

- [ ] **Step 3: Extend DialogState**

Modify `progrec_agent/dialog/state.py`:

```python
@dataclass
class DialogState:
    task: str = ""
    goal: str = ""
    active_goal: str = ""
    goal_targets: list[str] = field(default_factory=list)
    profile_context: dict[str, object] = field(default_factory=dict)
    planner_actions: list[dict[str, object]] = field(default_factory=list)
    suggested_next_actions: list[dict[str, object]] = field(default_factory=list)
    tool_results_summary: dict[str, object] = field(default_factory=dict)
    resolved_slots: dict[str, object] = field(default_factory=dict)
    candidate_slots: dict[str, object] = field(default_factory=dict)
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    pending_question: PendingQuestion | None = None
    conflicts: list[str] = field(default_factory=list)
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    clarification_turn_count: int = 0
    last_user_turn: str = ""
    last_agent_turn: str = ""
    skill_trace: list[dict[str, object]] = field(default_factory=list)
    last_skill_plan: dict[str, object] = field(default_factory=dict)
    last_result_summary: str = ""
```

- [ ] **Step 4: Preserve fields in service runner**

Modify `_dialog_state_from_payload` in `progrec_service/runtime/agent_v2_runner.py` by adding these constructor fields:

```python
        active_goal=str(payload.get("active_goal", "")),
        goal_targets=list(payload.get("goal_targets", []) or []),
        profile_context=dict(payload.get("profile_context", {}) or {}),
        planner_actions=list(payload.get("planner_actions", []) or []),
        suggested_next_actions=list(payload.get("suggested_next_actions", []) or []),
        tool_results_summary=dict(payload.get("tool_results_summary", {}) or {}),
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```bash
pytest progrec_service/tests/test_agent_stream.py::TestAgentStream::test_runner_preserves_semi_autonomous_state_fields -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/dialog/state.py progrec_service/runtime/agent_v2_runner.py progrec_service/tests/test_agent_stream.py
git commit -m "feat: persist semi-autonomous chat state"
```

---

### Task 9: Add Response Composer

**Files:**
- Create: `progrec_agent/response/composer.py`
- Test: `progrec_agent/tests/test_response_composer.py`

- [ ] **Step 1: Write failing composer tests**

Create `progrec_agent/tests/test_response_composer.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.response.composer import compose_fallback_reply


class TestResponseComposer(unittest.TestCase):
    def test_composes_mentor_result_reply(self) -> None:
        reply = compose_fallback_reply(
            turn_type="recommendation_result",
            tool_results_summary={"mentor_count": 2},
            suggested_next_actions=[{"target": "project", "label": "Find related projects"}],
        )

        self.assertIn("2 mentor", reply)
        self.assertIn("projects", reply.lower())

    def test_uses_question_for_clarification(self) -> None:
        reply = compose_fallback_reply(
            turn_type="clarification",
            next_question="What background should I use for your profile?",
            tool_results_summary={},
            suggested_next_actions=[],
        )

        self.assertEqual(reply, "What background should I use for your profile?")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
pytest progrec_agent/tests/test_response_composer.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.response.composer'`.

- [ ] **Step 3: Implement deterministic fallback composer**

Create `progrec_agent/response/composer.py`:

```python
from __future__ import annotations


def compose_fallback_reply(
    *,
    turn_type: str,
    tool_results_summary: dict[str, object],
    suggested_next_actions: list[dict[str, object]],
    next_question: str = "",
) -> str:
    if turn_type == "clarification" and next_question:
        return next_question

    if turn_type == "recommendation_result":
        mentor_count = int(tool_results_summary.get("mentor_count") or 0)
        if mentor_count:
            reply = f"I found {mentor_count} mentor recommendations for you."
        else:
            reply = "I finished the recommendation step."
        targets = [str(item.get("target") or "") for item in suggested_next_actions]
        if "project" in targets and "teammate" in targets:
            return reply + " Would you like me to look for related projects or teammates next?"
        if "project" in targets:
            return reply + " Would you like me to look for related projects next?"
        if "teammate" in targets:
            return reply + " Would you like me to look for teammates next?"
        return reply

    return "I updated the recommendation context."
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
pytest progrec_agent/tests/test_response_composer.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/response/composer.py progrec_agent/tests/test_response_composer.py
git commit -m "feat: compose semi-autonomous chat replies"
```

---

### Task 10: Rewrite AgentCoreV2 Around Semi-Autonomous Loop

**Files:**
- Modify: `progrec_agent/agent_core_v2.py`
- Test: `progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Replace hard-flow tests with semi-autonomous behavior tests**

In `progrec_agent/tests/test_agent_core_v2.py`, replace fixed slot-question tests with:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestAgentCoreV2(unittest.TestCase):
    def test_first_turn_uses_planner_question_not_question_bank(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me a bit about your NLP background and the opportunity you want.",
                "reasoning_summary": "Need profile context before mentor discovery.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

            reply, state = core.handle_message(DialogState(), "Help me find a mentor for NLP and trustworthy AI.")

        self.assertIn("NLP background", reply)
        self.assertNotIn("What kind of program are you targeting", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")
        self.assertEqual(state.planner_actions[-1]["action"], "ask_user")

    def test_complete_mentor_request_runs_mentor_discovery_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.build_temporary_profile",
                    "arguments": {
                        "profile_context": {
                            "research_topic": "NLP and trustworthy AI",
                            "program_type": "undergraduate research",
                            "experience_level": "medium",
                        }
                    },
                    "reasoning_summary": "Build profile.",
                },
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.rank_mentors",
                    "arguments": {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
                    "reasoning_summary": "Rank mentors only.",
                },
                {
                    "action": "suggest_next_steps",
                    "message": "I found mentors. Would you like related projects next?",
                    "suggested_next_actions": [{"target": "project", "label": "Find related projects"}],
                    "reasoning_summary": "Original mentor request is satisfied.",
                },
            ]
            runtime = Mock()
            runtime.run_mentor_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, state = core.handle_message(
                DialogState(),
                "Find an NLP mentor for undergraduate research. My experience is medium.",
            )

        runtime.run_mentor_recommendation_for_profile.assert_called_once()
        self.assertIn("mentor", reply.lower())
        self.assertEqual(state.execution_context.last_turn_type, "recommendation_result")
        self.assertIn("/mentor-discovery", [entry["skill_id"] for entry in state.skill_trace])
        self.assertNotIn("/project-teammate-discovery", [entry["skill_id"] for entry in state.skill_trace])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail on hard flow**

Run:

```bash
pytest progrec_agent/tests/test_agent_core_v2.py -q
```

Expected: FAIL because `AgentCoreV2` still uses the hard clarification and full-pipeline planner.

- [ ] **Step 3: Rewrite AgentCoreV2**

Replace `progrec_agent/agent_core_v2.py` with:

```python
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from progrec_agent.agent_planner import AgentPlanner
from progrec_agent.dialog.state import DialogState
from progrec_agent.response.composer import compose_fallback_reply
from progrec_agent.runtime import recommendation_runtime as recommendation_runtime_module
from progrec_agent.runtime.chat_tool_executor import ChatToolExecutor, ToolExecutionResult
from progrec_agent.target_policy import infer_user_targets, is_tool_allowed_for_state


MAX_AGENT_STEPS = 4


class AgentCoreV2:
    def __init__(
        self,
        *,
        repo_root,
        temp_dir,
        llm_client,
        recommendation_runtime=None,
        inspection_runtime=None,
        validation_runtime=None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self.temp_dir = Path(temp_dir)
        self.llm_client = llm_client
        self.recommendation_runtime = recommendation_runtime or recommendation_runtime_module
        self.planner = AgentPlanner(llm_client=llm_client)
        self.executor = ChatToolExecutor(
            repo_root=self.repo_root,
            temp_dir=self.temp_dir,
            recommendation_runtime=self.recommendation_runtime,
        )

    def _record_tool_result(self, state: DialogState, result: ToolExecutionResult) -> None:
        state.skill_trace.append(result.to_skill_trace_entry())
        if result.tool_name == "/student-profiling.build_temporary_profile":
            state.profile_context.update(dict(result.payload.get("profile") or {}))
        if result.tool_name == "/mentor-discovery.rank_mentors":
            state.execution_context.result_handle = "latest"
            state.execution_context.last_result = dict(result.payload)
            candidates = list(dict(result.payload.get("skill3_result") or {}).get("mentor_candidates") or [])
            state.tool_results_summary["mentor_count"] = len(candidates)

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        working.last_user_turn = user_text
        if not working.goal_targets:
            working.goal_targets = infer_user_targets(user_text)
        if not working.active_goal and working.goal_targets:
            working.active_goal = working.goal_targets[0]

        reply_text = ""
        for _step in range(MAX_AGENT_STEPS):
            action = self.planner.plan_next_action(working, user_text)
            working.planner_actions.append(asdict(action))
            working.last_skill_plan = asdict(action)

            if action.action == "ask_user":
                reply_text = action.message
                working.execution_context.last_turn_type = "clarification"
                working.execution_context.next_question = reply_text
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "call_tool":
                if not is_tool_allowed_for_state(action.tool_name, working):
                    reply_text = "I can do that, but I need you to confirm this new recommendation target first."
                    working.execution_context.last_turn_type = "clarification"
                    working.execution_context.next_question = reply_text
                    working.last_agent_turn = reply_text
                    return reply_text, working
                result = self.executor.execute(action.tool_name, action.arguments)
                self._record_tool_result(working, result)
                if action.tool_name == "/mentor-discovery.rank_mentors":
                    working.execution_context.last_turn_type = "recommendation_result"
                continue

            if action.action == "suggest_next_steps":
                working.suggested_next_actions = list(action.suggested_next_actions)
                reply_text = action.message or compose_fallback_reply(
                    turn_type=working.execution_context.last_turn_type or "recommendation_result",
                    tool_results_summary=working.tool_results_summary,
                    suggested_next_actions=working.suggested_next_actions,
                )
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "answer_from_context":
                reply_text = action.message or compose_fallback_reply(
                    turn_type=working.execution_context.last_turn_type,
                    tool_results_summary=working.tool_results_summary,
                    suggested_next_actions=working.suggested_next_actions,
                )
                working.last_agent_turn = reply_text
                return reply_text, working

            if action.action == "stop":
                break

        reply_text = reply_text or compose_fallback_reply(
            turn_type=working.execution_context.last_turn_type or "recommendation_result",
            tool_results_summary=working.tool_results_summary,
            suggested_next_actions=working.suggested_next_actions,
            next_question=working.execution_context.next_question,
        )
        working.last_agent_turn = reply_text
        return reply_text, working
```

- [ ] **Step 4: Run core tests**

Run:

```bash
pytest progrec_agent/tests/test_agent_core_v2.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/agent_core_v2.py progrec_agent/tests/test_agent_core_v2.py
git commit -m "feat: replace hard chat flow with agent loop"
```

---

### Task 11: Update Service Structured Results

**Files:**
- Modify: `progrec_service/runtime/agent_v2_runner.py`
- Modify: `progrec_service/services/sse.py`
- Test: `progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Update service tests**

Replace `test_runner_returns_clarification_turn_contract` in `progrec_service/tests/test_agent_stream.py` with:

```python
    def test_runner_returns_semi_autonomous_clarification_contract(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.return_value = {
                "action": "ask_user",
                "message": "Tell me about your background and target research opportunity.",
                "reasoning_summary": "Need profile context.",
            }
            result = agent_v2_runner.run_agent_turn(
                repo_root=__import__("pathlib").Path("."),
                dialog_state_payload={},
                runtime_context=_RuntimeContext(),
                user_text="Find an NLP mentor.",
            )

        self.assertEqual(result["structured_result"]["turn_type"], "clarification")
        self.assertEqual(result["structured_result"]["next_question"], "Tell me about your background and target research opportunity.")
        self.assertEqual(result["structured_result"]["planner_actions"][0]["action"], "ask_user")
        self.assertNotIn("program_type", result["structured_result"]["missing_slots"])
```

Add this mentor-only runner test:

```python
    def test_runner_returns_mentor_only_skill_usage(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/student-profiling.build_temporary_profile",
                    "arguments": {
                        "profile_context": {
                            "research_topic": "NLP",
                            "program_type": "undergraduate research",
                            "experience_level": "medium",
                        }
                    },
                },
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.rank_mentors",
                    "arguments": {"profile": {"student_id": "chat-temp-1"}, "top_k": 5},
                },
                {
                    "action": "answer_from_context",
                    "message": "I found mentor recommendations. Want projects next?",
                },
            ]
            with patch(
                "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
                return_value={
                    "student_profile": {"student_id": "chat-temp-1"},
                    "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
                },
            ):
                result = agent_v2_runner.run_agent_turn(
                    repo_root=__import__("pathlib").Path("."),
                    dialog_state_payload={},
                    runtime_context=_RuntimeContext(),
                    user_text="Find an NLP mentor for undergraduate research.",
                )

        skill_ids = [entry["skill_id"] for entry in result["structured_result"]["skill_usage"]]
        self.assertIn("/student-profiling", skill_ids)
        self.assertIn("/mentor-discovery", skill_ids)
        self.assertNotIn("/project-teammate-discovery", skill_ids)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
pytest progrec_service/tests/test_agent_stream.py -q
```

Expected: FAIL because structured result does not expose planner actions or semi-autonomous summaries yet.

- [ ] **Step 3: Update structured result mapper**

Modify `_structured_result_from_state` in `progrec_service/runtime/agent_v2_runner.py`:

```python
    structured: dict[str, object] = {
        "turn_type": turn_type,
        "intent": state.active_goal or state.task,
        "active_goal": state.active_goal,
        "goal_targets": list(state.goal_targets),
        "missing_slots": list(state.missing_slots),
        "next_question": state.execution_context.next_question,
        "last_result_handle": state.execution_context.result_handle,
        "skill_usage": list(state.skill_trace or []),
        "planner_actions": list(state.planner_actions or []),
        "suggested_next_actions": list(state.suggested_next_actions or []),
        "tool_results_summary": dict(state.tool_results_summary or {}),
    }
```

Keep the existing `recommendation_result` package block, but guard it for both `skill5_result` and mentor-only `skill3_result`:

```python
    if turn_type == "recommendation_result" and state.execution_context.last_result:
        last_result = dict(state.execution_context.last_result)
        if "skill5_result" in last_result:
            structured["summary"] = summarize_pipeline_result(last_result)
            structured["recommendation_result"] = normalize_result_package(last_result)
        else:
            structured["summary"] = dict(state.tool_results_summary)
            structured["recommendation_result"] = make_json_safe(last_result)
```

- [ ] **Step 4: Verify SSE stage mapping**

Modify `_stage_for_turn` in `progrec_service/services/sse.py` if needed:

```python
    return {
        "clarification": "collecting_context",
        "inspection": "inspecting_result",
        "recommendation_result": "running_recommendation",
        "resource_validation": "validating_resources",
        "agent_update": "selecting_skills",
    }.get(turn_type, "running_recommendation")
```

- [ ] **Step 5: Run service tests**

Run:

```bash
pytest progrec_service/tests/test_agent_stream.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add progrec_service/runtime/agent_v2_runner.py progrec_service/services/sse.py progrec_service/tests/test_agent_stream.py
git commit -m "feat: expose semi-autonomous chat results"
```

---

### Task 12: Remove Hard-Flow Defaults And Tests

**Files:**
- Delete or stop importing: `progrec_agent/policy/clarification.py`
- Delete or stop importing: `progrec_agent/dialog/slots.py`
- Delete or stop importing: `progrec_agent/planning/planner_v2.py`
- Modify/delete tests that assert `QUESTION_BANK`, `TASK_REQUIRED_SLOTS`, or `recommend_full_pipeline` chat behavior.
- Test: `progrec_agent/tests/test_clarification_policy.py`
- Test: `progrec_agent/tests/test_planner_v2.py`
- Test: `progrec_agent/tests/test_conversation_e2e_v2.py`

- [ ] **Step 1: Find remaining hard-flow imports**

Run:

```bash
rg -n "QUESTION_BANK|TASK_REQUIRED_SLOTS|choose_next_question|planner_v2|recommend_full_pipeline|program_type\".*experience_level" progrec_agent progrec_service
```

Expected: Some tests and legacy modules still reference the old flow.

- [ ] **Step 2: Delete old default-flow tests**

Delete tests that only verify the old hard policy:

```bash
git rm progrec_agent/tests/test_clarification_policy.py
git rm progrec_agent/tests/test_planner_v2.py
```

If `test_conversation_e2e_v2.py` asserts fixed question order or full-pipeline behavior, rewrite it to assert:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestConversationE2EV2(unittest.TestCase):
    def test_mentor_only_conversation_uses_mentor_skill_only(self) -> None:
        llm = Mock()
        llm.complete_json.side_effect = [
            {"action": "ask_user", "message": "Tell me your background and target opportunity."},
        ]
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            reply, state = core.handle_message(DialogState(), "Find me an NLP mentor.")

        self.assertIn("background", reply)
        self.assertEqual(state.execution_context.last_turn_type, "clarification")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Remove old modules if no runtime imports remain**

Run:

```bash
rg -n "progrec_agent\\.policy\\.clarification|progrec_agent\\.dialog\\.slots|progrec_agent\\.planning\\.planner_v2|choose_next_question|TASK_REQUIRED_SLOTS" progrec_agent progrec_service
```

If the command only returns the old modules themselves, delete them:

```bash
git rm progrec_agent/policy/clarification.py
git rm progrec_agent/dialog/slots.py
git rm progrec_agent/planning/planner_v2.py
```

- [ ] **Step 4: Run targeted suite**

Run:

```bash
pytest progrec_agent/tests/test_agent_actions.py \
  progrec_agent/tests/test_chat_tool_registry.py \
  progrec_agent/tests/test_chat_tool_executor.py \
  progrec_agent/tests/test_agent_planner.py \
  progrec_agent/tests/test_agent_core_v2.py \
  progrec_service/tests/test_agent_stream.py -q
```

Expected: PASS.

- [ ] **Step 5: Verify hard-flow strings are not in default chat path**

Run:

```bash
rg -n "What kind of program are you targeting|What is your current experience level|recommend_full_pipeline" progrec_agent progrec_service
```

Expected: No matches in default chat runtime files. Matches in docs or archived tests are acceptable only if they are historical references.

- [ ] **Step 6: Commit**

```bash
git add progrec_agent progrec_service
git commit -m "refactor: remove hard-flow chat policy"
```

---

### Task 13: Final Verification

**Files:**
- No new files unless a test exposes a necessary small fix.

- [ ] **Step 1: Run agent and service tests**

Run:

```bash
pytest progrec_agent/tests progrec_service/tests -q
```

Expected: PASS, except unrelated pre-existing tests should be recorded with exact failure names before continuing.

- [ ] **Step 2: Run hard-flow regression search**

Run:

```bash
rg -n "QUESTION_BANK|TASK_REQUIRED_SLOTS|choose_next_question|What kind of program are you targeting|What is your current experience level|recommend_full_pipeline" progrec_agent progrec_service
```

Expected: No matches in runtime code used by `/agent/sessions/{session_id}/messages`.

- [ ] **Step 3: Run chat route smoke test**

Run:

```bash
pytest progrec_service/tests/test_agent_stream.py::TestAgentStream::test_message_route_streams_stage_result_and_done_events -q
```

Expected: PASS and SSE still emits `message.accepted`, `agent.stage`, `agent.result`, and `done`.

- [ ] **Step 4: Commit final fixes if any**

If final verification required fixes:

```bash
git add progrec_agent progrec_service
git commit -m "test: verify semi-autonomous chat agent"
```

If no fixes were needed, do not create an empty commit.
