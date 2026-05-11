# ProgRec LLM-First Chat Agent and Skill 3 Reasoning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `progrec_agent` into a pure chat, LLM-first ProgRec agent with explicit scope handling and session meta-question support, while upgrading Skill 3 to emit evidence-grounded LLM-written mentor explanations via a new `reason_text` field.

**Architecture:** Keep Skills 3 to 5 as the recommendation core and keep structured evidence deterministic, but move turn-by-turn interaction into a conversation agent that decides whether to answer, clarify, refuse, or execute internal tools. Skill 3 explanation generation becomes a two-layer flow: deterministic evidence extraction plus constrained LLM explanation text with deterministic fallback.

**Tech Stack:** Python 3, stdlib `unittest`, existing `progrec_agent` and `skill3_mentor_discovery` packages, existing `LLMClient`, OpenAI-compatible Responses or Chat Completions endpoints via stdlib `urllib`

---

## File Structure

### Modify

- `progrec_agent/agent_schema.py`
- `progrec_agent/session.py`
- `progrec_agent/prompts.py`
- `progrec_agent/intent_router.py`
- `progrec_agent/agent_core.py`
- `progrec_agent/repl.py`
- `progrec_agent/response_synthesizer.py`
- `progrec_agent/tool_executor.py`
- `progrec_agent/llm_client.py`
- `progrec_agent/tests/test_agent_core.py`
- `progrec_agent/tests/test_intent_router.py`
- `progrec_agent/tests/test_repl_agent_flow.py`
- `progrec_agent/tests/test_llm_client.py`
- `progrec_agent/tests/test_tool_executor.py`
- `README.md`
- `skill3_mentor_discovery/models.py`
- `skill3_mentor_discovery/explanations.py`
- `skill3_mentor_discovery/retrieval.py`
- `skill3_mentor_discovery/run_skill3.py`
- `progrec_agent/adapters/skill3_adapter.py`
- `tests/test_skill3_graph_features.py`

### Create

- `tests/test_skill3_explanations.py`

## Task 1: Expand Conversation State For Chat-First Turns

**Files:**
- Modify: `progrec_agent/agent_schema.py`
- Modify: `progrec_agent/session.py`
- Test: `progrec_agent/tests/test_agent_core.py`

- [ ] **Step 1: Write the failing state-tracking tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class _StubExecutor:
    def execute(self, tool_name: str, arguments: dict[str, object], *, session):
        from progrec_agent.agent_schema import ToolExecutionResult

        return ToolExecutionResult(tool_name=tool_name, ok=True, payload={"tool_name": tool_name})


class TestAgentCore(unittest.TestCase):
    def test_session_records_last_action_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=None)
            session.set_last_action(kind="answer_only", tool_name="", tool_arguments={}, result_summary="answered meta")
            self.assertEqual(session.last_action_kind, "answer_only")
            self.assertEqual(session.last_action_result_summary, "answered meta")

    def test_session_clears_last_action_on_reset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_last_action(kind="execute_tool", tool_name="recommend_full_pipeline", tool_arguments={}, result_summary="ran")
            session.reset()
            self.assertIsNone(session.last_action_kind)
            self.assertIsNone(session.last_tool_name)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: FAIL with `AttributeError` because `AgentSession` does not yet expose `set_last_action`, `last_action_kind`, `last_tool_name`, or `last_action_result_summary`.

- [ ] **Step 3: Add richer turn and action fields to `AgentSession`**

```python
from dataclasses import asdict, dataclass, field


@dataclass
class AgentSession:
    temp_dir: Path
    # existing fields unchanged
    last_action_kind: str | None = None
    last_tool_name: str | None = None
    last_tool_arguments: JsonDict | None = None
    last_action_result_summary: str | None = None

    def set_last_action(
        self,
        *,
        kind: str,
        tool_name: str,
        tool_arguments: dict[str, object],
        result_summary: str,
    ) -> None:
        self.last_action_kind = kind
        self.last_tool_name = tool_name or None
        self.last_tool_arguments = dict(tool_arguments)
        self.last_action_result_summary = result_summary
```

Also clear these fields in `reset()`:

```python
        self.last_action_kind = None
        self.last_tool_name = None
        self.last_tool_arguments = None
        self.last_action_result_summary = None
```

- [ ] **Step 4: Extend the routing schema for richer turn decisions**

```python
from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal[
    "recommend_mentor",
    "recommend_project",
    "recommend_teammate",
    "inspect_current_mentor",
    "explain_recommendation",
    "show_current_profile",
    "inspect_artifacts",
    "debug_graph_mode",
    "ask_last_action",
    "ask_capabilities",
    "out_of_scope_other",
]
MessageType = Literal["domain_task", "meta_question", "out_of_scope", "startup_help", "unsafe_or_blocked"]


@dataclass
class RouterDecision:
    message_type: MessageType
    intent: IntentName
    confidence: float
    candidate_tools: list[str]
    in_scope: bool = True
    needs_clarification: bool = False
    clarification_question: str = ""
    answer_only: bool = False
    tool_name: str = ""
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    meta_reply: str = ""
    reasoning_summary: str = ""
```

- [ ] **Step 5: Re-run the tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: PASS

```bash
git add progrec_agent/agent_schema.py progrec_agent/session.py progrec_agent/tests/test_agent_core.py
git commit -m "feat: track conversational turn state"
```

## Task 2: Make REPL Chat-First And Block Startup Without LLM

**Files:**
- Modify: `progrec_agent/repl.py`
- Modify: `progrec_agent/tests/test_repl_agent_flow.py`

- [ ] **Step 1: Write the failing REPL startup tests**

```python
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from progrec_agent import repl


class TestReplAgentFlow(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_main_raises_when_llm_is_not_configured(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "LLM"):
            repl.main()

    @patch.dict(
        os.environ,
        {"PROGREC_AGENT_API_KEY": "key", "PROGREC_AGENT_MODEL": "demo-model"},
        clear=True,
    )
    @patch("builtins.input", side_effect=["quit"])
    @patch("builtins.print")
    def test_main_prints_chat_first_intro(self, mock_print, _mock_input) -> None:
        with patch("progrec_agent.repl.AgentCore"):
            exit_code = repl.main()
        self.assertEqual(exit_code, 0)
        printed = "\n".join(" ".join(str(arg) for arg in call.args) for call in mock_print.call_args_list)
        self.assertIn("You can talk to me naturally", printed)
        self.assertNotIn("Commands:", printed)
```

- [ ] **Step 2: Run the focused REPL tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: FAIL because `main()` still prints the command menu and does not hard-stop when no LLM client is configured.

- [ ] **Step 3: Add a startup intro and hard LLM guard**

```python
CHAT_INTRO = """ProgRec Agent

I help you explore mentor, project, and teammate recommendations based on your academic interests and goals.

You can talk to me naturally. For example:
- Find me an NLP mentor.
- I'm interested in trustworthy AI and I only have 4 hours per week.
- Show me the current profile of the top mentor.
- Why did you recommend this mentor?
- Check whether my graph-mode artifacts are valid.

If your question is outside the recommendation workflow, I'll tell you clearly instead of guessing.
"""


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".progrec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    session = AgentSession(temp_dir=temp_dir)
    llm_client = _build_llm_client_from_env()
    if llm_client is None:
        raise RuntimeError(
            "LLM configuration is required for the conversational REPL. "
            "Set PROGREC_AGENT_API_KEY or OPENAI_API_KEY before starting it."
        )
    core = AgentCore(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client)
    print(CHAT_INTRO)
    while True:
        command = input("> ").strip()
        if command.lower() in {"exit", "quit"}:
            return 0
        if not command:
            continue
        print(core.handle_message(session, command))
```

- [ ] **Step 4: Remove command-first branches from the main loop**

Delete the direct `recommend`, `show mentor`, `show profile`, `show trace`, and `restart` branches from `main()`. Keep those capabilities reachable later through agent intents and internal tools.

- [ ] **Step 5: Re-run the REPL tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow -v`  
Expected: PASS

```bash
git add progrec_agent/repl.py progrec_agent/tests/test_repl_agent_flow.py
git commit -m "feat: make repl chat first and require llm"
```

## Task 3: Upgrade The Router To Handle Meta Questions, Out-Of-Scope Requests, And Minimal Clarification

**Files:**
- Modify: `progrec_agent/prompts.py`
- Modify: `progrec_agent/intent_router.py`
- Modify: `progrec_agent/tests/test_intent_router.py`

- [ ] **Step 1: Write failing router tests for the new conversation categories**

```python
from __future__ import annotations

import unittest
from unittest.mock import Mock

from progrec_agent.intent_router import route_user_message


class TestIntentRouter(unittest.TestCase):
    def test_llm_meta_question_routes_to_answer_only(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "message_type": "meta_question",
            "intent": "ask_last_action",
            "confidence": 0.96,
            "candidate_tools": [],
            "in_scope": True,
            "needs_clarification": False,
            "clarification_question": "",
            "answer_only": True,
            "tool_name": "",
            "tool_arguments": {},
            "meta_reply": "I only asked a clarification question in the last turn.",
            "reasoning_summary": "This is a session meta-question.",
        }
        decision = route_user_message("Which skill did you use just now?", llm_client=llm, session=None)
        self.assertEqual(decision.message_type, "meta_question")
        self.assertTrue(decision.answer_only)

    def test_llm_out_of_scope_routes_without_tool(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "message_type": "out_of_scope",
            "intent": "out_of_scope_other",
            "confidence": 0.99,
            "candidate_tools": [],
            "in_scope": False,
            "needs_clarification": False,
            "clarification_question": "",
            "answer_only": True,
            "tool_name": "",
            "tool_arguments": {},
            "meta_reply": "That question is outside ProgRec's recommendation scope.",
            "reasoning_summary": "The user asked about weather.",
        }
        decision = route_user_message("How is the weather today?", llm_client=llm, session=None)
        self.assertEqual(decision.message_type, "out_of_scope")
        self.assertFalse(decision.in_scope)
```

- [ ] **Step 2: Run the router tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_intent_router -v`  
Expected: FAIL because `RouterDecision` and `route_user_message()` do not yet support `message_type`, `answer_only`, `meta_reply`, or `tool_arguments`.

- [ ] **Step 3: Rewrite the router prompt to request turn decisions instead of shallow intent tags**

```python
ROUTER_PROMPT = """
You are the routing layer for ProgRec, a bounded recommendation agent.
Return strict JSON with:
- message_type
- intent
- confidence
- candidate_tools
- in_scope
- needs_clarification
- clarification_question
- answer_only
- tool_name
- tool_arguments
- meta_reply
- reasoning_summary

Rules:
- ProgRec is not a general-purpose chatbot.
- Out-of-scope questions must not be converted into recommendation tasks.
- Session meta-questions should be answered directly when possible.
- Ask at most one clarification question.
- Only propose tool execution when enough context exists.
""".strip()
```

- [ ] **Step 4: Update `route_user_message()` to parse the richer JSON shape**

```python
def route_user_message(user_text: str, *, llm_client, session) -> RouterDecision:
    payload = llm_client.complete_json(f"{ROUTER_PROMPT}\nUser message: {user_text}")
    decision = RouterDecision(
        message_type=str(payload.get("message_type", "unsafe_or_blocked")),
        intent=str(payload.get("intent", "out_of_scope_other")),
        confidence=float(payload.get("confidence", 0.0)),
        candidate_tools=[str(item) for item in payload.get("candidate_tools", [])],
        in_scope=bool(payload.get("in_scope", True)),
        needs_clarification=bool(payload.get("needs_clarification")),
        clarification_question=str(payload.get("clarification_question", "")),
        answer_only=bool(payload.get("answer_only", False)),
        tool_name=str(payload.get("tool_name", "")),
        tool_arguments=dict(payload.get("tool_arguments") or {}),
        meta_reply=str(payload.get("meta_reply", "")),
        reasoning_summary=str(payload.get("reasoning_summary", "")),
    )
    known_tools = [name for name in decision.candidate_tools if name in TOOLS]
    if decision.tool_name and decision.tool_name not in TOOLS:
        decision.tool_name = ""
    decision.candidate_tools = known_tools
    return decision
```

Keep a narrow local safeguard only for malformed payloads:

```python
except Exception:
    return RouterDecision(
        message_type="unsafe_or_blocked",
        intent="out_of_scope_other",
        confidence=0.0,
        candidate_tools=[],
        in_scope=False,
        answer_only=True,
        meta_reply="I hit a routing failure and couldn't safely classify that request.",
    )
```

- [ ] **Step 5: Re-run router tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_intent_router -v`  
Expected: PASS

```bash
git add progrec_agent/prompts.py progrec_agent/intent_router.py progrec_agent/tests/test_intent_router.py
git commit -m "feat: add llm first conversation routing"
```

## Task 4: Teach Agent Core And Response Synthesis To Answer, Clarify, Refuse, Or Execute

**Files:**
- Modify: `progrec_agent/agent_core.py`
- Modify: `progrec_agent/response_synthesizer.py`
- Modify: `progrec_agent/tests/test_agent_core.py`

- [ ] **Step 1: Write failing agent-core tests for meta and out-of-scope turns**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

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
    def test_meta_question_is_answered_without_tool_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            session.set_last_action(
                kind="clarify_then_wait",
                tool_name="",
                tool_arguments={},
                result_summary="asked whether to use student_id or build a profile",
            )
            llm = Mock()
            llm.complete_json.return_value = {
                "message_type": "meta_question",
                "intent": "ask_last_action",
                "confidence": 0.97,
                "candidate_tools": [],
                "in_scope": True,
                "needs_clarification": False,
                "clarification_question": "",
                "answer_only": True,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "",
                "reasoning_summary": "Session meta-question.",
            }
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm)
            reply = core.handle_message(session, "Which skill did you use just now?")
            self.assertIn("clarification question", reply)
            self.assertEqual(executor.calls, [])

    def test_out_of_scope_question_is_refused_without_tool_execution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            llm = Mock()
            llm.complete_json.return_value = {
                "message_type": "out_of_scope",
                "intent": "out_of_scope_other",
                "confidence": 0.99,
                "candidate_tools": [],
                "in_scope": False,
                "needs_clarification": False,
                "clarification_question": "",
                "answer_only": True,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "That question is outside ProgRec's recommendation scope.",
                "reasoning_summary": "Out of scope.",
            }
            executor = _StubExecutor()
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=executor, llm_client=llm)
            reply = core.handle_message(session, "What is the weather today?")
            self.assertIn("outside ProgRec", reply)
            self.assertEqual(executor.calls, [])
```

- [ ] **Step 2: Run the focused agent-core tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: FAIL because `handle_message()` still expects the old action model and does not synthesize direct meta answers from session state.

- [ ] **Step 3: Add direct-answer branches in `handle_message()`**

```python
        decision = self._route_with_fallback(session, user_text)
        session.set_last_router_decision(decision)

        if decision.answer_only:
            reply = synthesize_reply(session=session, user_text=user_text, decision=decision, result=None)
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="answer_only",
                tool_name="",
                tool_arguments={},
                result_summary=reply,
            )
            return reply

        if decision.needs_clarification and decision.clarification_question:
            session.set_pending_clarification([{"key": "followup", "question": decision.clarification_question}], user_text)
            reply = decision.clarification_question
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="clarify_then_wait",
                tool_name="",
                tool_arguments={},
                result_summary=reply,
            )
            return reply
```

- [ ] **Step 4: Teach the synthesizer to answer meta and refusal turns from session state**

```python
def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if decision is not None and decision.message_type == "meta_question":
        if decision.intent == "ask_last_action":
            if session.last_action_kind == "clarify_then_wait":
                return (
                    "In the last turn I did not run a recommendation skill. "
                    "I asked a clarification question: "
                    f"{session.last_action_result_summary}"
                )
            if session.last_tool_name:
                return f"In the last turn I used `{session.last_tool_name}`."
            return "I have not run a repository tool in this session yet."

    if decision is not None and decision.message_type == "out_of_scope":
        return (
            "That question is outside ProgRec's recommendation scope. "
            "I can still help with mentor, project, teammate, or graph-debug questions."
        )
```

Keep the existing tool-backed reply branches below these new direct-answer cases.

- [ ] **Step 5: Re-run tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core -v`  
Expected: PASS

```bash
git add progrec_agent/agent_core.py progrec_agent/response_synthesizer.py progrec_agent/tests/test_agent_core.py
git commit -m "feat: handle meta and scope turns in agent core"
```

## Task 5: Let Tool Execution Reuse Current Recommendation Results Through Natural Language

**Files:**
- Modify: `progrec_agent/tool_executor.py`
- Modify: `progrec_agent/tests/test_tool_executor.py`

- [ ] **Step 1: Write the failing mentor-inspection test for natural-language follow-up flows**

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from progrec_agent.session import AgentSession
from progrec_agent.tool_executor import ToolExecutor


class TestToolExecutor(unittest.TestCase):
    def test_show_recommended_mentor_profile_defaults_to_top_ranked_mentor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            mentors_path = td_path / "mentor_profiles_standard.json"
            mentors_path.write_text(
                json.dumps(
                    {
                        "mentors": [
                            {"mentor_id": "m_101", "name": "Dr. Ada", "department": "Computer Science"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            session = AgentSession(temp_dir=td_path)
            session.set_resource_context({"mentors_path": str(mentors_path)})
            session.skill5_result = {
                "recommendations": {"mentors": [{"mentor_id": "m_101", "mentor_name": "Dr. Ada", "rank": 1}]}
            }
            executor = ToolExecutor(repo_root=Path("."), temp_dir=td_path)
            result = executor.execute("show_recommended_mentor_profile", {}, session=session)
            self.assertTrue(result.ok)
            self.assertEqual(result.payload["mentor_profile"]["name"], "Dr. Ada")
```

- [ ] **Step 2: Run the tool-executor tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_tool_executor -v`  
Expected: FAIL if the current executor cannot support chat follow-up defaults or if prior edits have not wired that behavior consistently.

- [ ] **Step 3: Keep mentor/profile inspection as internal tools, not REPL commands**

Make sure `_tool_show_recommended_mentor_profile()` supports an empty `mentor_id` by defaulting to the current top mentor:

```python
        requested_mentor_id = str(arguments.get("mentor_id") or "").strip()
        mentor_recommendation = (
            next((item for item in mentors if str(item.get("mentor_id")) == requested_mentor_id), None)
            if requested_mentor_id
            else None
        )
        if mentor_recommendation is None:
            mentor_recommendation = dict(mentors[0])
```

Also keep `_tool_show_current_profile()` and `_tool_inspect_artifacts()` read-only so the agent can answer natural-language requests without reviving command-first code paths.

- [ ] **Step 4: Re-run the tests and commit**

Run: `python3 -m unittest progrec_agent.tests.test_tool_executor -v`  
Expected: PASS

```bash
git add progrec_agent/tool_executor.py progrec_agent/tests/test_tool_executor.py
git commit -m "feat: support natural language inspection tools"
```

## Task 6: Add Evidence-Preserving Skill 3 Reason Text Generation

**Files:**
- Modify: `skill3_mentor_discovery/models.py`
- Modify: `skill3_mentor_discovery/explanations.py`
- Modify: `skill3_mentor_discovery/retrieval.py`
- Create: `tests/test_skill3_explanations.py`

- [ ] **Step 1: Write the failing Skill 3 explanation tests**

```python
from __future__ import annotations

import unittest

from skill3_mentor_discovery.explanations import build_reason_evidence, fallback_reason_text
from skill3_mentor_discovery.models import MentorCandidate


class TestSkill3Explanations(unittest.TestCase):
    def test_reason_evidence_keeps_top_graph_inputs(self) -> None:
        mentor = {"mentor_id": "m_1", "name": "Dr. Ada"}
        evidence = build_reason_evidence(
            mentor=mentor,
            overlap_terms={"nlp", "summarization"},
            community_id="community_0",
            activity_score=0.6,
            meta_path_breakdown={"project_path_score": 0.4, "interest_path_score": 0.1},
            graph_confidence=0.8,
            top_evidence_paths=["student->project->mentor"],
            topic_score=0.7,
            graph_score=0.5,
            personalized_proximity=0.4,
            mentor_authority=0.3,
        )
        self.assertEqual(evidence["mentor_name"], "Dr. Ada")
        self.assertEqual(evidence["top_evidence_paths"], ["student->project->mentor"])
        self.assertEqual(evidence["graph_confidence"], 0.8)

    def test_mentor_candidate_includes_reason_text(self) -> None:
        candidate = MentorCandidate(mentor_id="m_1", mentor_name="Dr. Ada", topic_score=0.8, reason_text="Topic fit is strong.")
        payload = candidate.to_dict()
        self.assertEqual(payload["reason_text"], "Topic fit is strong.")
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `python3 -m unittest tests.test_skill3_explanations -v`  
Expected: FAIL because `build_reason_evidence`, `fallback_reason_text`, and `reason_text` do not exist yet.

- [ ] **Step 3: Extend `MentorCandidate` and build a deterministic evidence contract**

```python
from dataclasses import asdict, dataclass, field


@dataclass
class MentorCandidate:
    mentor_id: str
    topic_score: float
    graph_score: float = 0.0
    community_id: str = "community_unknown"
    final_score: float = 0.0
    mentor_name: str = ""
    activity_score: float = 0.0
    centrality_score: float = 0.0
    network_proximity: float = 0.0
    personalized_proximity: float = 0.0
    graph_confidence: float = 0.0
    mentor_authority: float = 0.0
    meta_path_breakdown: dict[str, float] = field(default_factory=dict)
    top_evidence_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    reason_text: str = ""
```

In `skill3_mentor_discovery/explanations.py` add:

```python
def build_reason_evidence(
    *,
    mentor: dict[str, object],
    overlap_terms: set[str],
    community_id: str,
    activity_score: float,
    meta_path_breakdown: dict[str, float] | None,
    graph_confidence: float,
    top_evidence_paths: list[str] | None,
    topic_score: float,
    graph_score: float,
    personalized_proximity: float,
    mentor_authority: float,
) -> dict[str, object]:
    return {
        "mentor_id": str(mentor.get("mentor_id", "")),
        "mentor_name": str(mentor.get("name", "")),
        "overlap_terms": sorted(overlap_terms),
        "community_id": community_id,
        "activity_score": activity_score,
        "meta_path_breakdown": dict(meta_path_breakdown or {}),
        "graph_confidence": graph_confidence,
        "top_evidence_paths": list(top_evidence_paths or [])[:3],
        "topic_score": topic_score,
        "graph_score": graph_score,
        "personalized_proximity": personalized_proximity,
        "mentor_authority": mentor_authority,
    }
```

- [ ] **Step 4: Add deterministic fallback text and wire it into retrieval**

```python
def fallback_reason_text(evidence: dict[str, object]) -> str:
    overlap_terms = list(evidence.get("overlap_terms") or [])
    graph_paths = list(evidence.get("top_evidence_paths") or [])
    graph_confidence = float(evidence.get("graph_confidence", 0.0))
    parts: list[str] = []
    if overlap_terms:
        parts.append("Topic fit is supported by " + ", ".join(overlap_terms[:3]) + ".")
    if graph_paths:
        parts.append(f"Representative graph path: {graph_paths[0]}.")
    if graph_confidence >= 0.7:
        parts.append("Graph evidence is comparatively strong.")
    elif graph_confidence > 0.0:
        parts.append("Graph evidence is present but should be read cautiously.")
    return " ".join(parts) if parts else "This mentor remains competitive based on overall topic relevance."
```

Then in `skill3_mentor_discovery/retrieval.py`:

```python
        reason_evidence = build_reason_evidence(
            mentor=mentor,
            overlap_terms=set(item["overlap_terms"]),
            community_id=str(graph_feature.get("community_id", "community_unknown")),
            activity_score=activity_score,
            meta_path_breakdown=dict(graph_feature.get("meta_path_breakdown") or {}),
            graph_confidence=graph_confidence,
            top_evidence_paths=list(graph_feature.get("top_evidence_paths") or []),
            topic_score=float(item["topic_score"]),
            graph_score=effective_graph_score,
            personalized_proximity=float(graph_feature.get("personalized_proximity", 0.0)),
            mentor_authority=float(graph_feature.get("mentor_authority", 0.0)),
        )
        fallback_text = fallback_reason_text(reason_evidence)
```

Set `reason_text=fallback_text` for now so the tests pass before LLM generation is added in the next task.

- [ ] **Step 5: Re-run the tests and commit**

Run: `python3 -m unittest tests.test_skill3_explanations tests.test_skill3_graph_features -v`  
Expected: PASS

```bash
git add skill3_mentor_discovery/models.py skill3_mentor_discovery/explanations.py skill3_mentor_discovery/retrieval.py tests/test_skill3_explanations.py tests/test_skill3_graph_features.py
git commit -m "feat: add skill3 reason evidence and fallback text"
```

## Task 7: Add Constrained LLM Reason Generation To Skill 3 With Deterministic Fallback

**Files:**
- Modify: `skill3_mentor_discovery/explanations.py`
- Modify: `skill3_mentor_discovery/run_skill3.py`
- Modify: `progrec_agent/adapters/skill3_adapter.py`
- Modify: `progrec_agent/tests/test_llm_client.py`
- Modify: `tests/test_skill3_explanations.py`

- [ ] **Step 1: Write the failing LLM reason-generation test**

```python
from __future__ import annotations

import unittest
from unittest.mock import Mock

from skill3_mentor_discovery.explanations import generate_reason_text


class TestSkill3Explanations(unittest.TestCase):
    def test_generate_reason_text_uses_llm_output(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {"reason_text": "This mentor fits because topic overlap and project-path evidence are both strong."}
        text = generate_reason_text(
            {
                "mentor_name": "Dr. Ada",
                "overlap_terms": ["nlp"],
                "graph_confidence": 0.8,
                "top_evidence_paths": ["student->project->mentor"],
                "meta_path_breakdown": {"project_path_score": 0.4},
            },
            llm_client=llm,
        )
        self.assertIn("project-path evidence", text)
```

- [ ] **Step 2: Run the explanation tests to verify they fail**

Run: `python3 -m unittest tests.test_skill3_explanations -v`  
Expected: FAIL because `generate_reason_text()` does not exist yet.

- [ ] **Step 3: Implement constrained reason generation with fallback**

```python
REASON_PROMPT = """
You write mentor recommendation explanations for ProgRec.
Return strict JSON with:
- reason_text

Rules:
- Use only the provided evidence.
- Do not invent projects, graph paths, or mentor traits.
- Mention the strongest one or two evidence families.
- If graph confidence is low, sound cautious.
- Keep the explanation to 2 or 3 sentences.
""".strip()


def generate_reason_text(evidence: dict[str, object], *, llm_client) -> str:
    if llm_client is None:
        return fallback_reason_text(evidence)
    try:
        payload = llm_client.complete_json(f"{REASON_PROMPT}\nEvidence: {evidence}")
    except Exception:
        return fallback_reason_text(evidence)
    text = str(payload.get("reason_text", "")).strip()
    return text or fallback_reason_text(evidence)
```

- [ ] **Step 4: Wire optional LLM explanation generation into Skill 3 entrypoints**

In `skill3_mentor_discovery/run_skill3.py` add:

```python
from progrec_agent.llm_client import LLMClient, LLMConfig


def _build_reason_llm_from_env() -> LLMClient | None:
    api_key = (os.getenv("PROGREC_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    model = (os.getenv("PROGREC_AGENT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    endpoint = (os.getenv("PROGREC_AGENT_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1/responses").strip()
    return LLMClient(LLMConfig(model=model, api_key=api_key, endpoint=endpoint))
```

Then pass the client into retrieval:

```python
    reason_llm = _build_reason_llm_from_env()
    mentor_candidates = rank_mentors_for_student(
        student,
        resources.mentors,
        graph=resources.graph,
        top_k=args.top_k,
        llm_client=reason_llm,
    )
```

Update `progrec_agent/adapters/skill3_adapter.py` to keep in-process Skill 3 calls compatible by passing `llm_client=None` until a higher-level wiring task opts in.

- [ ] **Step 5: Re-run tests and commit**

Run: `python3 -m unittest tests.test_skill3_explanations progrec_agent.tests.test_llm_client -v`  
Expected: PASS

```bash
git add skill3_mentor_discovery/explanations.py skill3_mentor_discovery/run_skill3.py progrec_agent/adapters/skill3_adapter.py progrec_agent/tests/test_llm_client.py tests/test_skill3_explanations.py
git commit -m "feat: add llm grounded skill3 reason text"
```

## Task 8: Validate End-To-End Chat Behavior And Document The New UX

**Files:**
- Modify: `README.md`
- Modify: `progrec_agent/tests/test_repl_agent_flow.py`
- Modify: `progrec_agent/tests/test_agent_core.py`

- [ ] **Step 1: Write the failing conversation regression tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core import AgentCore
from progrec_agent.session import AgentSession


class _StubExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def execute(self, tool_name: str, arguments: dict[str, object], *, session):
        self.calls.append((tool_name, arguments))
        from progrec_agent.agent_schema import ToolExecutionResult

        return ToolExecutionResult(tool_name=tool_name, ok=True, payload={"tool_name": tool_name, "skill5_result": {"recommendations": {"mentors": []}}})


class TestAgentConversationRegression(unittest.TestCase):
    def test_recommendation_without_context_asks_one_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            session = AgentSession(temp_dir=Path(td))
            llm = Mock()
            llm.complete_json.return_value = {
                "message_type": "domain_task",
                "intent": "recommend_mentor",
                "confidence": 0.94,
                "candidate_tools": [],
                "in_scope": True,
                "needs_clarification": True,
                "clarification_question": "Do you want to use an existing student_id, or should I build a short profile from your interests?",
                "answer_only": False,
                "tool_name": "",
                "tool_arguments": {},
                "meta_reply": "",
                "reasoning_summary": "Need student context first.",
            }
            core = AgentCore(repo_root=Path("."), temp_dir=Path(td), executor=_StubExecutor(), llm_client=llm)
            reply = core.handle_message(session, "Find me an NLP mentor")
            self.assertIn("student_id", reply)
            self.assertEqual(len(session.pending_clarification_questions), 1)
```

- [ ] **Step 2: Run the conversation tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core progrec_agent.tests.test_repl_agent_flow -v`  
Expected: FAIL until the earlier routing, REPL, and response behavior all line up consistently.

- [ ] **Step 3: Update the README to document the chat-first workflow**

Replace the command-centric REPL section with:

```markdown
## ProgRec Conversational Agent CLI

Run the chat-first agent from the repository root:

```bash
export PROGREC_AGENT_API_KEY=your_key_here
export PROGREC_AGENT_MODEL=gpt-4.1-mini
python3 -m progrec_agent.repl
```

The REPL now expects natural-language input. Example prompts:

- `Find me an NLP mentor.`
- `I'm interested in trustworthy AI and only have 4 hours per week.`
- `Show me the current profile of the top mentor.`
- `Why did you recommend this mentor?`
- `Check whether my graph-mode artifacts are valid.`

If you ask a question outside the recommendation workflow, the agent will say so clearly instead of guessing.
```

- [ ] **Step 4: Run the relevant tests plus the full agent suite and commit**

Run: `python3 -m unittest discover -s progrec_agent/tests -v`  
Expected: PASS

Run: `python3 -m unittest tests.test_skill3_explanations tests.test_skill3_graph_features -v`  
Expected: PASS

```bash
git add README.md progrec_agent/tests/test_agent_core.py progrec_agent/tests/test_repl_agent_flow.py
git commit -m "docs: document chat first agent workflow"
```
