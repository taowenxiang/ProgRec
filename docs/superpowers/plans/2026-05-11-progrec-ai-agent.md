# ProgRec AI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `progrec_agent` from a fixed CLI wrapper into a natural-language, LLM-driven tool-using AI agent with clarification, planning, bounded reruns, and decision traces.

**Architecture:** Add an agent layer inside `progrec_agent/` that sits between the CLI and the existing skill adapters. Keep Skills 3 to 5 as the recommendation core, while the new layer owns intent understanding, structured profile enrichment, tool planning, strategy adjustment, result judging, and explanation rendering.

**Tech Stack:** Python 3, stdlib `unittest`, existing `progrec_agent` package, existing skill adapters, external LLM API over HTTPS via stdlib `urllib` or `http.client`

---

## File Structure

### New files

- Create: `progrec_agent/agent_schema.py`
- Create: `progrec_agent/llm_client.py`
- Create: `progrec_agent/prompts.py`
- Create: `progrec_agent/profile_enricher.py`
- Create: `progrec_agent/strategy.py`
- Create: `progrec_agent/result_judge.py`
- Create: `progrec_agent/tools.py`
- Create: `progrec_agent/planner.py`
- Create: `progrec_agent/explainer.py`
- Create: `progrec_agent/tests/test_agent_schema.py`
- Create: `progrec_agent/tests/test_llm_client.py`
- Create: `progrec_agent/tests/test_profile_enricher.py`
- Create: `progrec_agent/tests/test_strategy.py`
- Create: `progrec_agent/tests/test_result_judge.py`
- Create: `progrec_agent/tests/test_tools.py`
- Create: `progrec_agent/tests/test_planner.py`
- Create: `progrec_agent/tests/test_repl_agent_flow.py`

### Existing files to modify

- Modify: `progrec_agent/models.py`
- Modify: `progrec_agent/session.py`
- Modify: `progrec_agent/orchestrator.py`
- Modify: `progrec_agent/render.py`
- Modify: `progrec_agent/repl.py`
- Modify: `README.md`

### Existing files to leave mostly unchanged

- Keep stable: `skill3_mentor_discovery/`
- Keep stable: `skill4_program_teammate_discovery/`
- Keep stable: `skill5_student_recommendation_ranker/`
- Keep stable: `progrec_agent/config.py`
- Keep stable: `progrec_agent/schemas.py`

## Task 1: Add Agent Data Models And Session Memory

**Files:**
- Create: `progrec_agent/agent_schema.py`
- Modify: `progrec_agent/models.py`
- Modify: `progrec_agent/session.py`
- Test: `progrec_agent/tests/test_agent_schema.py`

- [ ] **Step 1: Write the failing tests for agent data structures and session behavior**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_schema import AgentProfile, ClarificationQuestion, ExecutionPlan
from progrec_agent.session import AgentSession


class TestAgentSchema(unittest.TestCase):
    def test_agent_profile_defaults(self) -> None:
        profile = AgentProfile(goal="find an NLP mentor")
        self.assertEqual(profile.goal, "find an NLP mentor")
        self.assertEqual(profile.research_direction, [])
        self.assertEqual(profile.desired_outcomes, [])
        self.assertFalse(profile.preferences["prefer_diversity"])

    def test_execution_plan_defaults(self) -> None:
        plan = ExecutionPlan()
        self.assertFalse(plan.need_clarification)
        self.assertFalse(plan.run_skill3)
        self.assertEqual(plan.clarification_questions, [])

    def test_session_tracks_agent_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.conversation_history.append({"role": "user", "content": "hello"})
            session.rerun_count = 1
            self.assertEqual(session.conversation_history[0]["role"], "user")
            self.assertEqual(session.rerun_count, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_agent_schema -v`  
Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.agent_schema` or missing `AgentSession` fields.

- [ ] **Step 3: Add the agent schema module**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ClarificationQuestion:
    key: str
    question: str


@dataclass
class AgentProfile:
    goal: str
    research_direction: list[str] = field(default_factory=list)
    desired_outcomes: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(
        default_factory=lambda: {
            "prefer_diversity": False,
            "prefer_low_commitment": False,
            "prefer_fast_onboarding": False,
            "collaboration_focus": "balanced",
        }
    )
    confidence: float = 0.0


@dataclass
class ExecutionPlan:
    need_clarification: bool = False
    clarification_questions: list[ClarificationQuestion] = field(default_factory=list)
    run_skill3: bool = False
    run_skill4: bool = False
    run_skill5: bool = False
    rerun_needed: bool = False
    stop_reason: str = ""
```

- [ ] **Step 4: Extend shared models and session state**

```python
# progrec_agent/models.py
from typing import Any, Literal, TypedDict

Mode = Literal["dataset_mode", "custom_profile_mode"]
JsonDict = dict[str, Any]


class ConversationTurn(TypedDict):
    role: str
    content: str
```

```python
# progrec_agent/session.py
from dataclasses import dataclass, field

from progrec_agent.models import ConversationTurn, JsonDict, Mode


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
    conversation_history: list[ConversationTurn] = field(default_factory=list)
    agent_profile: JsonDict | None = None
    latest_plan: JsonDict | None = None
    active_strategy: JsonDict | None = None
    decision_trace: list[str] = field(default_factory=list)
    rerun_count: int = 0
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_agent_schema -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/agent_schema.py progrec_agent/models.py progrec_agent/session.py progrec_agent/tests/test_agent_schema.py
git commit -m "feat: add agent session and schema models"
```

## Task 2: Add LLM Client And Prompt Catalog

**Files:**
- Create: `progrec_agent/llm_client.py`
- Create: `progrec_agent/prompts.py`
- Test: `progrec_agent/tests/test_llm_client.py`

- [ ] **Step 1: Write the failing tests for config validation and structured response parsing**

```python
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from progrec_agent.llm_client import LLMClient, LLMConfig


class TestLLMClient(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API key"):
            LLMConfig(model="gpt-4.1-mini", api_key="")

    @patch("progrec_agent.llm_client.urlopen")
    def test_parse_json_response(self, mock_urlopen) -> None:
        body = json.dumps({"output_text": "{\"goal\": \"nlp\"}"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = body
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))
        parsed = client.complete_json("prompt")
        self.assertEqual(parsed["goal"], "nlp")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_llm_client -v`  
Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.llm_client`.

- [ ] **Step 3: Implement a minimal provider-agnostic LLM client**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_key: str
    endpoint: str = "https://api.openai.com/v1/responses"
    temperature: float = 0.1

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("API key is required")


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(self, prompt: str) -> dict[str, object]:
        payload = {
            "model": self.config.model,
            "input": prompt,
            "temperature": self.config.temperature,
        }
        request = Request(
            self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        with urlopen(request) as response:
            raw = json.loads(response.read().decode("utf-8"))
        output_text = raw.get("output_text", "{}")
        return json.loads(output_text)
```

- [ ] **Step 4: Add prompt constants**

```python
INTENT_UNDERSTANDING_PROMPT = """
You are ProgRec's planning layer.
Return strict JSON with:
- goal
- research_direction
- desired_outcomes
- constraints
- preferences
"""

CLARIFICATION_PROMPT = """
Given the current agent profile, return strict JSON with:
- need_clarification
- clarification_questions
"""
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_llm_client -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/llm_client.py progrec_agent/prompts.py progrec_agent/tests/test_llm_client.py
git commit -m "feat: add llm client and prompt catalog"
```

## Task 3: Build Profile Enrichment And Preference Strategy Mapping

**Files:**
- Create: `progrec_agent/profile_enricher.py`
- Create: `progrec_agent/strategy.py`
- Test: `progrec_agent/tests/test_profile_enricher.py`
- Test: `progrec_agent/tests/test_strategy.py`

- [ ] **Step 1: Write the failing tests for natural-language profile extraction and strategy mapping**

```python
from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.profile_enricher import build_profiles_from_text
from progrec_agent.strategy import build_strategy


class TestProfileEnricher(unittest.TestCase):
    def test_build_profiles_from_text(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "goal": "find a trustworthy ai mentor",
            "research_direction": ["trustworthy ai", "nlp"],
            "constraints": {"time_budget_hours_per_week": 3},
            "preferences": {"prefer_low_commitment": True},
            "skill_profile": {
                "grade": "Junior",
                "major": "Computer Science",
                "skills": ["python"],
                "interests": ["nlp"],
                "experience_summary": "Built class projects",
                "availability": "low",
            },
        }
        skill_profile, agent_profile = build_profiles_from_text("I want NLP and low commitment", llm)
        self.assertEqual(skill_profile["major"], "Computer Science")
        self.assertTrue(agent_profile.preferences["prefer_low_commitment"])


class TestStrategy(unittest.TestCase):
    def test_build_strategy_from_preferences(self) -> None:
        strategy = build_strategy(
            {"constraints": {"time_budget_hours_per_week": 3}, "preferences": {"prefer_diversity": True}}
        )
        self.assertTrue(strategy["prefer_diversity"])
        self.assertEqual(strategy["top_k"], 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_profile_enricher progrec_agent.tests.test_strategy -v`  
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement profile enrichment using the LLM client**

```python
from __future__ import annotations

from progrec_agent.agent_schema import AgentProfile
from progrec_agent.adapters.skill1_adapter import normalize_manual_profile
from progrec_agent.prompts import INTENT_UNDERSTANDING_PROMPT


def build_profiles_from_text(user_text: str, llm_client) -> tuple[dict[str, object], AgentProfile]:
    payload = llm_client.complete_json(f"{INTENT_UNDERSTANDING_PROMPT}\nUser request: {user_text}")
    raw_skill = payload.get("skill_profile") or {}
    skill_profile = normalize_manual_profile(
        {
            "grade": str(raw_skill.get("grade", "")),
            "major": str(raw_skill.get("major", "")),
            "skills": ", ".join(raw_skill.get("skills", [])),
            "interests": ", ".join(raw_skill.get("interests", [])),
            "experience_summary": str(raw_skill.get("experience_summary", "")),
            "availability": str(raw_skill.get("availability", "moderate")),
            "resume_text": user_text,
        }
    )
    agent_profile = AgentProfile(
        goal=str(payload.get("goal", user_text)),
        research_direction=list(payload.get("research_direction") or []),
        desired_outcomes=list(payload.get("desired_outcomes") or []),
        constraints=dict(payload.get("constraints") or {}),
        preferences=dict(payload.get("preferences") or {}),
        confidence=float(payload.get("confidence", 0.0)),
    )
    return skill_profile, agent_profile
```

- [ ] **Step 4: Implement strategy mapping**

```python
from __future__ import annotations


def build_strategy(agent_profile: dict[str, object]) -> dict[str, object]:
    constraints = dict(agent_profile.get("constraints") or {})
    preferences = dict(agent_profile.get("preferences") or {})
    time_budget = int(constraints.get("time_budget_hours_per_week") or 0)
    return {
        "top_k": 5,
        "prefer_diversity": bool(preferences.get("prefer_diversity")),
        "prefer_low_commitment": bool(preferences.get("prefer_low_commitment") or (0 < time_budget <= 4)),
        "prefer_fast_onboarding": bool(preferences.get("prefer_fast_onboarding") or (0 < time_budget <= 4)),
        "exclude_topics": list(constraints.get("exclude_topics") or []),
        "max_reruns": 2,
    }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_profile_enricher progrec_agent.tests.test_strategy -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/profile_enricher.py progrec_agent/strategy.py progrec_agent/tests/test_profile_enricher.py progrec_agent/tests/test_strategy.py
git commit -m "feat: add profile enrichment and strategy mapping"
```

## Task 4: Wrap Existing Skill Adapters As Agent Tools And Refactor The Orchestrator

**Files:**
- Create: `progrec_agent/tools.py`
- Modify: `progrec_agent/orchestrator.py`
- Test: `progrec_agent/tests/test_tools.py`

- [ ] **Step 1: Write the failing tests for tool wrapper behavior**

```python
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent.tools import AgentTools


class TestAgentTools(unittest.TestCase):
    @patch("progrec_agent.tools.run_skill3")
    def test_run_mentor_discovery_tool(self, mock_skill3) -> None:
        mock_skill3.return_value = {"student_id": "s1", "mentor_candidates": []}
        tools = AgentTools(repo_root=Path("."), temp_dir=Path("."))
        result = tools.run_mentor_discovery_tool({"student_id": "s1"}, top_k=5)
        self.assertEqual(result["student_id"], "s1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_tools -v`  
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Add a tool wrapper class over the existing adapters**

```python
from __future__ import annotations

from pathlib import Path

from progrec_agent.adapters.skill3_adapter import run_skill3
from progrec_agent.adapters.skill4_adapter import run_skill4_custom_mode, run_skill4_dataset_mode
from progrec_agent.adapters.skill5_adapter import run_skill5


class AgentTools:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir

    def run_mentor_discovery_tool(self, student_profile: dict[str, object], top_k: int) -> dict[str, object]:
        return run_skill3(self.repo_root, student_profile, top_k)
```

- [ ] **Step 4: Refactor `orchestrator.py` into an execution helper instead of the top-level decision maker**

```python
class ProgRecOrchestrator:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.tools = AgentTools(repo_root=repo_root, temp_dir=temp_dir)

    def run_full_pipeline(self, student_profile: dict[str, object], student_id: str, top_k: int) -> dict[str, object]:
        skill3_result = self.tools.run_mentor_discovery_tool(student_profile, top_k)
        # keep existing skill4 / skill5 execution and alignment checks here
        return {"skill3_result": skill3_result}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_tools progrec_agent.tests.test_orchestrator_graph_skill3 -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/tools.py progrec_agent/orchestrator.py progrec_agent/tests/test_tools.py
git commit -m "refactor: expose skill adapters as agent tools"
```

## Task 5: Add Result Judging And Planner Logic

**Files:**
- Create: `progrec_agent/result_judge.py`
- Create: `progrec_agent/planner.py`
- Test: `progrec_agent/tests/test_result_judge.py`
- Test: `progrec_agent/tests/test_planner.py`

- [ ] **Step 1: Write the failing tests for clarification decisions and rerun decisions**

```python
from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.planner import build_execution_plan
from progrec_agent.result_judge import judge_results


class TestPlanner(unittest.TestCase):
    def test_requests_clarification_when_slots_missing(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "need_clarification": True,
            "clarification_questions": [{"key": "time_budget", "question": "How many hours per week?"}],
            "tool_plan": {"run_skill3": False, "run_skill4": False, "run_skill5": False},
        }
        plan = build_execution_plan({"goal": "find a mentor"}, llm)
        self.assertTrue(plan.need_clarification)
        self.assertEqual(plan.clarification_questions[0].key, "time_budget")


class TestResultJudge(unittest.TestCase):
    def test_flags_rerun_for_empty_projects(self) -> None:
        verdict = judge_results(
            skill5_result={"recommendations": {"mentors": [1], "projects": [], "teammates": [1]}},
            strategy={"max_reruns": 2},
            rerun_count=0,
        )
        self.assertTrue(verdict["rerun_needed"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_result_judge progrec_agent.tests.test_planner -v`  
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the result judge with bounded heuristics**

```python
from __future__ import annotations


def judge_results(*, skill5_result: dict[str, object], strategy: dict[str, object], rerun_count: int) -> dict[str, object]:
    recs = dict(skill5_result.get("recommendations") or {})
    mentors = list(recs.get("mentors") or [])
    projects = list(recs.get("projects") or [])
    teammates = list(recs.get("teammates") or [])
    reasons: list[str] = []
    if len(projects) < 3:
        reasons.append("project coverage too small")
    if len(mentors) < 3:
        reasons.append("mentor coverage too small")
    rerun_needed = bool(reasons) and rerun_count < int(strategy.get("max_reruns", 0))
    return {"rerun_needed": rerun_needed, "reasons": reasons, "stop_reason": "" if rerun_needed else "quality acceptable"}
```

- [ ] **Step 4: Implement the planner with structured JSON output and guardrails**

```python
from __future__ import annotations

from progrec_agent.agent_schema import ClarificationQuestion, ExecutionPlan
from progrec_agent.prompts import CLARIFICATION_PROMPT


def build_execution_plan(agent_profile: dict[str, object], llm_client) -> ExecutionPlan:
    payload = llm_client.complete_json(f"{CLARIFICATION_PROMPT}\nProfile: {agent_profile}")
    questions = [
        ClarificationQuestion(key=str(item["key"]), question=str(item["question"]))
        for item in list(payload.get("clarification_questions") or [])[:2]
    ]
    tool_plan = dict(payload.get("tool_plan") or {})
    return ExecutionPlan(
        need_clarification=bool(payload.get("need_clarification")),
        clarification_questions=questions,
        run_skill3=bool(tool_plan.get("run_skill3", True)),
        run_skill4=bool(tool_plan.get("run_skill4", True)),
        run_skill5=bool(tool_plan.get("run_skill5", True)),
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_result_judge progrec_agent.tests.test_planner -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/result_judge.py progrec_agent/planner.py progrec_agent/tests/test_result_judge.py progrec_agent/tests/test_planner.py
git commit -m "feat: add planner and result judge"
```

## Task 6: Upgrade The CLI Into A Natural-Language Agent Loop

**Files:**
- Modify: `progrec_agent/repl.py`
- Modify: `progrec_agent/render.py`
- Modify: `progrec_agent/session.py`
- Test: `progrec_agent/tests/test_repl_agent_flow.py`

- [ ] **Step 1: Write the failing tests for natural-language routing and `show trace`**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_agent import repl


class TestReplAgentFlow(unittest.TestCase):
    @patch("builtins.input", side_effect=["I want an NLP mentor", "exit"])
    @patch("progrec_agent.repl.run_agent_turn")
    def test_free_text_enters_agent_flow(self, mock_turn, _mock_input) -> None:
        mock_turn.return_value = "summary"
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_turn.assert_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: FAIL because `run_agent_turn` does not exist and the REPL only supports fixed commands.

- [ ] **Step 3: Add a natural-language turn handler and preserve support commands**

```python
def run_agent_turn(session: AgentSession, user_text: str, planner, orchestrator, explainer) -> str:
    session.conversation_history.append({"role": "user", "content": user_text})
    # call profile enricher, planner, orchestrator, judge, explainer
    return explainer.render_agent_summary(session)


def main() -> int:
    # keep help / show profile / show trace / show mentor / exit
    # otherwise treat input as a natural-language request
    if command == "show trace":
        print("\\n".join(session.decision_trace) or "No trace available.")
        continue
```

- [ ] **Step 4: Extend rendering to include trace-aware output**

```python
def render_agent_summary(session: AgentSession) -> str:
    lines = [
        f"Goal: {session.agent_profile.get('goal', '') if session.agent_profile else ''}",
        "Decision Trace:",
    ]
    lines.extend(f"  - {line}" for line in session.decision_trace[:5])
    return "\\n".join(lines)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/repl.py progrec_agent/render.py progrec_agent/session.py progrec_agent/tests/test_repl_agent_flow.py
git commit -m "feat: add natural language agent repl"
```

## Task 7: Integrate Strategy-Aware Reruns And Final Explanations

**Files:**
- Create: `progrec_agent/explainer.py`
- Modify: `progrec_agent/orchestrator.py`
- Modify: `progrec_agent/render.py`
- Test: `progrec_agent/tests/test_planner.py`
- Test: `progrec_agent/tests/test_repl_agent_flow.py`

- [ ] **Step 1: Write the failing tests for rerun traces and final explanation content**

```python
from __future__ import annotations

import unittest

from progrec_agent.explainer import build_final_response


class TestExplainer(unittest.TestCase):
    def test_build_final_response_includes_trace(self) -> None:
        text = build_final_response(
            agent_profile={"goal": "find mentor"},
            skill5_result={"recommendations": {"mentors": [], "projects": [], "teammates": []}},
            decision_trace=["Asked for clarification", "Reran with diversity bias"],
        )
        self.assertIn("Reran with diversity bias", text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_planner progrec_agent.tests.test_repl_agent_flow -v`  
Expected: FAIL due to missing explanation integration.

- [ ] **Step 3: Implement the explainer**

```python
from __future__ import annotations


def build_final_response(*, agent_profile: dict[str, object], skill5_result: dict[str, object], decision_trace: list[str]) -> str:
    recs = dict(skill5_result.get("recommendations") or {})
    return "\\n".join(
        [
            f"Goal: {agent_profile.get('goal', '')}",
            f"Top mentors: {len(list(recs.get('mentors') or []))}",
            "Decision Trace:",
            *[f"- {line}" for line in decision_trace],
        ]
    )
```

- [ ] **Step 4: Add bounded rerun handling in the agent loop**

```python
if verdict["rerun_needed"] and session.rerun_count < int(session.active_strategy.get("max_reruns", 0)):
    session.rerun_count += 1
    session.decision_trace.append(f"Reran with adjusted strategy: {', '.join(verdict['reasons'])}")
    session.active_strategy["prefer_diversity"] = True
    # rerun pipeline once with the updated strategy
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s progrec_agent/tests -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add progrec_agent/explainer.py progrec_agent/orchestrator.py progrec_agent/render.py progrec_agent/tests/test_planner.py progrec_agent/tests/test_repl_agent_flow.py
git commit -m "feat: add rerun traces and final explanations"
```

## Task 8: Document Configuration, Demo Flow, And Verify MVP

**Files:**
- Modify: `README.md`
- Optionally Create: `outputs/verified_demo/ai_agent_demo_notes.md`

- [ ] **Step 1: Add README setup instructions for the LLM-backed agent**

```md
## ProgRec AI Agent CLI

Set an API key before running:

```bash
export OPENAI_API_KEY=your_key_here
python3 -m progrec_agent.repl
```

Example requests:

- I want a mentor in trustworthy AI and NLP.
- I only have three hours per week.
- Recommend again, but prioritize teammate complementarity.
```

- [ ] **Step 2: Add a short demo script for live presentation**

```md
1. Start the CLI.
2. Enter: "I want an NLP mentor and easy onboarding."
3. Answer one clarification question about weekly time budget.
4. Show the first recommendation set.
5. Enter: "Recommend again, but prioritize teammate complementarity."
6. Run `show trace` to demonstrate planning and rerun behavior.
```

- [ ] **Step 3: Run verification commands**

Run: `python3 -m unittest discover -s progrec_agent/tests -v`  
Expected: PASS

Run: `python3 -m progrec_agent.repl`  
Expected: CLI starts and accepts free-text requests plus `show trace`.

- [ ] **Step 4: Commit**

```bash
git add README.md outputs/verified_demo/ai_agent_demo_notes.md
git commit -m "docs: add ai agent setup and demo flow"
```

## Self-Review Checklist

- Spec coverage:
  - natural-language CLI: covered in Tasks 6 and 8
  - profile extraction and enrichment: covered in Task 3
  - planner-driven tool usage: covered in Tasks 4 and 5
  - bounded clarification and reruns: covered in Tasks 5 and 7
  - final explanation and decision trace: covered in Tasks 6 and 7
- Placeholder scan:
  - no `TBD`, `TODO`, or unresolved scope markers remain in the task steps
- Type consistency:
  - shared agent concepts use `AgentProfile`, `ExecutionPlan`, `ConversationTurn`, `decision_trace`, and `active_strategy` consistently across tasks

## Recommended Execution Order

1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7
8. Task 8
