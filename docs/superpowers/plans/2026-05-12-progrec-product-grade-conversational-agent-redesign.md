# ProgRec Product-Grade Conversational Agent Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `progrec_agent/` chat layer into a stateful, clarification-first conversational agent that understands natural language reliably, asks for missing required information before execution, and handles follow-up requests through stable session context.

**Architecture:** Introduce a V2 agent pipeline that separates semantic parsing, dialog state, clarification policy, planning, runtime integration, and response rendering. Keep the existing Skills 3-5 recommendation core intact, run the new chat stack behind `PROGREC_AGENT_V2=1`, and migrate the REPL only after semantic, state, policy, and end-to-end tests are green.

**Tech Stack:** Python 3, stdlib `unittest`, existing `progrec_agent/` package, OpenAI-compatible JSON LLM client, JSON fixtures, environment-flagged runtime switching.

---

## File Structure

### New files

- `progrec_agent/nlu/schema.py`
  Defines typed semantic-frame dataclasses and allowed enums for intents, field provenance, and target types.
- `progrec_agent/nlu/parser.py`
  Builds semantic-parse prompts, calls `LLMClient`, validates JSON, and returns `IntentFrame`.
- `progrec_agent/nlu/validators.py`
  Validates model output and converts invalid parses into safe fallback parse results.
- `progrec_agent/dialog/state.py`
  Defines `DialogState`, `PendingQuestion`, `ExecutionContext`, and helper constructors.
- `progrec_agent/dialog/slots.py`
  Defines task-specific slot requirements and low-risk defaults.
- `progrec_agent/dialog/merge.py`
  Merges `IntentFrame` updates into `DialogState`, preserving explicit values and tracking conflicts.
- `progrec_agent/dialog/answer_parser.py`
  Resolves pending-question answers into slot updates before general routing.
- `progrec_agent/policy/clarification.py`
  Picks the next clarification question from missing or conflicting slots.
- `progrec_agent/policy/readiness.py`
  Computes required slots, missing slots, and execution readiness from current state.
- `progrec_agent/planning/actions.py`
  Declares V2 planner action names and action payload schemas.
- `progrec_agent/planning/planner_v2.py`
  Maps resolved dialog state into deterministic execution plans.
- `progrec_agent/runtime/recommendation_runtime.py`
  Wraps recommendation execution for existing-student and temporary-profile flows.
- `progrec_agent/runtime/inspection_runtime.py`
  Wraps session-result entity lookup such as top mentor or ranked project retrieval.
- `progrec_agent/runtime/validation_runtime.py`
  Wraps graph-mode and artifact validation actions.
- `progrec_agent/response/replies.py`
  Renders clarification prompts, execution blockers, summaries, and follow-up responses.
- `progrec_agent/agent_core_v2.py`
  Orchestrates the V2 end-to-end flow.
- `progrec_agent/tests/test_nlu_schema.py`
- `progrec_agent/tests/test_nlu_parser.py`
- `progrec_agent/tests/test_dialog_state.py`
- `progrec_agent/tests/test_dialog_answer_parser.py`
- `progrec_agent/tests/test_clarification_policy.py`
- `progrec_agent/tests/test_planner_v2.py`
- `progrec_agent/tests/test_agent_core_v2.py`
- `progrec_agent/tests/test_conversation_e2e_v2.py`
- `progrec_agent/tests/fixtures/conversations/existing_graph_recommendation.json`
- `progrec_agent/tests/fixtures/conversations/temporary_profile_recommendation.json`
- `progrec_agent/tests/fixtures/conversations/followup_top_mentor.json`
- `progrec_agent/tests/fixtures/conversations/ambiguous_show_profile.json`
- `progrec_agent/tests/fixtures/conversations/conflicting_profile_source.json`

### Modified files

- `progrec_agent/repl.py`
  Switches to V2 when `PROGREC_AGENT_V2=1` is set.
- `progrec_agent/llm_client.py`
  Reused as-is for semantic parsing unless a small helper method is needed for better error labeling.
- `progrec_agent/tool_executor.py`
  Keeps V1 tools stable, but exposes runtime-friendly helpers if needed.
- `README.md`
  Documents the V2 feature flag, recommended test command, and clarification-first behavior.

### Files intentionally left stable

- `progrec_agent/orchestrator.py`
- `progrec_agent/run_agent.py`
- `skill3_mentor_discovery/`
- `skill4_handoff/`
- `skill5_student-recommendation-ranker/`

These should only receive changes if the runtime wrapper reveals a real integration gap.

---

### Task 1: Create Shared V2 Schemas

**Files:**
- Create: `progrec_agent/nlu/schema.py`
- Create: `progrec_agent/dialog/state.py`
- Create: `progrec_agent/dialog/slots.py`
- Test: `progrec_agent/tests/test_nlu_schema.py`
- Test: `progrec_agent/tests/test_dialog_state.py`

- [ ] **Step 1: Write the failing schema tests**

```python
import unittest

from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.schema import IntentFrame, SlotValue


class TestNLUSchema(unittest.TestCase):
    def test_intent_frame_defaults_to_empty_safe_collections(self) -> None:
        frame = IntentFrame(intent="recommendation_request")
        self.assertEqual(frame.target_types, [])
        self.assertEqual(frame.entities, {})
        self.assertEqual(frame.uncertain_fields, [])

    def test_slot_value_tracks_provenance(self) -> None:
        slot = SlotValue(value="graph", provenance="explicit")
        self.assertEqual(slot.value, "graph")
        self.assertEqual(slot.provenance, "explicit")


class TestDialogState(unittest.TestCase):
    def test_new_state_has_no_pending_question(self) -> None:
        state = DialogState()
        self.assertIsNone(state.pending_question)
        self.assertEqual(state.resolved_slots, {})

    def test_pending_question_carries_slot_binding(self) -> None:
        question = PendingQuestion(
            slot_name="profile_source",
            question="Should I use an existing student profile or build a temporary profile?",
            expected_answer_shape="existing_profile|temporary_profile",
        )
        self.assertEqual(question.slot_name, "profile_source")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_nlu_schema progrec_agent.tests.test_dialog_state -v`

Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.nlu` or `progrec_agent.dialog`.

- [ ] **Step 3: Write the minimal shared schema implementation**

```python
# progrec_agent/nlu/schema.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal[
    "recommendation_request",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
    "out_of_scope",
]
Provenance = Literal["explicit", "inferred", "unknown"]


@dataclass
class SlotValue:
    value: Any
    provenance: Provenance


@dataclass
class IntentFrame:
    intent: IntentName
    target_types: list[str] = field(default_factory=list)
    entities: dict[str, SlotValue] = field(default_factory=dict)
    constraints: dict[str, SlotValue] = field(default_factory=dict)
    preferences: dict[str, SlotValue] = field(default_factory=dict)
    references: dict[str, SlotValue] = field(default_factory=dict)
    confidence: float = 0.0
    uncertain_fields: list[str] = field(default_factory=list)
    possible_conflicts: list[str] = field(default_factory=list)
```

```python
# progrec_agent/dialog/state.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PendingQuestion:
    slot_name: str
    question: str
    expected_answer_shape: str


@dataclass
class ExecutionContext:
    result_handle: str | None = None
    selected_entity_type: str | None = None
    selected_entity_id: str | None = None


@dataclass
class DialogState:
    task: str = ""
    goal: str = ""
    resolved_slots: dict[str, object] = field(default_factory=dict)
    candidate_slots: dict[str, object] = field(default_factory=dict)
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)
    pending_question: PendingQuestion | None = None
    conflicts: list[str] = field(default_factory=list)
    execution_context: ExecutionContext = field(default_factory=ExecutionContext)
    clarification_turn_count: int = 0
```

```python
# progrec_agent/dialog/slots.py
from __future__ import annotations

TASK_REQUIRED_SLOTS = {
    "recommend_existing_student": ["student_id", "mode"],
    "recommend_temporary_profile": ["research_topic", "program_type", "experience_level"],
    "inspect_recommendation": [],
    "validate_resources": ["mode"],
}

LOW_RISK_DEFAULTS = {
    "target_types": ["mentor"],
    "top_k": 5,
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_nlu_schema progrec_agent.tests.test_dialog_state -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/nlu/schema.py progrec_agent/dialog/state.py progrec_agent/dialog/slots.py progrec_agent/tests/test_nlu_schema.py progrec_agent/tests/test_dialog_state.py
git commit -m "feat: add v2 dialog and semantic schema"
```

### Task 2: Build Semantic Parse Validation and Parsing

**Files:**
- Create: `progrec_agent/nlu/validators.py`
- Create: `progrec_agent/nlu/parser.py`
- Modify: `progrec_agent/llm_client.py`
- Test: `progrec_agent/tests/test_nlu_parser.py`

- [ ] **Step 1: Write the failing parser tests**

```python
import unittest
from unittest.mock import Mock

from progrec_agent.nlu.parser import parse_user_message


class TestNLUParser(unittest.TestCase):
    def test_parse_extracts_student_id_and_mode(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "intent": "recommendation_request",
            "target_types": ["mentor", "project", "teammate"],
            "entities": {
                "student_id": {"value": "jamie-taylor-00008", "provenance": "explicit"},
                "mode": {"value": "graph", "provenance": "explicit"},
            },
            "constraints": {},
            "preferences": {},
            "references": {},
            "confidence": 0.95,
            "uncertain_fields": [],
            "possible_conflicts": [],
        }
        frame = parse_user_message(
            "Recommend mentors for student_id jamie-taylor-00008 in graph mode.",
            dialog_state=None,
            llm_client=llm,
        )
        self.assertEqual(frame.entities["student_id"].value, "jamie-taylor-00008")
        self.assertEqual(frame.entities["mode"].value, "graph")

    def test_invalid_mode_becomes_safe_out_of_scope_frame(self) -> None:
        llm = Mock()
        llm.complete_json.return_value = {
            "intent": "recommendation_request",
            "target_types": ["mentor"],
            "entities": {"mode": {"value": "production", "provenance": "explicit"}},
            "constraints": {},
            "preferences": {},
            "references": {},
            "confidence": 0.6,
            "uncertain_fields": [],
            "possible_conflicts": [],
        }
        frame = parse_user_message("use production mode", dialog_state=None, llm_client=llm)
        self.assertEqual(frame.intent, "out_of_scope")
        self.assertIn("mode", frame.uncertain_fields)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_nlu_parser -v`

Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.nlu.parser`.

- [ ] **Step 3: Implement parser and validator**

```python
# progrec_agent/nlu/validators.py
from __future__ import annotations

from progrec_agent.nlu.schema import IntentFrame, SlotValue

ALLOWED_INTENTS = {
    "recommendation_request",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
    "out_of_scope",
}
ALLOWED_MODES = {"demo", "graph"}


def build_safe_fallback_frame(reason: str, *, uncertain_fields: list[str] | None = None) -> IntentFrame:
    return IntentFrame(
        intent="out_of_scope",
        confidence=0.0,
        uncertain_fields=list(uncertain_fields or []),
        possible_conflicts=[reason],
    )


def validate_parse_payload(payload: dict[str, object]) -> IntentFrame:
    intent = str(payload.get("intent") or "")
    if intent not in ALLOWED_INTENTS:
        return build_safe_fallback_frame("invalid_intent")
    entities = {}
    for key, item in dict(payload.get("entities") or {}).items():
        row = dict(item or {})
        entities[str(key)] = SlotValue(value=row.get("value"), provenance=str(row.get("provenance") or "unknown"))
    mode = entities.get("mode")
    if mode is not None and str(mode.value) not in ALLOWED_MODES:
        return build_safe_fallback_frame("invalid_mode", uncertain_fields=["mode"])
    return IntentFrame(
        intent=intent,
        target_types=[str(x) for x in list(payload.get("target_types") or [])],
        entities=entities,
        constraints={},
        preferences={},
        references={},
        confidence=float(payload.get("confidence", 0.0)),
        uncertain_fields=[str(x) for x in list(payload.get("uncertain_fields") or [])],
        possible_conflicts=[str(x) for x in list(payload.get("possible_conflicts") or [])],
    )
```

```python
# progrec_agent/nlu/parser.py
from __future__ import annotations

from progrec_agent.nlu.validators import build_safe_fallback_frame, validate_parse_payload

SEMANTIC_PARSE_PROMPT = """
Return strict JSON describing the user's request.
Do not choose tools.
Do not ask clarification questions.
Do not invent facts.
""".strip()


def parse_user_message(user_text: str, *, dialog_state, llm_client):
    if llm_client is None:
        return build_safe_fallback_frame("missing_llm")
    payload = llm_client.complete_json(
        f"{SEMANTIC_PARSE_PROMPT}\nDialog state: {dialog_state}\nUser message: {user_text}"
    )
    return validate_parse_payload(dict(payload))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_nlu_parser -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/nlu/validators.py progrec_agent/nlu/parser.py progrec_agent/tests/test_nlu_parser.py
git commit -m "feat: add v2 semantic parser and validators"
```

### Task 3: Implement Dialog Merge and Pending-Answer Parsing

**Files:**
- Create: `progrec_agent/dialog/merge.py`
- Create: `progrec_agent/dialog/answer_parser.py`
- Test: `progrec_agent/tests/test_dialog_answer_parser.py`
- Test: `progrec_agent/tests/test_dialog_state.py`

- [ ] **Step 1: Write the failing dialog-state evolution tests**

```python
import unittest

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.schema import IntentFrame, SlotValue
from progrec_agent.dialog.merge import merge_intent_frame


class TestDialogMerge(unittest.TestCase):
    def test_merge_promotes_explicit_entities_to_resolved_slots(self) -> None:
        state = DialogState()
        frame = IntentFrame(
            intent="recommendation_request",
            entities={"student_id": SlotValue(value="jamie-taylor-00008", provenance="explicit")},
        )
        merged = merge_intent_frame(state, frame)
        self.assertEqual(merged.resolved_slots["student_id"], "jamie-taylor-00008")

    def test_apply_pending_answer_updates_bound_slot(self) -> None:
        state = DialogState(
            pending_question=PendingQuestion(
                slot_name="mode",
                question="Use demo or graph mode?",
                expected_answer_shape="demo|graph",
            )
        )
        updated = apply_pending_answer(state, "graph")
        self.assertEqual(updated.resolved_slots["mode"], "graph")
        self.assertIsNone(updated.pending_question)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_dialog_state progrec_agent.tests.test_dialog_answer_parser -v`

Expected: FAIL with missing modules or missing functions `merge_intent_frame` and `apply_pending_answer`.

- [ ] **Step 3: Implement merge and answer parsing**

```python
# progrec_agent/dialog/merge.py
from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.state import DialogState


def merge_intent_frame(state: DialogState, frame) -> DialogState:
    updated = deepcopy(state)
    updated.task = updated.task or frame.intent
    for key, slot in frame.entities.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    for key, slot in frame.constraints.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    return updated
```

```python
# progrec_agent/dialog/answer_parser.py
from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.state import DialogState

ANSWER_MAP = {
    "use my description": {"profile_source": "temporary_profile"},
    "temporary": {"profile_source": "temporary_profile"},
    "existing": {"profile_source": "existing_profile"},
    "graph": {"mode": "graph"},
    "demo": {"mode": "demo"},
}


def apply_pending_answer(state: DialogState, user_text: str) -> DialogState:
    updated = deepcopy(state)
    pending = updated.pending_question
    if pending is None:
        return updated
    normalized = user_text.strip().lower()
    if normalized in ANSWER_MAP and pending.slot_name in ANSWER_MAP[normalized]:
        updated.resolved_slots[pending.slot_name] = ANSWER_MAP[normalized][pending.slot_name]
    else:
        updated.resolved_slots[pending.slot_name] = user_text.strip()
    updated.pending_question = None
    return updated
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_dialog_state progrec_agent.tests.test_dialog_answer_parser -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/dialog/merge.py progrec_agent/dialog/answer_parser.py progrec_agent/tests/test_dialog_state.py progrec_agent/tests/test_dialog_answer_parser.py
git commit -m "feat: add v2 dialog merge and answer parsing"
```

### Task 4: Add Readiness Computation and Clarification Policy

**Files:**
- Create: `progrec_agent/policy/readiness.py`
- Create: `progrec_agent/policy/clarification.py`
- Test: `progrec_agent/tests/test_clarification_policy.py`

- [ ] **Step 1: Write the failing clarification-policy tests**

```python
import unittest

from progrec_agent.dialog.state import DialogState
from progrec_agent.policy.clarification import choose_next_question
from progrec_agent.policy.readiness import compute_readiness


class TestClarificationPolicy(unittest.TestCase):
    def test_existing_student_request_needs_student_id_before_mode(self) -> None:
        state = DialogState(task="recommend_existing_student", resolved_slots={})
        state = compute_readiness(state)
        question = choose_next_question(state)
        self.assertEqual(question.slot_name, "student_id")

    def test_missing_mode_is_asked_after_student_id(self) -> None:
        state = DialogState(task="recommend_existing_student", resolved_slots={"student_id": "jamie-taylor-00008"})
        state = compute_readiness(state)
        question = choose_next_question(state)
        self.assertEqual(question.slot_name, "mode")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_clarification_policy -v`

Expected: FAIL with `ModuleNotFoundError` or missing functions.

- [ ] **Step 3: Implement readiness and clarification policy**

```python
# progrec_agent/policy/readiness.py
from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.slots import TASK_REQUIRED_SLOTS


def compute_readiness(state):
    updated = deepcopy(state)
    required = TASK_REQUIRED_SLOTS.get(updated.task, [])
    updated.required_slots = list(required)
    updated.missing_slots = [slot for slot in required if slot not in updated.resolved_slots]
    return updated
```

```python
# progrec_agent/policy/clarification.py
from __future__ import annotations

from progrec_agent.dialog.state import PendingQuestion

QUESTION_BANK = {
    "profile_source": "Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
    "student_id": "Which student_id from the dataset should I use?",
    "mode": "Should I use demo mode or graph mode?",
    "research_topic": "What research topic should I use for the temporary profile?",
    "program_type": "What kind of program are you targeting, such as undergraduate research or summer research?",
    "experience_level": "What is your current experience level in this topic?",
}


def choose_next_question(state):
    if state.conflicts:
        return PendingQuestion(
            slot_name="conflict_resolution",
            question="Your last two instructions conflict. Which one should I follow?",
            expected_answer_shape="free_text",
        )
    for slot_name in state.missing_slots:
        return PendingQuestion(
            slot_name=slot_name,
            question=QUESTION_BANK[slot_name],
            expected_answer_shape="free_text",
        )
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_clarification_policy -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/policy/readiness.py progrec_agent/policy/clarification.py progrec_agent/tests/test_clarification_policy.py
git commit -m "feat: add v2 readiness and clarification policy"
```

### Task 5: Implement V2 Planner and Runtime Wrappers

**Files:**
- Create: `progrec_agent/planning/actions.py`
- Create: `progrec_agent/planning/planner_v2.py`
- Create: `progrec_agent/runtime/recommendation_runtime.py`
- Create: `progrec_agent/runtime/inspection_runtime.py`
- Create: `progrec_agent/runtime/validation_runtime.py`
- Test: `progrec_agent/tests/test_planner_v2.py`

- [ ] **Step 1: Write the failing planner tests**

```python
import unittest

from progrec_agent.dialog.state import DialogState, ExecutionContext
from progrec_agent.planning.planner_v2 import build_execution_plan


class TestPlannerV2(unittest.TestCase):
    def test_existing_student_plan_uses_student_runtime(self) -> None:
        state = DialogState(
            task="recommend_existing_student",
            resolved_slots={"student_id": "jamie-taylor-00008", "mode": "graph"},
            missing_slots=[],
        )
        plan = build_execution_plan(state)
        self.assertEqual(plan.action, "run_existing_profile_recommendation")

    def test_top_mentor_followup_uses_inspection_runtime(self) -> None:
        state = DialogState(
            task="inspect_recommendation",
            execution_context=ExecutionContext(result_handle="result-1"),
            resolved_slots={"entity_type": "mentor", "rank": 1},
            missing_slots=[],
        )
        plan = build_execution_plan(state)
        self.assertEqual(plan.action, "inspect_ranked_entity")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_planner_v2 -v`

Expected: FAIL with missing planner modules.

- [ ] **Step 3: Implement planner and runtime wrappers**

```python
# progrec_agent/planning/actions.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExecutionPlanV2:
    action: str
    arguments: dict[str, object] = field(default_factory=dict)
```

```python
# progrec_agent/planning/planner_v2.py
from __future__ import annotations

from progrec_agent.planning.actions import ExecutionPlanV2


def build_execution_plan(state) -> ExecutionPlanV2:
    if state.missing_slots:
        return ExecutionPlanV2(action="await_clarification")
    if state.task == "recommend_existing_student":
        return ExecutionPlanV2(
            action="run_existing_profile_recommendation",
            arguments={
                "student_id": state.resolved_slots["student_id"],
                "mode": state.resolved_slots["mode"],
                "top_k": state.resolved_slots.get("top_k", 5),
            },
        )
    if state.task == "recommend_temporary_profile":
        return ExecutionPlanV2(
            action="run_temporary_profile_recommendation",
            arguments={"profile": dict(state.resolved_slots), "top_k": state.resolved_slots.get("top_k", 5)},
        )
    if state.task == "inspect_recommendation":
        return ExecutionPlanV2(
            action="inspect_ranked_entity",
            arguments={
                "result_handle": state.execution_context.result_handle,
                "entity_type": state.resolved_slots.get("entity_type", "mentor"),
                "rank": state.resolved_slots.get("rank", 1),
            },
        )
    if state.task == "validate_resources":
        return ExecutionPlanV2(action="validate_resources", arguments={"mode": state.resolved_slots["mode"]})
    return ExecutionPlanV2(action="unsupported")
```

```python
# progrec_agent/runtime/recommendation_runtime.py
from __future__ import annotations

from progrec_agent.config import resolve_resource_config
from progrec_agent.orchestrator import ProgRecOrchestrator


def run_recommendation_for_student_id(*, repo_root, temp_dir, student_id: str, mode: str, top_k: int):
    bundle = resolve_resource_config(mode, repo_root, validate_graph=True)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.recommend_for_student_id(student_id, top_k=top_k, bundle=bundle)
```

```python
# progrec_agent/runtime/inspection_runtime.py
from __future__ import annotations


def get_ranked_entity(*, skill5_result: dict[str, object], entity_type: str, rank: int):
    rows = list((skill5_result.get("recommendations") or {}).get(f"{entity_type}s") or [])
    for row in rows:
        if int(row.get("rank", 0)) == rank:
            return dict(row)
    return {}
```

```python
# progrec_agent/runtime/validation_runtime.py
from __future__ import annotations

from progrec_agent.config import resolve_resource_config


def validate_resources(*, repo_root, mode: str):
    bundle = resolve_resource_config(mode, repo_root, validate_graph=(mode == "graph"))
    return {
        "mode": mode,
        "students_path": str(bundle.skill2_students),
        "mentors_path": str(bundle.skill2_mentors),
        "graph_path": str(bundle.skill2_graph) if bundle.skill2_graph else "",
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_planner_v2 -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/planning/actions.py progrec_agent/planning/planner_v2.py progrec_agent/runtime/recommendation_runtime.py progrec_agent/runtime/inspection_runtime.py progrec_agent/runtime/validation_runtime.py progrec_agent/tests/test_planner_v2.py
git commit -m "feat: add v2 planner and runtime wrappers"
```

### Task 6: Orchestrate V2 Agent Flow

**Files:**
- Create: `progrec_agent/response/replies.py`
- Create: `progrec_agent/agent_core_v2.py`
- Test: `progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Write the failing V2 orchestration tests**

```python
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestAgentCoreV2(unittest.TestCase):
    def test_missing_required_slot_returns_clarification_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())
            reply, state = core.handle_message(DialogState(), "Find me a mentor.")
            self.assertIn("existing student profile", reply)
            self.assertIsNotNone(state.pending_question)

    def test_followup_answer_updates_state_instead_of_restarting_task(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())
            state = DialogState(
                task="recommend_existing_student",
                pending_question=core._make_pending_question("mode"),
            )
            reply, updated = core.handle_message(state, "graph")
            self.assertIn("student_id", reply)
            self.assertEqual(updated.resolved_slots["mode"], "graph")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core_v2 -v`

Expected: FAIL with missing module `progrec_agent.agent_core_v2`.

- [ ] **Step 3: Implement V2 orchestration and reply rendering**

```python
# progrec_agent/response/replies.py
from __future__ import annotations


def render_clarification(question) -> str:
    return question.question


def render_execution_blocker(state) -> str:
    return f"I still need {', '.join(state.missing_slots)} before I can run this request."


def render_recommendation_summary(result: dict[str, object]) -> str:
    recs = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    return (
        "I ran the recommendation pipeline and generated recommendations. "
        f"Mentors: {len(list(recs.get('mentors') or []))}, "
        f"Projects: {len(list(recs.get('projects') or []))}, "
        f"Teammates: {len(list(recs.get('teammates') or []))}."
    )
```

```python
# progrec_agent/agent_core_v2.py
from __future__ import annotations

from progrec_agent.dialog.answer_parser import apply_pending_answer
from progrec_agent.dialog.merge import merge_intent_frame
from progrec_agent.dialog.state import DialogState, PendingQuestion
from progrec_agent.nlu.parser import parse_user_message
from progrec_agent.planning.planner_v2 import build_execution_plan
from progrec_agent.policy.clarification import choose_next_question
from progrec_agent.policy.readiness import compute_readiness
from progrec_agent.response.replies import render_clarification, render_execution_blocker


class AgentCoreV2:
    def __init__(self, *, repo_root, temp_dir, llm_client, recommendation_runtime=None, inspection_runtime=None, validation_runtime=None):
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.llm_client = llm_client
        self.recommendation_runtime = recommendation_runtime
        self.inspection_runtime = inspection_runtime
        self.validation_runtime = validation_runtime

    def _make_pending_question(self, slot_name: str) -> PendingQuestion:
        from progrec_agent.policy.clarification import QUESTION_BANK

        return PendingQuestion(slot_name=slot_name, question=QUESTION_BANK[slot_name], expected_answer_shape="free_text")

    def handle_message(self, state: DialogState, user_text: str):
        working = state
        if working.pending_question is not None:
            working = apply_pending_answer(working, user_text)
        else:
            frame = parse_user_message(user_text, dialog_state=working, llm_client=self.llm_client)
            working = merge_intent_frame(working, frame)
            if "student_id" in working.resolved_slots:
                working.task = "recommend_existing_student"
            elif any(k in working.resolved_slots for k in ["research_topic", "program_type", "experience_level"]):
                working.task = "recommend_temporary_profile"
        if not working.task:
            working.task = "recommend_temporary_profile"
        working = compute_readiness(working)
        next_question = choose_next_question(working)
        if next_question is not None:
            working.pending_question = next_question
            return render_clarification(next_question), working
        plan = build_execution_plan(working)
        return render_execution_blocker(working if plan.action == "await_clarification" else working), working
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_agent_core_v2 -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/response/replies.py progrec_agent/agent_core_v2.py progrec_agent/tests/test_agent_core_v2.py
git commit -m "feat: add v2 agent orchestration flow"
```

### Task 7: Connect V2 to Real Runtime and REPL Feature Flag

**Files:**
- Modify: `progrec_agent/agent_core_v2.py`
- Modify: `progrec_agent/repl.py`
- Test: `progrec_agent/tests/test_repl_agent_flow.py`
- Test: `progrec_agent/tests/test_conversation_e2e_v2.py`

- [ ] **Step 1: Write the failing feature-flag and runtime integration tests**

```python
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState


class TestConversationE2EV2(unittest.TestCase):
    def test_existing_student_graph_request_runs_runtime_after_required_slots_present(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_student_id.return_value = {
                "skill5_result": {"recommendations": {"mentors": [1] * 5, "projects": [1] * 4, "teammates": [1] * 5}}
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor", "project", "teammate"],
                "entities": {
                    "student_id": {"value": "jamie-taylor-00008", "provenance": "explicit"},
                    "mode": {"value": "graph", "provenance": "explicit"},
                },
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.95,
                "uncertain_fields": [],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)
            reply, _state = core.handle_message(DialogState(task="recommend_existing_student"), "Run graph mode for jamie-taylor-00008")
            self.assertIn("recommendation pipeline", reply)
            runtime.run_recommendation_for_student_id.assert_called_once()


class TestReplV2Flag(unittest.TestCase):
    @patch.dict(os.environ, {"PROGREC_AGENT_V2": "1", "PROGREC_AGENT_API_KEY": "k"}, clear=True)
    @patch("builtins.input", side_effect=["quit"])
    @patch("progrec_agent.repl.AgentCoreV2")
    def test_repl_uses_v2_core_when_flag_enabled(self, mock_v2, _mock_input) -> None:
        from progrec_agent import repl

        repl.main()
        mock_v2.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow progrec_agent.tests.test_conversation_e2e_v2 -v`

Expected: FAIL because `repl.py` still instantiates only V1 and `AgentCoreV2` does not execute real runtime plans.

- [ ] **Step 3: Wire planner actions to runtime and gate REPL with `PROGREC_AGENT_V2`**

```python
# progrec_agent/agent_core_v2.py
from progrec_agent.response.replies import render_clarification, render_execution_blocker, render_recommendation_summary
from progrec_agent.runtime import recommendation_runtime as recommendation_runtime_module

# inside __init__
self.recommendation_runtime = recommendation_runtime or recommendation_runtime_module

# replace final branch in handle_message
plan = build_execution_plan(working)
if plan.action == "await_clarification":
    return render_execution_blocker(working), working
if plan.action == "run_existing_profile_recommendation":
    result = self.recommendation_runtime.run_recommendation_for_student_id(
        repo_root=self.repo_root,
        temp_dir=self.temp_dir,
        student_id=str(plan.arguments["student_id"]),
        mode=str(plan.arguments["mode"]),
        top_k=int(plan.arguments["top_k"]),
    )
    working.execution_context.result_handle = "latest"
    return render_recommendation_summary(result), working
return "I do not support that request yet in V2.", working
```

```python
# progrec_agent/repl.py
from progrec_agent.agent_core_v2 import AgentCoreV2

# inside main()
use_v2 = (os.getenv("PROGREC_AGENT_V2") or "").strip() == "1"
if use_v2:
    core_v2 = AgentCoreV2(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client)
    state = None
    print(CHAT_INTRO)
    while True:
        command = input("> ").strip()
        if command.lower() in {"exit", "quit"}:
            return 0
        if not command:
            continue
        state = state or __import__("progrec_agent.dialog.state", fromlist=["DialogState"]).DialogState()
        reply, state = core_v2.handle_message(state, command)
        print(reply)
else:
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_agent.tests.test_repl_agent_flow progrec_agent.tests.test_conversation_e2e_v2 -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/agent_core_v2.py progrec_agent/repl.py progrec_agent/tests/test_repl_agent_flow.py progrec_agent/tests/test_conversation_e2e_v2.py
git commit -m "feat: wire repl to v2 conversational agent behind flag"
```

### Task 8: Add Golden Conversation Fixtures and Documentation

**Files:**
- Create: `progrec_agent/tests/fixtures/conversations/existing_graph_recommendation.json`
- Create: `progrec_agent/tests/fixtures/conversations/temporary_profile_recommendation.json`
- Create: `progrec_agent/tests/fixtures/conversations/followup_top_mentor.json`
- Create: `progrec_agent/tests/fixtures/conversations/ambiguous_show_profile.json`
- Create: `progrec_agent/tests/fixtures/conversations/conflicting_profile_source.json`
- Modify: `progrec_agent/tests/test_conversation_e2e_v2.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing fixture-driven regression test**

```python
import json
import unittest
from pathlib import Path


class TestConversationFixtures(unittest.TestCase):
    def test_existing_graph_fixture_declares_expected_clarification_sequence(self) -> None:
        path = Path("progrec_agent/tests/fixtures/conversations/existing_graph_recommendation.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["expected_plan_action"], "run_existing_profile_recommendation")
        self.assertEqual(payload["turns"][0]["speaker"], "user")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest progrec_agent.tests.test_conversation_e2e_v2 -v`

Expected: FAIL because fixture files do not exist yet.

- [ ] **Step 3: Add fixtures and README documentation**

```json
{
  "name": "existing_graph_recommendation",
  "turns": [
    {"speaker": "user", "text": "Recommend mentors, projects, and teammates for student_id jamie-taylor-00008 using graph mode."}
  ],
  "expected_clarification_sequence": [],
  "expected_plan_action": "run_existing_profile_recommendation",
  "expected_reply_contains": [
    "recommendation pipeline",
    "Mentors:",
    "Projects:",
    "Teammates:"
  ]
}
```

```json
{
  "name": "temporary_profile_recommendation",
  "turns": [
    {"speaker": "user", "text": "I want a trustworthy AI undergraduate research mentor."},
    {"speaker": "agent", "text": "Should I use an existing student profile from the dataset, or build a temporary profile from your description?"},
    {"speaker": "user", "text": "Build a temporary profile."}
  ],
  "expected_clarification_sequence": ["profile_source", "research_topic", "program_type", "experience_level"],
  "expected_plan_action": "run_temporary_profile_recommendation",
  "expected_reply_contains": ["I still need"]
}
```

```markdown
## Conversational Agent V2

Set `PROGREC_AGENT_V2=1` to enable the redesigned clarification-first agent:

```bash
export PROGREC_AGENT_V2=1
python3 -m progrec_agent.repl
```

The V2 agent:

- parses natural language into structured semantic frames
- collects required slots before execution
- prefers session follow-up context over prompt-only re-interpretation
- stays behind a feature flag until the golden conversation fixtures are stable
```

- [ ] **Step 4: Run the full V2 test suite**

Run: `python3 -m unittest progrec_agent.tests.test_nlu_schema progrec_agent.tests.test_nlu_parser progrec_agent.tests.test_dialog_state progrec_agent.tests.test_dialog_answer_parser progrec_agent.tests.test_clarification_policy progrec_agent.tests.test_planner_v2 progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_conversation_e2e_v2 -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_agent/tests/fixtures/conversations progrec_agent/tests/test_conversation_e2e_v2.py README.md
git commit -m "test: add v2 golden conversation fixtures"
```

## Self-Review Coverage

- Spec architecture sections map to Tasks 1 through 7.
- Dialog state, slot schema, and clarification policy map to Tasks 1, 3, and 4.
- Planner and execution model map to Tasks 5 and 7.
- NLU layer and strict validation map to Task 2.
- Testing, migration, and rollout map to Task 8 plus the `PROGREC_AGENT_V2` feature flag in Task 7.
- Batch-mode pipeline stability is preserved because `run_agent.py` and the Skills 3-5 core are not touched in this plan.

