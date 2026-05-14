# ProgRec Conversational Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `progrec_agent` into a chat-first repository-local agent that can route user requests, execute safe recommendation and inspection tools automatically, and require confirmation before risky Skill 1 and Skill 2 actions.

**Architecture:** Keep the current skill adapters and recommendation algorithms intact, but move the agent behavior into a reusable `agent core` composed of session state, intent routing, execution policy, tool registry/executor, and natural-language response synthesis. The terminal REPL becomes a thin frontend over that core.

**Tech Stack:** Python 3, stdlib `unittest`, existing `progrec_agent` modules, existing Skill 1 through Skill 5 adapters, optional OpenAI Responses API through `LLMClient`

---

### Task 1: Expand Shared Agent State

**Files:**
- Modify: `progrec_agent/agent_schema.py`
- Modify: `progrec_agent/session.py`
- Modify: `progrec_agent/models.py`
- Modify: `progrec_agent/tests/test_agent_schema.py`

- [ ] **Step 1: Write the failing session-state tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_schema import PendingConfirmation, RouterDecision
from progrec_agent.session import AgentSession


class TestAgentSchema(unittest.TestCase):
    def test_router_decision_defaults(self) -> None:
        decision = RouterDecision(intent="chat", confidence=0.2, candidate_tools=[])
        self.assertEqual(decision.intent, "chat")
        self.assertEqual(decision.candidate_tools, [])
        self.assertFalse(decision.needs_clarification)

    def test_session_tracks_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            pending = PendingConfirmation(
                action_id="rebuild-graph-1",
                tool_name="rebuild_skill2_graph",
                arguments={"mode": "graph"},
                prompt="Rebuild graph now?",
            )
            session.set_pending_confirmation(pending)
            self.assertEqual(session.pending_confirmation_action["tool_name"], "rebuild_skill2_graph")
            session.clear_pending_confirmation()
            self.assertIsNone(session.pending_confirmation_action)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_agent_schema -v`  
Expected: FAIL with `ImportError` or `AttributeError` because `PendingConfirmation`, `RouterDecision`, or the new session helpers do not exist yet.

- [ ] **Step 3: Add the shared routing and confirmation dataclasses**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal["recommend", "explain", "inspect", "debug", "rebuild", "help", "chat"]
RiskLevel = Literal["safe", "confirm", "restricted"]


@dataclass
class PendingConfirmation:
    action_id: str
    tool_name: str
    arguments: dict[str, Any]
    prompt: str


@dataclass
class RouterDecision:
    intent: IntentName
    confidence: float
    candidate_tools: list[str]
    needs_clarification: bool = False
    clarification_question: str = ""
    reasoning_summary: str = ""


@dataclass
class ToolExecutionResult:
    tool_name: str
    ok: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str = ""
```

Add those classes to `progrec_agent/agent_schema.py` below the existing `AgentProfile` and `ExecutionPlan` types.

- [ ] **Step 4: Extend `AgentSession` to store routing and confirmation state**

```python
from dataclasses import asdict

# inside AgentSession
last_router_decision: JsonDict | None = None
last_response_summary: str = ""
pending_confirmation_action: JsonDict | None = None

def set_last_router_decision(self, decision: object) -> None:
    self.last_router_decision = asdict(decision) if hasattr(decision, "__dataclass_fields__") else dict(decision)

def set_last_response_summary(self, summary: str) -> None:
    self.last_response_summary = summary

def set_pending_confirmation(self, pending: object) -> None:
    self.pending_confirmation_action = (
        asdict(pending) if hasattr(pending, "__dataclass_fields__") else dict(pending)
    )

def clear_pending_confirmation(self) -> None:
    self.pending_confirmation_action = None
```

Also widen `ConversationTurn` in `progrec_agent/models.py` to allow assistant messages to be stored in the same structure:

```python
class ConversationTurn(TypedDict):
    role: str
    content: str
```

Keep that shape intact, but make sure the new assistant responses are appended by later tasks.

- [ ] **Step 5: Re-run the tests and commit the state scaffolding**

Run: `python3 -m unittest progrec_agent.tests.test_agent_schema -v`  
Expected: PASS

```bash
git add progrec_agent/agent_schema.py progrec_agent/session.py progrec_agent/models.py progrec_agent/tests/test_agent_schema.py
git commit -m "feat: expand conversational agent session state"
```

### Task 2: Add the Tool Registry and Tool Executor

**Files:**
- Create: `progrec_agent/tool_registry.py`
- Create: `progrec_agent/tool_executor.py`
- Modify: `progrec_agent/tools.py`
- Create: `progrec_agent/tests/test_tool_registry.py`
- Create: `progrec_agent/tests/test_tool_executor.py`

- [ ] **Step 1: Write failing tests for tool metadata and safe read-only tools**

In `progrec_agent/tests/test_tool_registry.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.tool_registry import get_tool, list_tools


class TestToolRegistry(unittest.TestCase):
    def test_rebuild_graph_requires_confirmation(self) -> None:
        tool = get_tool("rebuild_skill2_graph")
        self.assertEqual(tool["risk_level"], "confirm")
        self.assertTrue(tool["requires_confirmation"])

    def test_recommendation_tool_is_safe(self) -> None:
        tool = get_tool("recommend_full_pipeline")
        self.assertEqual(tool["risk_level"], "safe")
```

In `progrec_agent/tests/test_tool_executor.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.tool_executor import ToolExecutor
from progrec_agent.session import AgentSession


class TestToolExecutor(unittest.TestCase):
    def test_show_current_profile_returns_session_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_student_profile({"student_id": "s_002", "major": "CS"})
            executor = ToolExecutor(repo_root=Path("."), temp_dir=Path(td))
            result = executor.execute("show_current_profile", {}, session=session)
            self.assertTrue(result.ok)
            self.assertEqual(result.payload["student_profile"]["student_id"], "s_002")
```

- [ ] **Step 2: Run the registry and executor tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_tool_registry progrec_agent.tests.test_tool_executor -v`  
Expected: FAIL with `ModuleNotFoundError` because the new modules do not exist yet.

- [ ] **Step 3: Create `tool_registry.py` with stable metadata**

```python
from __future__ import annotations

TOOLS: dict[str, dict[str, object]] = {
    "recommend_full_pipeline": {
        "name": "recommend_full_pipeline",
        "purpose": "Run Skill 3, Skill 4, and Skill 5 for one student or drafted profile.",
        "intent_tags": ["recommend"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "run_recommendation",
    },
    "show_current_profile": {
        "name": "show_current_profile",
        "purpose": "Return the active student profile from session state.",
        "intent_tags": ["inspect", "explain"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "show_current_profile",
    },
    "inspect_artifacts": {
        "name": "inspect_artifacts",
        "purpose": "Inspect the latest skill artifacts and surface high-level metadata.",
        "intent_tags": ["inspect", "debug"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "inspect_artifacts",
    },
    "debug_graph_mode": {
        "name": "debug_graph_mode",
        "purpose": "Check graph-mode prerequisites and alignment for a student_id.",
        "intent_tags": ["debug"],
        "risk_level": "safe",
        "requires_confirmation": False,
        "side_effects": [],
        "executor_name": "debug_graph_mode",
    },
    "rebuild_skill2_graph": {
        "name": "rebuild_skill2_graph",
        "purpose": "Regenerate Skill 2 processed graph artifacts.",
        "intent_tags": ["rebuild"],
        "risk_level": "confirm",
        "requires_confirmation": True,
        "side_effects": ["refreshes processed graph artifacts"],
        "executor_name": "rebuild_skill2_graph",
    },
    "rebuild_skill1_profiles": {
        "name": "rebuild_skill1_profiles",
        "purpose": "Refresh Skill 1 normalized profiles when an external generator is configured.",
        "intent_tags": ["rebuild"],
        "risk_level": "confirm",
        "requires_confirmation": True,
        "side_effects": ["refreshes normalized profile artifacts"],
        "executor_name": "rebuild_skill1_profiles",
    },
}


def get_tool(name: str) -> dict[str, object]:
    return dict(TOOLS[name])


def list_tools() -> list[dict[str, object]]:
    return [dict(TOOLS[name]) for name in TOOLS]
```

- [ ] **Step 4: Create `tool_executor.py` and route safe tools through existing adapters**

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from progrec_agent.agent_schema import ToolExecutionResult
from progrec_agent.config import resolve_repo_root, resolve_resource_config
from progrec_agent.orchestrator import ProgRecOrchestrator


class ToolExecutor:
    def __init__(self, *, repo_root: Path, temp_dir: Path) -> None:
        self.repo_root = resolve_repo_root(repo_root)
        self.temp_dir = temp_dir
        self.orchestrator = ProgRecOrchestrator(repo_root=self.repo_root, temp_dir=self.temp_dir)

    def execute(self, tool_name: str, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return ToolExecutionResult(tool_name=tool_name, ok=False, error=f"Unknown tool: {tool_name}")
        return handler(arguments, session=session)

    def _tool_show_current_profile(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="show_current_profile",
            ok=True,
            payload={"student_profile": dict(session.student_profile or {})},
        )

    def _tool_inspect_artifacts(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        artifacts = {
            "mode": session.mode,
            "temporary_paths": [str(path) for path in session.temporary_paths],
            "resource_context": dict(session.resource_context or {}),
        }
        return ToolExecutionResult(tool_name="inspect_artifacts", ok=True, payload=artifacts)

    def _tool_debug_graph_mode(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        bundle = resolve_resource_config("graph", self.repo_root, validate_graph=False)
        return ToolExecutionResult(
            tool_name="debug_graph_mode",
            ok=True,
            payload={
                "student_id": str(arguments.get("student_id") or ""),
                "graph_exists": bool(bundle.skill2_graph and bundle.skill2_graph.exists()),
                "students_path": str(bundle.skill2_students),
                "mentors_path": str(bundle.skill2_mentors),
                "graph_path": str(bundle.skill2_graph) if bundle.skill2_graph else "",
            },
        )

    def _tool_rebuild_skill2_graph(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        script = self.repo_root / "skill2_academic_graph_builder" / "regenerate_kit" / "scripts" / "build_graph.py"
        completed = subprocess.run(
            ["python3", str(script)],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return ToolExecutionResult(tool_name="rebuild_skill2_graph", ok=False, error=completed.stderr.strip())
        return ToolExecutionResult(tool_name="rebuild_skill2_graph", ok=True, payload={"stdout": completed.stdout.strip()})

    def _tool_rebuild_skill1_profiles(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
        return ToolExecutionResult(
            tool_name="rebuild_skill1_profiles",
            ok=False,
            error="Skill 1 rebuild is not configured in-repo; provide an external entrypoint before enabling this tool.",
        )
```

Also repurpose `progrec_agent/tools.py` into a thin compatibility wrapper:

```python
from progrec_agent.tool_executor import ToolExecutor
```

- [ ] **Step 5: Run the tool tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_tool_registry progrec_agent.tests.test_tool_executor -v`  
Expected: PASS

```bash
git add progrec_agent/tool_registry.py progrec_agent/tool_executor.py progrec_agent/tools.py progrec_agent/tests/test_tool_registry.py progrec_agent/tests/test_tool_executor.py
git commit -m "feat: add conversational agent tool registry"
```

### Task 3: Build the Intent Router and Execution Policy

**Files:**
- Create: `progrec_agent/intent_router.py`
- Create: `progrec_agent/execution_policy.py`
- Modify: `progrec_agent/prompts.py`
- Create: `progrec_agent/tests/test_intent_router.py`
- Create: `progrec_agent/tests/test_execution_policy.py`

- [ ] **Step 1: Write failing router and policy tests**

```python
from __future__ import annotations

import unittest

from progrec_agent.agent_schema import PendingConfirmation, RouterDecision
from progrec_agent.execution_policy import choose_action
from progrec_agent.intent_router import route_user_message


class TestIntentRouter(unittest.TestCase):
    def test_recommend_keywords_route_to_recommend(self) -> None:
        decision = route_user_message("Find me an NLP mentor", llm_client=None, session=None)
        self.assertEqual(decision.intent, "recommend")
        self.assertIn("recommend_full_pipeline", decision.candidate_tools)

    def test_rebuild_keywords_route_to_rebuild(self) -> None:
        decision = route_user_message("Rebuild the graph artifacts", llm_client=None, session=None)
        self.assertEqual(decision.intent, "rebuild")
        self.assertIn("rebuild_skill2_graph", decision.candidate_tools)


class TestExecutionPolicy(unittest.TestCase):
    def test_confirmation_required_for_confirm_tool(self) -> None:
        decision = RouterDecision(intent="rebuild", confidence=0.9, candidate_tools=["rebuild_skill2_graph"])
        action = choose_action(decision, tool_name="rebuild_skill2_graph", tool_meta={"risk_level": "confirm"})
        self.assertEqual(action["kind"], "confirm")

    def test_low_confidence_routes_to_clarification(self) -> None:
        decision = RouterDecision(intent="chat", confidence=0.3, candidate_tools=[], needs_clarification=True, clarification_question="Which student?")
        action = choose_action(decision, tool_name="", tool_meta={})
        self.assertEqual(action["kind"], "clarify")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_intent_router progrec_agent.tests.test_execution_policy -v`  
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Add a dedicated router prompt and a deterministic fallback**

```python
ROUTER_PROMPT = """
You are the routing layer for ProgRec.
Return strict JSON with:
- intent
- confidence
- candidate_tools
- needs_clarification
- clarification_question
- reasoning_summary
""".strip()
```

Create `route_user_message()` in `progrec_agent/intent_router.py`:

```python
from __future__ import annotations

from progrec_agent.agent_schema import RouterDecision
from progrec_agent.prompts import ROUTER_PROMPT


def route_user_message(user_text: str, *, llm_client, session) -> RouterDecision:
    normalized = user_text.lower().strip()
    if llm_client is not None:
        payload = llm_client.complete_json(f"{ROUTER_PROMPT}\nUser message: {user_text}")
        return RouterDecision(
            intent=str(payload.get("intent", "chat")),
            confidence=float(payload.get("confidence", 0.0)),
            candidate_tools=[str(item) for item in payload.get("candidate_tools", [])],
            needs_clarification=bool(payload.get("needs_clarification")),
            clarification_question=str(payload.get("clarification_question", "")),
            reasoning_summary=str(payload.get("reasoning_summary", "")),
        )
    if any(word in normalized for word in ["mentor", "recommend", "project", "teammate"]):
        return RouterDecision(intent="recommend", confidence=0.8, candidate_tools=["recommend_full_pipeline"])
    if "rebuild" in normalized and "graph" in normalized:
        return RouterDecision(intent="rebuild", confidence=0.9, candidate_tools=["rebuild_skill2_graph"])
    if any(word in normalized for word in ["why", "debug", "mismatch", "graph mode"]):
        return RouterDecision(intent="debug", confidence=0.75, candidate_tools=["debug_graph_mode", "inspect_artifacts"])
    if any(word in normalized for word in ["show profile", "current profile"]):
        return RouterDecision(intent="inspect", confidence=0.9, candidate_tools=["show_current_profile"])
    return RouterDecision(
        intent="chat",
        confidence=0.35,
        candidate_tools=[],
        needs_clarification=True,
        clarification_question="Do you want recommendations, an explanation, or a graph/debug check?",
        reasoning_summary="Fallback router could not confidently classify the request.",
    )
```

- [ ] **Step 4: Implement the policy gate**

```python
from __future__ import annotations


def choose_action(decision, *, tool_name: str, tool_meta: dict[str, object]) -> dict[str, object]:
    if decision.needs_clarification and decision.clarification_question:
        return {"kind": "clarify", "question": decision.clarification_question}
    if decision.confidence < 0.5 and decision.clarification_question:
        return {"kind": "clarify", "question": decision.clarification_question}
    if tool_meta.get("risk_level") == "confirm":
        return {"kind": "confirm", "tool_name": tool_name}
    if tool_name:
        return {"kind": "execute", "tool_name": tool_name}
    return {"kind": "answer_only"}
```

- [ ] **Step 5: Re-run the router/policy tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_intent_router progrec_agent.tests.test_execution_policy -v`  
Expected: PASS

```bash
git add progrec_agent/intent_router.py progrec_agent/execution_policy.py progrec_agent/prompts.py progrec_agent/tests/test_intent_router.py progrec_agent/tests/test_execution_policy.py
git commit -m "feat: add agent routing and policy gates"
```

### Task 4: Create the Agent Core Turn Loop

**Files:**
- Create: `progrec_agent/agent_core.py`
- Create: `progrec_agent/response_synthesizer.py`
- Modify: `progrec_agent/profile_enricher.py`
- Create: `progrec_agent/tests/test_agent_core.py`

- [ ] **Step 1: Write failing end-to-end turn tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class _StubExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, tool_name: str, arguments: dict[str, object], *, session):
        self.calls.append((tool_name, arguments))
        from progrec_agent.agent_schema import ToolExecutionResult
        return ToolExecutionResult(tool_name=tool_name, ok=True, payload={"tool_name": tool_name})


class TestAgentCore(unittest.TestCase):
    def test_recommend_message_executes_safe_tool(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("tool_name", reply)

    def test_rebuild_message_creates_pending_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            reply = core.handle_message(session, "Rebuild the graph artifacts")
            self.assertIn("Do you want me to continue", reply)
            self.assertIsNotNone(session.pending_confirmation_action)
```

- [ ] **Step 2: Run the agent-core tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.agent_core`.

- [ ] **Step 3: Create `AgentCore` and implement pending confirmation handling**

First create `progrec_agent/response_synthesizer.py` so the core can depend on it:

```python
from __future__ import annotations


def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if not result.ok:
        return f"I tried to run `{result.tool_name}`, but it failed: {result.error}"
    return f"I handled your request with `{result.tool_name}`."
```

Then create `progrec_agent/agent_core.py`:

```python
from __future__ import annotations

import uuid
from pathlib import Path

from progrec_agent.agent_schema import PendingConfirmation
from progrec_agent.execution_policy import choose_action
from progrec_agent.intent_router import route_user_message
from progrec_agent.response_synthesizer import synthesize_reply
from progrec_agent.tool_executor import ToolExecutor
from progrec_agent.tool_registry import get_tool


class AgentCore:
    def __init__(self, *, repo_root: Path, temp_dir: Path, executor=None, llm_client=None) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.llm_client = llm_client
        self.executor = executor or ToolExecutor(repo_root=repo_root, temp_dir=temp_dir)

    def handle_message(self, session, user_text: str) -> str:
        normalized = user_text.strip().lower()
        if session.pending_confirmation_action and normalized in {"yes", "y", "confirm", "continue"}:
            pending = dict(session.pending_confirmation_action)
            session.clear_pending_confirmation()
            result = self.executor.execute(pending["tool_name"], dict(pending["arguments"]), session=session)
            return synthesize_reply(session=session, user_text=user_text, decision=None, result=result)

        decision = route_user_message(user_text, llm_client=self.llm_client, session=session)
        session.set_last_router_decision(decision)
        tool_name = decision.candidate_tools[0] if decision.candidate_tools else ""
        tool_meta = get_tool(tool_name) if tool_name else {}
        action = choose_action(decision, tool_name=tool_name, tool_meta=tool_meta)

        if action["kind"] == "clarify":
            session.set_pending_clarification([{"key": "followup", "question": action["question"]}], user_text)
            return action["question"]

        if action["kind"] == "confirm":
            pending = PendingConfirmation(
                action_id=str(uuid.uuid4()),
                tool_name=tool_name,
                arguments={},
                prompt="I think this requires rebuilding the Skill 2 graph. That may refresh artifacts and take a few minutes. Do you want me to continue?",
            )
            session.set_pending_confirmation(pending)
            return pending.prompt

        if action["kind"] == "execute":
            result = self.executor.execute(tool_name, {}, session=session)
            return synthesize_reply(session=session, user_text=user_text, decision=decision, result=result)

        return "I need a bit more detail before I can decide what to run."
```

- [ ] **Step 4: Reuse profile drafting only when recommendation work needs a profile**

Update `progrec_agent/profile_enricher.py` with a helper that can draft a normalized profile lazily:

```python
def build_profile_if_needed(user_text: str, llm_client) -> tuple[dict[str, object], AgentProfile]:
    if llm_client is None:
        return normalize_manual_profile(
            {
                "grade": "",
                "major": "",
                "skills": "",
                "interests": "",
                "experience_summary": user_text,
                "availability": "moderate",
                "resume_text": user_text,
            }
        ), AgentProfile(goal=user_text, confidence=0.0)
    return build_profiles_from_text(user_text, llm_client)
```

Use that helper in `AgentCore` before invoking `recommend_full_pipeline` so recommendation turns can still use the current profile drafting path without forcing every debug/inspect message through profile synthesis.

- [ ] **Step 5: Re-run the agent-core tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: PASS

```bash
git add progrec_agent/agent_core.py progrec_agent/response_synthesizer.py progrec_agent/profile_enricher.py progrec_agent/tests/test_agent_core.py
git commit -m "feat: add conversational agent core loop"
```

### Task 5: Replace REPL Turn Logic with the Agent Core

**Files:**
- Modify: `progrec_agent/response_synthesizer.py`
- Modify: `progrec_agent/repl.py`
- Modify: `progrec_agent/render.py`
- Modify: `progrec_agent/tests/test_repl_agent_flow.py`

- [ ] **Step 1: Write the failing REPL integration tests**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_agent import repl


class TestReplAgentFlow(unittest.TestCase):
    @patch("builtins.input", side_effect=["Find me an NLP mentor", "exit"])
    @patch("progrec_agent.repl.AgentCore")
    def test_free_text_is_delegated_to_agent_core(self, mock_core, _mock_input) -> None:
        mock_core.return_value.handle_message.return_value = "Here are the top matches."
        exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        mock_core.return_value.handle_message.assert_called_once()
```

- [ ] **Step 2: Run the REPL test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: FAIL because `repl.py` still imports and uses `run_agent_turn()` directly.

- [ ] **Step 3: Expand the natural-language response synthesizer**

```python
from __future__ import annotations


def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if not result.ok:
        return f"I tried to run `{result.tool_name}`, but it failed: {result.error}"

    if result.tool_name == "show_current_profile":
        profile = result.payload.get("student_profile") or {}
        return f"Current profile: {profile}"

    if result.tool_name == "inspect_artifacts":
        return (
            "I inspected the current artifacts. "
            f"Mode: {result.payload.get('mode')}, files: {result.payload.get('temporary_paths')}"
        )

    if result.tool_name == "debug_graph_mode":
        return (
            "I checked graph-mode prerequisites. "
            f"Graph exists: {result.payload.get('graph_exists')}. "
            f"Students path: {result.payload.get('students_path')}"
        )

    return f"I handled your request with `{result.tool_name}`."
```

- [ ] **Step 4: Make the REPL a thin frontend**

Replace the free-text path in `progrec_agent/repl.py` with `AgentCore`:

```python
from progrec_agent.agent_core import AgentCore


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".progrec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    session = AgentSession(temp_dir=temp_dir)
    llm_client = _build_llm_client_from_env()
    core = AgentCore(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client)

    print("ProgRec Agent CLI")
    print(HELP_TEXT)
    while True:
        command = input("> ").strip()
        if command == "exit":
            return 0
        if command == "help":
            print(HELP_TEXT)
            continue
        if command == "restart":
            session.reset()
            print("Session cleared.")
            continue
        if command == "show profile":
            print(session.student_profile or "No active profile.")
            continue
        if command == "show trace":
            print("\n".join(session.decision_trace) if session.decision_trace else "No trace available.")
            continue
        print(core.handle_message(session, command))
```

Keep the existing explicit `show mentor <id>` command for now, but stop using `run_agent_turn()` as the primary path.

- [ ] **Step 5: Re-run the REPL tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: PASS

```bash
git add progrec_agent/response_synthesizer.py progrec_agent/repl.py progrec_agent/render.py progrec_agent/tests/test_repl_agent_flow.py
git commit -m "feat: route repl through conversational agent core"
```

### Task 6: Add Recommendation Execution, Debug Helpers, and Conversation Regressions

**Files:**
- Modify: `progrec_agent/tool_executor.py`
- Modify: `progrec_agent/agent_core.py`
- Modify: `progrec_agent/response_synthesizer.py`
- Modify: `README.md`
- Create: `progrec_agent/tests/test_conversation_scripts.py`

- [ ] **Step 1: Write failing conversation regression tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class TestConversationScripts(unittest.TestCase):
    @patch("progrec_agent.tool_executor.ToolExecutor.execute")
    def test_recommendation_flow_mentions_recommendation_tool(self, mock_execute) -> None:
        from progrec_agent.agent_schema import ToolExecutionResult
        mock_execute.return_value = ToolExecutionResult(
            tool_name="recommend_full_pipeline",
            ok=True,
            payload={"summary": {"mentors": 5, "projects": 5, "teammates": 5}},
        )
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), llm_client=None)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("recommendations", reply.lower())

    def test_confirmation_decline_clears_pending_action(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.pending_confirmation_action = {
                "action_id": "a1",
                "tool_name": "rebuild_skill2_graph",
                "arguments": {},
                "prompt": "confirm?",
            }
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), llm_client=None)
            reply = core.handle_message(session, "no")
            self.assertIn("won't run", reply.lower())
            self.assertIsNone(session.pending_confirmation_action)
```

- [ ] **Step 2: Run the regression test and verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_conversation_scripts -v`  
Expected: FAIL because the executor does not yet implement `recommend_full_pipeline` and `AgentCore` does not handle declined confirmations.

- [ ] **Step 3: Add the real recommendation executor and decline handling**

Extend `progrec_agent/tool_executor.py`:

```python
def _tool_recommend_full_pipeline(self, arguments: dict[str, object], *, session) -> ToolExecutionResult:
    if session.student_profile and session.student_profile.get("student_id"):
        result = self.orchestrator.recommend_for_profile(dict(session.student_profile), top_k=5)
    else:
        student_id = str(arguments.get("student_id") or "")
        result = self.orchestrator.recommend_for_student_id(student_id, top_k=5)
    session.set_mode(result["mode"])
    session.set_student_profile(result["student_profile"])
    session.set_resource_context(result["resource_context"])
    session.set_results(
        skill3_result=result["skill3_result"],
        skill4_result=result["skill4_result"],
        skill5_result=result["skill5_result"],
        temporary_paths=result["temporary_paths"],
    )
    return ToolExecutionResult(tool_name="recommend_full_pipeline", ok=True, payload=result)
```

Extend `progrec_agent/agent_core.py`:

```python
if session.pending_confirmation_action and normalized in {"no", "n", "cancel"}:
    session.clear_pending_confirmation()
    return "Okay, I won't run that rebuild. If you want, I can inspect the current artifacts instead."
```

- [ ] **Step 4: Teach the response synthesizer to summarize recommendation results and update docs**

Update `progrec_agent/response_synthesizer.py`:

```python
if result.tool_name == "recommend_full_pipeline":
    skill5 = dict(result.payload.get("skill5_result") or {})
    recs = dict(skill5.get("recommendations") or {})
    return (
        "I ran the recommendation pipeline and generated recommendations. "
        f"Mentors: {len(list(recs.get('mentors') or []))}, "
        f"Projects: {len(list(recs.get('projects') or []))}, "
        f"Teammates: {len(list(recs.get('teammates') or []))}."
    )
```

Then update `README.md` so the agent section describes:

```markdown
- chat-first natural-language requests
- clarification when intent is ambiguous
- confirmation before graph/profile rebuild actions
- repository-local debugging and inspection help
```

- [ ] **Step 5: Run the regression suite, then commit**

Run: `python3 -m unittest discover -s progrec_agent/tests -v`  
Expected: PASS

```bash
git add progrec_agent/tool_executor.py progrec_agent/agent_core.py progrec_agent/response_synthesizer.py README.md progrec_agent/tests/test_conversation_scripts.py
git commit -m "feat: finish conversational agent recommendation flow"
```

## Self-Review

### Spec coverage

- Chat-first REPL: covered by Task 4 and Task 5
- Repository-local general agent scope: covered by Task 2, Task 3, and Task 6
- Unified tool metadata/execution: covered by Task 2
- Risk-based confirmation: covered by Task 3 and Task 6
- Multi-turn clarification and confirmation state: covered by Task 1 and Task 4
- Tests for routing, policy, execution flow, and conversation scripts: covered by every task, especially Task 3 through Task 6

### Placeholder scan

This plan intentionally avoids unresolved placeholder markers and "come back later" language. Each code step names concrete files, functions, and test commands.

### Type consistency

- `RouterDecision`, `PendingConfirmation`, and `ToolExecutionResult` are introduced in Task 1 and reused consistently afterward.
- Tool names are consistent across registry, router, executor, and tests:
  - `recommend_full_pipeline`
  - `show_current_profile`
  - `inspect_artifacts`
  - `debug_graph_mode`
  - `rebuild_skill2_graph`
  - `rebuild_skill1_profiles`
