# Skill-Aware Chat Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the brittle `/chat` intent state machine with a skill-aware planner that reads compact ProgRec skill descriptions, understands natural-language turns, selects validated local tools, standardizes temporary profiles, and records real skill usage.

**Architecture:** Add a skill catalog and skill-aware NLU frame, route pending clarification answers through semantic slot parsing, keep deterministic local planning and execution gates, and surface skill trace entries from real runtime activity. The LLM proposes tasks, slots, skills, and tools; local code validates and executes only registered ProgRec actions.

**Tech Stack:** Python 3.12, stdlib `unittest`, dataclasses, existing `progrec_agent` runtime modules, FastAPI service tests, existing `LLMClient.complete_json()` contract.

---

## Working Tree Warning

The repository already contains unrelated modified files. During implementation, do not revert or reformat unrelated changes. Each task commit should stage only the files listed in that task.

Run before each commit:

```bash
git status --short
```

Expected: only files from the current task are staged. Unrelated modified files may remain unstaged.

## File Structure

Create:

- `progrec_agent/skill_catalog.py`: Builds compact skill cards from `skill_registry.py`, local `SKILL.md` docs, and `tool_registry.py`.
- `progrec_agent/nlu/skill_frame.py`: Defines `SkillAwareFrame`, validates LLM parser payloads, and converts validated frames into dialog slots.
- `progrec_agent/dialog/pending_answer.py`: Slot-specific semantic parser for answers to pending clarification questions.
- `progrec_agent/runtime/profile_standardizer.py`: Converts chat-collected temporary-profile slots into the standardized student profile schema required by Skill 3.
- `progrec_agent/runtime/skill_trace.py`: Helpers for creating skill trace entries from real runtime actions.
- `progrec_agent/tests/test_skill_catalog.py`: Unit tests for compact skill cards.
- `progrec_agent/tests/test_skill_frame.py`: Unit tests for skill-aware frame validation.
- `progrec_agent/tests/test_pending_answer.py`: Unit tests for natural-language pending answers.
- `progrec_agent/tests/test_profile_standardizer.py`: Unit tests for temporary profile standardization.

Modify:

- `progrec_agent/dialog/state.py`: Add `skill_trace`, `last_skill_plan`, and `last_result_summary` fields to `DialogState`.
- `progrec_agent/dialog/answer_parser.py`: Delegate pending-answer parsing to `dialog/pending_answer.py` while preserving the existing public function.
- `progrec_agent/dialog/merge.py`: Add a merge path for `SkillAwareFrame`.
- `progrec_agent/nlu/parser.py`: Add skill-aware parser prompt and `parse_skill_aware_user_message()`.
- `progrec_agent/policy/readiness.py`: Keep required-slot computation compatible with normalized skill-aware tasks.
- `progrec_agent/policy/clarification.py`: Add bounded questions for explain/meta flows if needed.
- `progrec_agent/planning/actions.py`: Add plan fields needed by skill-aware execution.
- `progrec_agent/planning/planner_v2.py`: Validate candidate tools/skills and emit deterministic plan actions.
- `progrec_agent/runtime/recommendation_runtime.py`: Standardize temporary profiles before calling `ProgRecOrchestrator.recommend_for_profile()`.
- `progrec_agent/agent_core_v2.py`: Wire catalog, skill-aware parser, pending-answer parser, planner actions, and skill trace.
- `progrec_agent/response/replies.py`: Add concise meta, explain, refusal, and recommendation rendering helpers.
- `progrec_service/runtime/agent_v2_runner.py`: Return `state.skill_trace` as `structured_result.skill_usage` instead of fabricated fixed skill entries.
- `progrec_agent/tests/test_agent_core_v2.py`: Add regression tests for screenshot flow, meta, follow-up, and out-of-scope behavior.
- `progrec_agent/tests/test_conversation_e2e_v2.py`: Add end-to-end skill-aware dialog tests.
- `progrec_agent/tests/test_nlu_parser.py`: Add skill-aware parser tests while keeping current fallback behavior covered.
- `progrec_agent/tests/test_planner_v2.py`: Add plan selection tests for recommendation, inspect, explain, meta, validation, and refusal.
- `progrec_service/tests/test_agent_stream.py`: Assert `skill_usage` comes from state/runtime trace.

---

### Task 1: Add Regression Tests For The Screenshot Failure

**Files:**
- Modify: `progrec_agent/tests/test_dialog_answer_parser.py`
- Modify: `progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Add failing pending-answer parser tests**

Append these tests to `progrec_agent/tests/test_dialog_answer_parser.py`:

```python
    def test_profile_source_accepts_full_temporary_profile_option(self) -> None:
        state = DialogState(
            task="recommendation_request",
            pending_question=PendingQuestion(
                slot_name="profile_source",
                question="Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
                expected_answer_shape="existing_profile|temporary_profile",
            ),
        )

        updated = apply_pending_answer(state, "build a temporary profile from your description")

        self.assertEqual(updated.resolved_slots["profile_source"], "temporary_profile")
        self.assertIsNone(updated.pending_question)

    def test_profile_source_accepts_existing_student_profile_phrase(self) -> None:
        state = DialogState(
            task="recommendation_request",
            pending_question=PendingQuestion(
                slot_name="profile_source",
                question="Should I use an existing student profile from the dataset, or build a temporary profile from your description?",
                expected_answer_shape="existing_profile|temporary_profile",
            ),
        )

        updated = apply_pending_answer(state, "use an existing student profile")

        self.assertEqual(updated.resolved_slots["profile_source"], "existing_profile")
```

- [ ] **Step 2: Add failing conversation regression test**

Append this test to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_full_temporary_profile_answer_does_not_refuse_after_profile_source_question(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "intent": "recommendation_request",
                "target_types": ["mentor"],
                "entities": {},
                "constraints": {},
                "preferences": {},
                "references": {},
                "confidence": 0.8,
                "uncertain_fields": ["profile_source"],
                "possible_conflicts": [],
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            first_reply, state = core.handle_message(
                DialogState(),
                "Help me find a mentor for NLP and trustworthy AI.",
            )

            second_reply, updated = core.handle_message(
                state,
                "build a temporary profile from your description",
            )

            self.assertIn("existing student profile", first_reply)
            self.assertNotIn("I can only help", second_reply)
            self.assertEqual(updated.task, "recommend_temporary_profile")
            self.assertEqual(updated.resolved_slots["profile_source"], "temporary_profile")
            self.assertIn("research_topic", updated.missing_slots)
```

- [ ] **Step 3: Run the targeted tests to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_dialog_answer_parser \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: FAIL because `apply_pending_answer()` stores `build a temporary profile from your description` literally.

- [ ] **Step 4: Commit only failing regression tests**

```bash
git add progrec_agent/tests/test_dialog_answer_parser.py progrec_agent/tests/test_agent_core_v2.py
git commit -m "test: capture skill-aware chat regression"
```

Expected: commit succeeds with only test changes staged.

---

### Task 2: Add SkillCatalog

**Files:**
- Create: `progrec_agent/skill_catalog.py`
- Create: `progrec_agent/tests/test_skill_catalog.py`

- [ ] **Step 1: Write failing SkillCatalog tests**

Create `progrec_agent/tests/test_skill_catalog.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path

from progrec_agent.skill_catalog import build_skill_catalog


class TestSkillCatalog(unittest.TestCase):
    def test_catalog_contains_compact_cards_for_core_skills(self) -> None:
        catalog = build_skill_catalog(Path("."))
        cards = {card.skill_id: card for card in catalog.cards}

        self.assertIn("/student-profiling", cards)
        self.assertIn("/mentor-discovery", cards)
        self.assertIn("/project-teammate-discovery", cards)
        self.assertIn("/social-ranking", cards)
        self.assertIn("mentor", cards["/mentor-discovery"].when_to_use.lower())
        self.assertIn("recommend_full_pipeline", cards["/mentor-discovery"].allowed_tools)

    def test_catalog_prompt_context_is_compact_and_names_allowed_tools(self) -> None:
        catalog = build_skill_catalog(Path("."))
        prompt_context = catalog.to_prompt_context()

        self.assertIn("/mentor-discovery", prompt_context)
        self.assertIn("recommend_full_pipeline", prompt_context)
        self.assertLess(len(prompt_context), 9000)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_skill_catalog -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.skill_catalog'`.

- [ ] **Step 3: Implement SkillCatalog**

Create `progrec_agent/skill_catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from progrec_agent.skill_registry import SKILL_REGISTRY, list_skills
from progrec_agent.tool_registry import TOOLS


_SKILL_DOC_PATHS = {
    "/student-profiling": "skill1_student_profiling/SKILL.md",
    "/academic-graph": "skill2_academic_graph_builder/SKILL.md",
    "/mentor-discovery": "skill3_mentor_discovery/SKILL.md",
    "/project-teammate-discovery": "skill4_program_teammate_discovery/SKILL.md",
    "/social-ranking": "skill5_student_recommendation_ranker/SKILL.md",
}

_SKILL_TOOLS = {
    "/student-profiling": ["recommend_full_pipeline"],
    "/academic-graph": ["recommend_full_pipeline", "debug_graph_mode", "inspect_artifacts", "rebuild_skill2_graph"],
    "/mentor-discovery": ["recommend_full_pipeline"],
    "/project-teammate-discovery": ["recommend_full_pipeline"],
    "/social-ranking": ["recommend_full_pipeline"],
}

_CANNOT_DO = {
    "/student-profiling": ["rank mentors", "recommend projects", "perform final social ranking"],
    "/academic-graph": ["choose mentors by itself", "explain ranked recommendations"],
    "/mentor-discovery": ["recommend projects", "recommend teammates", "perform final joint ranking"],
    "/project-teammate-discovery": ["standardize raw profiles", "perform final joint ranking"],
    "/social-ranking": ["parse raw student stories", "rebuild graph resources"],
}


@dataclass(frozen=True)
class SkillCard:
    skill_id: str
    name: str
    when_to_use: str
    requires: list[str]
    produces: list[str]
    allowed_tools: list[str]
    cannot_do: list[str]

    def to_prompt_block(self) -> str:
        return (
            f"- skill_id: {self.skill_id}\n"
            f"  name: {self.name}\n"
            f"  when_to_use: {self.when_to_use}\n"
            f"  requires: {', '.join(self.requires)}\n"
            f"  produces: {', '.join(self.produces)}\n"
            f"  allowed_tools: {', '.join(self.allowed_tools)}\n"
            f"  cannot_do: {', '.join(self.cannot_do)}"
        )


@dataclass(frozen=True)
class SkillCatalog:
    cards: list[SkillCard]
    allowed_skill_ids: set[str]
    allowed_tool_names: set[str]

    def to_prompt_context(self) -> str:
        return "\n".join(card.to_prompt_block() for card in self.cards)


def _split_contract(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = [part.strip(" .") for part in text.replace(";", ",").split(",")]
    return [part for part in parts if part]


def _first_doc_description(repo_root: Path, skill_id: str) -> str:
    doc_path = repo_root / _SKILL_DOC_PATHS.get(skill_id, "")
    if not doc_path.is_file():
        return ""
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            return stripped.removeprefix("description:").strip().strip('"')
    return ""


def _card_from_registry(repo_root: Path, skill_id: str, meta: dict[str, Any]) -> SkillCard:
    doc_description = _first_doc_description(repo_root, skill_id)
    when_to_use = doc_description or str(meta.get("function") or "")
    allowed_tools = [tool for tool in _SKILL_TOOLS.get(skill_id, []) if tool in TOOLS]
    return SkillCard(
        skill_id=skill_id,
        name=str(meta.get("name") or skill_id),
        when_to_use=when_to_use,
        requires=_split_contract(meta.get("input_contract")),
        produces=_split_contract(meta.get("output_contract")),
        allowed_tools=allowed_tools,
        cannot_do=list(_CANNOT_DO.get(skill_id, [])),
    )


def build_skill_catalog(repo_root: Path) -> SkillCatalog:
    cards = [
        _card_from_registry(repo_root, skill_id, dict(SKILL_REGISTRY[skill_id]))
        for skill_id in list_skills()
        if skill_id in SKILL_REGISTRY
    ]
    return SkillCatalog(
        cards=cards,
        allowed_skill_ids={card.skill_id for card in cards},
        allowed_tool_names=set(TOOLS),
    )
```

- [ ] **Step 4: Run SkillCatalog tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_skill_catalog -v
```

Expected: PASS.

- [ ] **Step 5: Commit SkillCatalog**

```bash
git add progrec_agent/skill_catalog.py progrec_agent/tests/test_skill_catalog.py
git commit -m "feat: add skill catalog"
```

Expected: commit contains only the catalog and its tests.

---

### Task 3: Add SkillAwareFrame Schema And Validation

**Files:**
- Create: `progrec_agent/nlu/skill_frame.py`
- Create: `progrec_agent/tests/test_skill_frame.py`

- [ ] **Step 1: Write failing frame validation tests**

Create `progrec_agent/tests/test_skill_frame.py`:

```python
from __future__ import annotations

import unittest
from pathlib import Path

from progrec_agent.nlu.skill_frame import validate_skill_frame_payload
from progrec_agent.skill_catalog import build_skill_catalog


class TestSkillAwareFrame(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = build_skill_catalog(Path("."))

    def test_validates_recommendation_payload_with_candidate_skills(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": ["program_type", "experience_level"],
                "confidence": 0.92,
                "reasoning_summary": "Mentor recommendation request with a temporary profile.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertEqual(frame.slots["research_topic"].value, "NLP and trustworthy AI")
        self.assertIn("/mentor-discovery", frame.candidate_skills)

    def test_rejects_unknown_skill_and_tool_names(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {},
                "candidate_skills": ["/made-up-skill"],
                "candidate_tools": ["delete_everything"],
                "missing_information": [],
                "confidence": 0.88,
                "reasoning_summary": "Invalid tool proposal.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("unknown_skill:/made-up-skill", frame.validation_errors)
        self.assertIn("unknown_tool:delete_everything", frame.validation_errors)

    def test_invalid_mode_is_not_accepted(self) -> None:
        frame = validate_skill_frame_payload(
            {
                "turn_type": "domain_task",
                "task": "recommend_existing_student",
                "target_types": ["mentor"],
                "slots": {"mode": {"value": "production", "provenance": "explicit"}},
                "candidate_skills": ["/mentor-discovery"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.8,
                "reasoning_summary": "Bad mode.",
            },
            self.catalog,
        )

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("invalid_mode:production", frame.validation_errors)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_skill_frame -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.nlu.skill_frame'`.

- [ ] **Step 3: Implement frame schema**

Create `progrec_agent/nlu/skill_frame.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from progrec_agent.nlu.schema import SlotValue
from progrec_agent.skill_catalog import SkillCatalog


ALLOWED_TURN_TYPES = {
    "domain_task",
    "clarification_answer",
    "inspect_previous_result",
    "resource_validation",
    "meta_question",
    "out_of_scope",
}
ALLOWED_TASKS = {
    "recommend_existing_student",
    "recommend_temporary_profile",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
    "answer_meta_question",
    "out_of_scope",
}
ALLOWED_PROVENANCE = {"explicit", "inferred", "unknown"}
ALLOWED_MODES = {"demo", "graph"}


@dataclass(frozen=True)
class SkillAwareFrame:
    turn_type: str
    task: str
    target_types: list[str] = field(default_factory=list)
    slots: dict[str, SlotValue] = field(default_factory=dict)
    candidate_skills: list[str] = field(default_factory=list)
    candidate_tools: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning_summary: str = ""
    validation_errors: list[str] = field(default_factory=list)


def _coerce_slot_value(raw: Any) -> SlotValue:
    row = dict(raw or {})
    provenance = str(row.get("provenance") or "unknown")
    if provenance not in ALLOWED_PROVENANCE:
        provenance = "unknown"
    return SlotValue(value=row.get("value"), provenance=provenance)


def _safe_out_of_scope(errors: list[str], *, reasoning_summary: str = "") -> SkillAwareFrame:
    return SkillAwareFrame(
        turn_type="out_of_scope",
        task="out_of_scope",
        confidence=0.0,
        reasoning_summary=reasoning_summary,
        validation_errors=errors,
    )


def validate_skill_frame_payload(payload: dict[str, object], catalog: SkillCatalog) -> SkillAwareFrame:
    errors: list[str] = []
    turn_type = str(payload.get("turn_type") or "")
    task = str(payload.get("task") or "")
    if turn_type not in ALLOWED_TURN_TYPES:
        errors.append(f"invalid_turn_type:{turn_type}")
    if task not in ALLOWED_TASKS:
        errors.append(f"invalid_task:{task}")

    slots = {
        str(key): _coerce_slot_value(value)
        for key, value in dict(payload.get("slots") or {}).items()
    }
    mode = slots.get("mode")
    if mode is not None and str(mode.value).strip().lower() not in ALLOWED_MODES:
        errors.append(f"invalid_mode:{mode.value}")

    candidate_skills = [str(item) for item in list(payload.get("candidate_skills") or [])]
    candidate_tools = [str(item) for item in list(payload.get("candidate_tools") or [])]
    for skill_id in candidate_skills:
        if skill_id not in catalog.allowed_skill_ids:
            errors.append(f"unknown_skill:{skill_id}")
    for tool_name in candidate_tools:
        if tool_name not in catalog.allowed_tool_names:
            errors.append(f"unknown_tool:{tool_name}")

    reasoning_summary = str(payload.get("reasoning_summary") or "")
    if errors:
        return _safe_out_of_scope(errors, reasoning_summary=reasoning_summary)

    return SkillAwareFrame(
        turn_type=turn_type,
        task=task,
        target_types=[str(item) for item in list(payload.get("target_types") or [])],
        slots=slots,
        candidate_skills=candidate_skills,
        candidate_tools=candidate_tools,
        missing_information=[str(item) for item in list(payload.get("missing_information") or [])],
        confidence=float(payload.get("confidence") or 0.0),
        reasoning_summary=reasoning_summary,
        validation_errors=[],
    )
```

- [ ] **Step 4: Run frame tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_skill_frame -v
```

Expected: PASS.

- [ ] **Step 5: Commit frame schema**

```bash
git add progrec_agent/nlu/skill_frame.py progrec_agent/tests/test_skill_frame.py
git commit -m "feat: add skill-aware nlu frame"
```

Expected: commit contains only frame schema and tests.

---

### Task 4: Add Semantic PendingAnswerParser

**Files:**
- Create: `progrec_agent/dialog/pending_answer.py`
- Modify: `progrec_agent/dialog/answer_parser.py`
- Create: `progrec_agent/tests/test_pending_answer.py`
- Modify: `progrec_agent/tests/test_dialog_answer_parser.py`
- Modify: `progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Write focused pending-answer tests**

Create `progrec_agent/tests/test_pending_answer.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.dialog.pending_answer import parse_pending_answer
from progrec_agent.dialog.state import PendingQuestion


class TestPendingAnswer(unittest.TestCase):
    def test_profile_source_variants(self) -> None:
        question = PendingQuestion(
            slot_name="profile_source",
            question="Use existing profile or temporary profile?",
            expected_answer_shape="existing_profile|temporary_profile",
        )

        self.assertEqual(parse_pending_answer(question, "temporary").value, "temporary_profile")
        self.assertEqual(
            parse_pending_answer(question, "build a temporary profile from your description").value,
            "temporary_profile",
        )
        self.assertEqual(
            parse_pending_answer(question, "use an existing student profile").value,
            "existing_profile",
        )

    def test_mode_variants(self) -> None:
        question = PendingQuestion(
            slot_name="mode",
            question="Use demo or graph mode?",
            expected_answer_shape="demo|graph",
        )

        self.assertEqual(parse_pending_answer(question, "use the real graph").value, "graph")
        self.assertEqual(parse_pending_answer(question, "graph mode please").value, "graph")
        self.assertEqual(parse_pending_answer(question, "demo mode").value, "demo")

    def test_free_text_slots_preserve_answer(self) -> None:
        topic = PendingQuestion("research_topic", "What research topic?", "free_text")
        program = PendingQuestion("program_type", "What program?", "free_text")

        self.assertEqual(parse_pending_answer(topic, "NLP safety and trustworthy AI").value, "NLP safety and trustworthy AI")
        self.assertEqual(parse_pending_answer(program, "undergraduate research").value, "undergraduate research")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_pending_answer \
  progrec_agent.tests.test_dialog_answer_parser \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: FAIL because `progrec_agent.dialog.pending_answer` does not exist.

- [ ] **Step 3: Implement pending-answer parser**

Create `progrec_agent/dialog/pending_answer.py`:

```python
from __future__ import annotations

import re

from progrec_agent.dialog.state import PendingQuestion
from progrec_agent.nlu.schema import SlotValue


def _normalized(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _parse_profile_source(text: str) -> str:
    if _contains_any(
        text,
        (
            "temporary",
            "my description",
            "from your description",
            "from my description",
            "build one",
            "build a profile",
            "create a profile",
            "use what i tell",
        ),
    ):
        return "temporary_profile"
    if _contains_any(text, ("existing", "dataset", "student id", "student_id", "saved profile")):
        return "existing_profile"
    return ""


def _parse_mode(text: str) -> str:
    if re.search(r"\b(graph|real graph|full graph)\b", text):
        return "graph"
    if re.search(r"\b(demo|sample)\b", text):
        return "demo"
    return ""


def _parse_experience_level(text: str) -> str:
    if re.search(r"\b(beginner|new|novice|introductory)\b", text):
        return "beginner"
    if re.search(r"\b(intermediate|some experience|moderate)\b", text):
        return "intermediate"
    if re.search(r"\b(advanced|experienced|expert|strong)\b", text):
        return "advanced"
    return ""


def parse_pending_answer(question: PendingQuestion, user_text: str) -> SlotValue:
    raw = user_text.strip()
    text = _normalized(user_text)
    slot_name = question.slot_name

    if slot_name == "profile_source":
        value = _parse_profile_source(text)
        return SlotValue(value=value or raw, provenance="explicit")
    if slot_name == "mode":
        value = _parse_mode(text)
        return SlotValue(value=value or raw, provenance="explicit")
    if slot_name == "experience_level":
        value = _parse_experience_level(text)
        return SlotValue(value=value or raw, provenance="explicit")
    return SlotValue(value=raw, provenance="explicit")
```

- [ ] **Step 4: Modify answer_parser to delegate**

Replace `progrec_agent/dialog/answer_parser.py` with:

```python
from __future__ import annotations

from copy import deepcopy

from progrec_agent.dialog.pending_answer import parse_pending_answer
from progrec_agent.dialog.state import DialogState


def apply_pending_answer(state: DialogState, user_text: str) -> DialogState:
    updated = deepcopy(state)
    pending = updated.pending_question
    if pending is None:
        return updated
    slot = parse_pending_answer(pending, user_text)
    updated.resolved_slots[pending.slot_name] = slot.value
    updated.pending_question = None
    updated.clarification_turn_count += 1
    updated.last_user_turn = user_text
    return updated
```

- [ ] **Step 5: Run pending-answer tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_pending_answer \
  progrec_agent.tests.test_dialog_answer_parser \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: PASS for the pending-answer and screenshot regression tests.

- [ ] **Step 6: Commit pending-answer parsing**

```bash
git add \
  progrec_agent/dialog/pending_answer.py \
  progrec_agent/dialog/answer_parser.py \
  progrec_agent/tests/test_pending_answer.py \
  progrec_agent/tests/test_dialog_answer_parser.py \
  progrec_agent/tests/test_agent_core_v2.py
git commit -m "fix: parse pending chat answers semantically"
```

Expected: commit contains parser implementation and tests.

---

### Task 5: Add Skill-Aware Parser

**Files:**
- Modify: `progrec_agent/nlu/parser.py`
- Modify: `progrec_agent/tests/test_nlu_parser.py`

- [ ] **Step 1: Add failing skill-aware parser tests**

Append these tests to `progrec_agent/tests/test_nlu_parser.py`:

```python
    def test_skill_aware_parser_returns_candidate_skills_and_slots(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.return_value = {
            "turn_type": "domain_task",
            "task": "recommend_temporary_profile",
            "target_types": ["mentor"],
            "slots": {
                "profile_source": {"value": "temporary_profile", "provenance": "inferred"},
                "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"},
            },
            "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
            "candidate_tools": ["recommend_full_pipeline"],
            "missing_information": ["program_type", "experience_level"],
            "confidence": 0.91,
            "reasoning_summary": "The user wants a mentor recommendation for a temporary profile.",
        }

        frame = parse_skill_aware_user_message(
            "Help me find a mentor for NLP and trustworthy AI.",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(frame.task, "recommend_temporary_profile")
        self.assertEqual(frame.slots["research_topic"].value, "NLP and trustworthy AI")
        self.assertIn("/mentor-discovery", frame.candidate_skills)

    def test_skill_aware_parser_falls_back_to_out_of_scope_on_llm_error(self) -> None:
        from pathlib import Path

        from progrec_agent.nlu.parser import parse_skill_aware_user_message
        from progrec_agent.skill_catalog import build_skill_catalog

        llm = Mock()
        llm.complete_json.side_effect = ValueError("bad upstream json")

        frame = parse_skill_aware_user_message(
            "what is the weather today?",
            dialog_state=None,
            llm_client=llm,
            skill_catalog=build_skill_catalog(Path(".")),
        )

        self.assertEqual(frame.task, "out_of_scope")
        self.assertIn("llm_parse_error", frame.validation_errors)
```

- [ ] **Step 2: Run parser tests to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_nlu_parser -v
```

Expected: FAIL because `parse_skill_aware_user_message` is not defined.

- [ ] **Step 3: Implement skill-aware parser without removing the legacy parser**

Add this import and prompt to `progrec_agent/nlu/parser.py`:

```python
from progrec_agent.nlu.skill_frame import SkillAwareFrame, validate_skill_frame_payload
from progrec_agent.skill_catalog import SkillCatalog
```

Add this prompt and function below the existing `SEMANTIC_PARSE_PROMPT`:

```python
SKILL_AWARE_PARSE_PROMPT = """
You are the skill-aware NLU layer for ProgRec, a bounded academic recommendation assistant.
Use the skill catalog to classify the user turn and propose candidate skills/tools.
Return strict JSON with keys:
turn_type, task, target_types, slots, candidate_skills, candidate_tools, missing_information, confidence, reasoning_summary.
Do not execute tools.
Do not invent student ids.
Use task "recommend_temporary_profile" when the user wants recommendations from a described profile.
Use task "recommend_existing_student" only when a dataset student_id is explicit or the user chooses an existing profile.
Use task "inspect_recommendation" or "explain_recommendation" for follow-ups about previous ranked results.
Use task "validate_resources" for graph/demo resource checks.
Use task "answer_meta_question" for questions about what skills or tools were used.
Use task "out_of_scope" only when the request is unrelated to ProgRec recommendations.
Only propose candidate_skills and candidate_tools that appear in the skill catalog.
Each slot value must be an object with "value" and "provenance".
""".strip()


def parse_skill_aware_user_message(
    user_text: str,
    *,
    dialog_state,
    llm_client,
    skill_catalog: SkillCatalog,
) -> SkillAwareFrame:
    if llm_client is None:
        fallback = build_domain_fallback_frame(user_text, reason="missing_llm_skill_fallback")
        return SkillAwareFrame(
            turn_type="domain_task" if fallback.intent == "recommendation_request" else "out_of_scope",
            task="recommend_temporary_profile" if fallback.intent == "recommendation_request" else "out_of_scope",
            target_types=list(fallback.target_types),
            slots={**fallback.entities, **fallback.constraints, **fallback.preferences, **fallback.references},
            candidate_skills=["/student-profiling", "/mentor-discovery", "/social-ranking"]
            if fallback.intent == "recommendation_request"
            else [],
            candidate_tools=["recommend_full_pipeline"] if fallback.intent == "recommendation_request" else [],
            missing_information=list(fallback.uncertain_fields),
            confidence=fallback.confidence,
            reasoning_summary="Local domain fallback.",
            validation_errors=[],
        )
    try:
        payload = llm_client.complete_json(
            f"{SKILL_AWARE_PARSE_PROMPT}\n"
            f"Skill catalog:\n{skill_catalog.to_prompt_context()}\n"
            f"Dialog state: {dialog_state}\n"
            f"User message: {user_text}"
        )
        return validate_skill_frame_payload(dict(payload), skill_catalog)
    except Exception:
        return SkillAwareFrame(
            turn_type="out_of_scope",
            task="out_of_scope",
            confidence=0.0,
            reasoning_summary="LLM parse failure.",
            validation_errors=["llm_parse_error"],
        )
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_nlu_parser -v
```

Expected: PASS.

- [ ] **Step 5: Run legacy parser smoke tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_nlu_parser \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: PASS.

- [ ] **Step 6: Commit skill-aware parser**

```bash
git add progrec_agent/nlu/parser.py progrec_agent/tests/test_nlu_parser.py
git commit -m "feat: parse chat turns with skill catalog"
```

Expected: commit contains parser and tests only.

---

### Task 6: Add Dialog State Fields And Skill Frame Merge

**Files:**
- Modify: `progrec_agent/dialog/state.py`
- Modify: `progrec_agent/dialog/merge.py`
- Modify: `progrec_agent/tests/test_dialog_state.py`
- Modify: `progrec_agent/tests/test_dialog_answer_parser.py`

- [ ] **Step 1: Add failing state and merge tests**

Append to `progrec_agent/tests/test_dialog_state.py`:

```python
    def test_dialog_state_tracks_skill_plan_and_trace(self) -> None:
        state = DialogState()

        self.assertEqual(state.skill_trace, [])
        self.assertEqual(state.last_skill_plan, {})
        self.assertEqual(state.last_result_summary, "")
```

Append to `progrec_agent/tests/test_dialog_answer_parser.py`:

```python
    def test_merge_skill_frame_promotes_explicit_slots(self) -> None:
        from progrec_agent.dialog.merge import merge_skill_frame
        from progrec_agent.nlu.schema import SlotValue
        from progrec_agent.nlu.skill_frame import SkillAwareFrame

        frame = SkillAwareFrame(
            turn_type="domain_task",
            task="recommend_temporary_profile",
            target_types=["mentor"],
            slots={
                "research_topic": SlotValue("NLP", "explicit"),
                "profile_source": SlotValue("temporary_profile", "inferred"),
            },
            candidate_skills=["/mentor-discovery"],
            candidate_tools=["recommend_full_pipeline"],
            missing_information=["program_type"],
            confidence=0.9,
            reasoning_summary="topic supplied",
        )

        merged = merge_skill_frame(DialogState(), frame)

        self.assertEqual(merged.task, "recommend_temporary_profile")
        self.assertEqual(merged.resolved_slots["research_topic"], "NLP")
        self.assertEqual(merged.candidate_slots["profile_source"], "temporary_profile")
        self.assertEqual(merged.last_skill_plan["candidate_skills"], ["/mentor-discovery"])
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_dialog_state \
  progrec_agent.tests.test_dialog_answer_parser \
  -v
```

Expected: FAIL because `DialogState` does not have the new fields and `merge_skill_frame()` is missing.

- [ ] **Step 3: Add DialogState fields**

Modify `progrec_agent/dialog/state.py` by adding these fields to `DialogState`:

```python
    skill_trace: list[dict[str, object]] = field(default_factory=list)
    last_skill_plan: dict[str, object] = field(default_factory=dict)
    last_result_summary: str = ""
```

- [ ] **Step 4: Add merge_skill_frame**

Append to `progrec_agent/dialog/merge.py`:

```python
def merge_skill_frame(state: DialogState, frame) -> DialogState:
    updated = deepcopy(state)
    if frame.task and frame.task != "out_of_scope":
        updated.task = frame.task
    elif frame.task == "out_of_scope":
        updated.task = "out_of_scope"
    for key, slot in frame.slots.items():
        if getattr(slot, "provenance", "unknown") == "explicit":
            updated.resolved_slots[key] = slot.value
        elif key not in updated.resolved_slots:
            updated.candidate_slots[key] = slot.value
    updated.last_skill_plan = {
        "turn_type": frame.turn_type,
        "task": frame.task,
        "target_types": list(frame.target_types),
        "candidate_skills": list(frame.candidate_skills),
        "candidate_tools": list(frame.candidate_tools),
        "missing_information": list(frame.missing_information),
        "confidence": frame.confidence,
        "reasoning_summary": frame.reasoning_summary,
        "validation_errors": list(frame.validation_errors),
    }
    return updated
```

- [ ] **Step 5: Run state and merge tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_dialog_state \
  progrec_agent.tests.test_dialog_answer_parser \
  -v
```

Expected: PASS.

- [ ] **Step 6: Commit dialog state and merge**

```bash
git add \
  progrec_agent/dialog/state.py \
  progrec_agent/dialog/merge.py \
  progrec_agent/tests/test_dialog_state.py \
  progrec_agent/tests/test_dialog_answer_parser.py
git commit -m "feat: track skill-aware dialog state"
```

Expected: commit contains only dialog state and merge changes.

---

### Task 7: Standardize Temporary Profiles Before Runtime

**Files:**
- Create: `progrec_agent/runtime/profile_standardizer.py`
- Modify: `progrec_agent/runtime/recommendation_runtime.py`
- Create: `progrec_agent/tests/test_profile_standardizer.py`
- Modify: `progrec_agent/tests/test_conversation_e2e_v2.py`

- [ ] **Step 1: Write failing profile standardizer tests**

Create `progrec_agent/tests/test_profile_standardizer.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile


class TestProfileStandardizer(unittest.TestCase):
    def test_standardizes_chat_slots_for_skill3(self) -> None:
        profile = standardize_temporary_profile(
            {
                "profile_source": "temporary_profile",
                "research_topic": "NLP and trustworthy AI",
                "program_type": "undergraduate research",
                "experience_level": "intermediate",
                "skills": ["python", "machine learning"],
                "availability": "low",
            }
        )

        self.assertTrue(str(profile["student_id"]).startswith("chat-temp-"))
        self.assertEqual(profile["grade"], "unknown")
        self.assertEqual(profile["major"], "unknown")
        self.assertEqual(profile["skills"], ["python", "machine learning"])
        self.assertEqual(profile["interests"], ["nlp", "trustworthy ai"])
        self.assertEqual(profile["availability"], "low")
        self.assertIn("undergraduate research", profile["experience_summary"])
        self.assertIn("intermediate", profile["experience_summary"])

    def test_defaults_missing_optional_fields(self) -> None:
        profile = standardize_temporary_profile({"research_topic": "graph neural networks"})

        self.assertEqual(profile["skills"], [])
        self.assertEqual(profile["interests"], ["graph neural networks"])
        self.assertEqual(profile["availability"], "moderate")
        self.assertEqual(profile["major"], "unknown")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_profile_standardizer -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'progrec_agent.runtime.profile_standardizer'`.

- [ ] **Step 3: Implement standardizer**

Create `progrec_agent/runtime/profile_standardizer.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    separators = [",", ";"]
    parts = [text]
    for sep in separators:
        if sep in text:
            parts = text.split(sep)
            break
    return [part.strip().lower() for part in parts if part.strip()]


def _topic_terms(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    normalized = text.replace("&", " and ")
    parts = [part.strip().lower() for part in normalized.split(" and ") if part.strip()]
    return parts or [text.lower()]


def _experience_summary(slots: dict[str, object]) -> str:
    pieces: list[str] = []
    topic = str(slots.get("research_topic") or "").strip()
    program = str(slots.get("program_type") or "").strip()
    experience = str(slots.get("experience_level") or "").strip()
    freeform = str(slots.get("profile_details") or slots.get("description") or "").strip()
    if topic:
        pieces.append(f"Interested in {topic}.")
    if program:
        pieces.append(f"Targeting {program}.")
    if experience:
        pieces.append(f"Experience level: {experience}.")
    if freeform:
        pieces.append(freeform)
    return " ".join(pieces).strip()


def standardize_temporary_profile(slots: dict[str, object]) -> dict[str, object]:
    topic = slots.get("research_topic") or slots.get("topic") or slots.get("research_area") or ""
    skills = _as_list(slots.get("skills"))
    interests = _topic_terms(topic) + [item for item in _as_list(slots.get("interests")) if item not in _topic_terms(topic)]
    availability = str(slots.get("availability") or "moderate").strip().lower() or "moderate"
    return {
        "student_id": f"chat-temp-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "grade": str(slots.get("grade") or "unknown").strip() or "unknown",
        "major": str(slots.get("major") or "unknown").strip() or "unknown",
        "skills": skills,
        "interests": interests,
        "experience_summary": _experience_summary({**slots, "research_topic": topic}),
        "availability": availability,
    }
```

- [ ] **Step 4: Modify recommendation runtime**

Replace `run_recommendation_for_profile()` in `progrec_agent/runtime/recommendation_runtime.py` with:

```python
def run_recommendation_for_profile(*, repo_root, temp_dir, profile: dict[str, object], top_k: int):
    from progrec_agent.runtime.profile_standardizer import standardize_temporary_profile

    standardized = (
        dict(profile)
        if {"student_id", "grade", "major", "skills", "interests", "experience_summary", "availability"}.issubset(profile)
        else standardize_temporary_profile(profile)
    )
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    return orchestrator.recommend_for_profile(standardized, top_k=top_k)
```

- [ ] **Step 5: Add runtime standardization test**

Append to `progrec_agent/tests/test_conversation_e2e_v2.py`:

```python
    def test_temporary_profile_runtime_receives_standardized_profile(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_profile.return_value = {
                "skill5_result": {
                    "recommendations": {"mentors": [1], "projects": [], "teammates": []}
                }
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP", "provenance": "explicit"},
                    "program_type": {"value": "undergraduate research", "provenance": "explicit"},
                    "experience_level": {"value": "intermediate", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.94,
                "reasoning_summary": "Complete temporary mentor request.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, _state = core.handle_message(DialogState(), "Find me an NLP mentor.")

            self.assertIn("recommendation pipeline", reply)
            profile = runtime.run_recommendation_for_profile.call_args.kwargs["profile"]
            self.assertEqual(profile["research_topic"], "NLP")
```

This test confirms that `AgentCoreV2` passes planner slots to the runtime. The runtime-level standardizer test confirms those slots become a full Skill 3 profile.

- [ ] **Step 6: Run standardizer tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_profile_standardizer \
  progrec_agent.tests.test_conversation_e2e_v2 \
  -v
```

Expected: PASS after AgentCoreV2 is wired in Task 9. If this fails now because AgentCoreV2 still uses the legacy parser, keep the profile standardizer test passing and let the conversation test pass in Task 9.

- [ ] **Step 7: Commit standardizer**

```bash
git add \
  progrec_agent/runtime/profile_standardizer.py \
  progrec_agent/runtime/recommendation_runtime.py \
  progrec_agent/tests/test_profile_standardizer.py \
  progrec_agent/tests/test_conversation_e2e_v2.py
git commit -m "feat: standardize temporary chat profiles"
```

Expected: commit includes standardization code and tests.

---

### Task 8: Add Real SkillTrace Helpers

**Files:**
- Create: `progrec_agent/runtime/skill_trace.py`
- Modify: `progrec_agent/dialog/state.py`
- Modify: `progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Add failing skill trace tests**

Append to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_recommendation_result_records_real_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
                "skill4_result": {"mentor_project_teammate_recommendations": []},
                "skill5_result": {
                    "recommendations": {"mentors": [{"rank": 1}], "projects": [], "teammates": []}
                },
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP", "provenance": "explicit"},
                    "program_type": {"value": "undergraduate research", "provenance": "explicit"},
                    "experience_level": {"value": "intermediate", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.95,
                "reasoning_summary": "Complete temporary request.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            _reply, state = core.handle_message(DialogState(), "Find an NLP mentor.")

            skill_ids = [entry["skill_id"] for entry in state.skill_trace]
            self.assertIn("/student-profiling", skill_ids)
            self.assertIn("/mentor-discovery", skill_ids)
            self.assertIn("/social-ranking", skill_ids)
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2.TestAgentCoreV2.test_recommendation_result_records_real_skill_trace -v
```

Expected: FAIL because no runtime trace is recorded.

- [ ] **Step 3: Implement skill trace helpers**

Create `progrec_agent/runtime/skill_trace.py`:

```python
from __future__ import annotations

from typing import Any


def trace_entry(
    *,
    skill_id: str,
    tool_name: str,
    status: str,
    summary: str,
    inputs: dict[str, object] | None = None,
    outputs: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "skill_id": skill_id,
        "tool_name": tool_name,
        "status": status,
        "summary": summary,
        "inputs": dict(inputs or {}),
        "outputs": dict(outputs or {}),
    }


def recommendation_trace(result: dict[str, Any], *, tool_name: str = "recommend_full_pipeline") -> list[dict[str, object]]:
    student_profile = dict(result.get("student_profile") or {})
    skill3 = dict(result.get("skill3_result") or {})
    skill4 = dict(result.get("skill4_result") or {})
    skill5 = dict(result.get("skill5_result") or {})
    recs = dict(skill5.get("recommendations") or {})
    student_id = str(student_profile.get("student_id") or skill3.get("student_id") or "")
    return [
        trace_entry(
            skill_id="/student-profiling",
            tool_name=tool_name,
            status="succeeded",
            summary="Resolved the student profile used for the recommendation request.",
            inputs={"profile_source": student_profile.get("student_id", "")},
            outputs={"student_id": student_id},
        ),
        trace_entry(
            skill_id="/mentor-discovery",
            tool_name=tool_name,
            status="succeeded",
            summary="Ranked mentor candidates for the student context.",
            inputs={"student_id": student_id},
            outputs={"mentor_count": len(list(skill3.get("mentor_candidates") or recs.get("mentors") or []))},
        ),
        trace_entry(
            skill_id="/project-teammate-discovery",
            tool_name=tool_name,
            status="succeeded",
            summary="Expanded mentor matches into project and teammate recommendations.",
            inputs={"student_id": student_id},
            outputs={
                "project_count": len(list(recs.get("projects") or [])),
                "teammate_count": len(list(recs.get("teammates") or [])),
            },
        ),
        trace_entry(
            skill_id="/social-ranking",
            tool_name=tool_name,
            status="succeeded",
            summary="Produced the final ranked recommendation package.",
            inputs={"student_id": student_id},
            outputs={
                "mentor_count": len(list(recs.get("mentors") or [])),
                "project_count": len(list(recs.get("projects") or [])),
                "teammate_count": len(list(recs.get("teammates") or [])),
            },
        ),
    ]
```

- [ ] **Step 4: Wire trace in AgentCoreV2 after recommendation execution**

In `progrec_agent/agent_core_v2.py`, import:

```python
from progrec_agent.runtime.skill_trace import recommendation_trace, trace_entry
```

After `working.execution_context.last_result = result` in both recommendation branches, add:

```python
            working.skill_trace = recommendation_trace(result)
```

For validation branch, after `payload = ...`, add:

```python
            working.skill_trace = [
                trace_entry(
                    skill_id="/academic-graph",
                    tool_name="validate_resources",
                    status="succeeded",
                    summary=f"Validated resources for {payload['mode']} mode.",
                    inputs={"mode": payload["mode"]},
                    outputs=payload,
                )
            ]
```

- [ ] **Step 5: Run skill trace test**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2.TestAgentCoreV2.test_recommendation_result_records_real_skill_trace -v
```

Expected: PASS after AgentCoreV2 is wired in Task 9. If it still uses the legacy parser, apply Task 9 before completing this task.

- [ ] **Step 6: Commit skill trace helpers**

```bash
git add \
  progrec_agent/runtime/skill_trace.py \
  progrec_agent/agent_core_v2.py \
  progrec_agent/tests/test_agent_core_v2.py
git commit -m "feat: record real chat skill trace"
```

Expected: commit contains trace helper, AgentCoreV2 trace wiring, and tests.

---

### Task 9: Wire Skill-Aware Parser And Planner Into AgentCoreV2

**Files:**
- Modify: `progrec_agent/agent_core_v2.py`
- Modify: `progrec_agent/planning/actions.py`
- Modify: `progrec_agent/planning/planner_v2.py`
- Modify: `progrec_agent/response/replies.py`
- Modify: `progrec_agent/tests/test_agent_core_v2.py`
- Modify: `progrec_agent/tests/test_planner_v2.py`

- [ ] **Step 1: Add failing planner tests**

Append to `progrec_agent/tests/test_planner_v2.py`:

```python
    def test_out_of_scope_plan_refuses(self) -> None:
        state = DialogState(task="out_of_scope", missing_slots=[])

        plan = build_execution_plan(state)

        self.assertEqual(plan.action, "refuse_out_of_scope")

    def test_meta_question_plan_answers_without_recommendation_runtime(self) -> None:
        state = DialogState(
            task="answer_meta_question",
            missing_slots=[],
            skill_trace=[{"skill_id": "/mentor-discovery", "summary": "Ranked mentor candidates."}],
        )

        plan = build_execution_plan(state)

        self.assertEqual(plan.action, "answer_meta_question")

    def test_explain_requires_existing_result(self) -> None:
        state = DialogState(task="explain_recommendation", missing_slots=[])

        plan = build_execution_plan(state)

        self.assertEqual(plan.action, "await_clarification")
```

- [ ] **Step 2: Add failing AgentCoreV2 skill-aware test**

Append to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_skill_aware_parser_runs_complete_temporary_profile_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            runtime.run_recommendation_for_profile.return_value = {
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
                "skill4_result": {"target_student_id": "chat-temp-1"},
                "skill5_result": {
                    "recommendations": {"mentors": [{"rank": 1}], "projects": [], "teammates": []}
                },
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP", "provenance": "explicit"},
                    "program_type": {"value": "undergraduate research", "provenance": "explicit"},
                    "experience_level": {"value": "intermediate", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.96,
                "reasoning_summary": "Complete temporary mentor request.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, state = core.handle_message(DialogState(), "Find an NLP mentor for undergraduate research.")

            self.assertIn("recommendation pipeline", reply)
            self.assertEqual(state.task, "recommend_temporary_profile")
            runtime.run_recommendation_for_profile.assert_called_once()
            self.assertTrue(state.skill_trace)
```

- [ ] **Step 3: Run planner and core tests to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_planner_v2 \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: FAIL because planner actions and AgentCoreV2 are not wired for skill-aware frames.

- [ ] **Step 4: Extend ExecutionPlanV2 if needed**

If `progrec_agent/planning/actions.py` has only `action` and `arguments`, keep it unchanged. If it lacks default arguments, update it to:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExecutionPlanV2:
    action: str
    arguments: dict[str, object] = field(default_factory=dict)
```

- [ ] **Step 5: Update planner actions**

Modify `progrec_agent/planning/planner_v2.py`:

```python
from __future__ import annotations

from progrec_agent.planning.actions import ExecutionPlanV2


def build_execution_plan(state) -> ExecutionPlanV2:
    if state.task == "out_of_scope":
        return ExecutionPlanV2(action="refuse_out_of_scope")
    if state.task == "answer_meta_question":
        return ExecutionPlanV2(action="answer_meta_question")
    if state.task in {"inspect_recommendation", "explain_recommendation"} and not state.execution_context.last_result:
        return ExecutionPlanV2(action="await_clarification")
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
    if state.task == "explain_recommendation":
        return ExecutionPlanV2(
            action="explain_ranked_entity",
            arguments={
                "entity_type": state.resolved_slots.get("entity_type", "mentor"),
                "rank": state.resolved_slots.get("rank", 1),
            },
        )
    if state.task == "validate_resources":
        return ExecutionPlanV2(action="validate_resources", arguments={"mode": state.resolved_slots["mode"]})
    return ExecutionPlanV2(action="refuse_out_of_scope")
```

- [ ] **Step 6: Add response helpers**

Append to `progrec_agent/response/replies.py`:

```python
def render_meta_answer(state) -> str:
    trace = list(state.skill_trace or [])
    if not trace:
        return "I have not run any ProgRec skills in this chat yet."
    summaries = [f"{entry.get('skill_id')}: {entry.get('summary')}" for entry in trace]
    return "I used these ProgRec skills: " + " ".join(summaries)


def render_scope_refusal() -> str:
    return (
        "That is outside ProgRec's recommendation scope. "
        "I can help with mentor, project, teammate, ranking explanation, or resource validation questions."
    )
```

- [ ] **Step 7: Wire AgentCoreV2 to skill-aware parser**

Modify `progrec_agent/agent_core_v2.py` imports:

```python
from progrec_agent.dialog.merge import merge_intent_frame, merge_skill_frame
from progrec_agent.nlu.parser import parse_skill_aware_user_message
from progrec_agent.response.replies import (
    render_clarification,
    render_execution_blocker,
    render_meta_answer,
    render_ranked_entity,
    render_recommendation_summary,
    render_scope_refusal,
)
from progrec_agent.runtime.skill_trace import recommendation_trace, trace_entry
from progrec_agent.skill_catalog import build_skill_catalog
```

In `__init__`, add:

```python
        self.skill_catalog = build_skill_catalog(self.repo_root)
```

Replace the non-pending parse branch:

```python
            frame = parse_skill_aware_user_message(
                user_text,
                dialog_state=working,
                llm_client=self.llm_client,
                skill_catalog=self.skill_catalog,
            )
            working = merge_skill_frame(working, frame)
```

Keep `_normalize_recommendation_state()` after merge so pending-answer flows still normalize.

Add plan handlers before the final fallback:

```python
        if plan.action == "answer_meta_question":
            message = render_meta_answer(working)
            working.execution_context.last_turn_type = "meta_answer"
            working.execution_context.next_question = ""
            working.last_agent_turn = message
            return message, working
        if plan.action == "refuse_out_of_scope":
            message = render_scope_refusal()
            working.execution_context.last_turn_type = "refusal"
            working.execution_context.next_question = ""
            working.last_agent_turn = message
            return message, working
```

Add trace assignment after recommendation results:

```python
            working.skill_trace = recommendation_trace(result)
```

- [ ] **Step 8: Run planner and core tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_planner_v2 \
  progrec_agent.tests.test_agent_core_v2 \
  progrec_agent.tests.test_conversation_e2e_v2 \
  -v
```

Expected: PASS.

- [ ] **Step 9: Commit skill-aware AgentCoreV2 wiring**

```bash
git add \
  progrec_agent/agent_core_v2.py \
  progrec_agent/planning/actions.py \
  progrec_agent/planning/planner_v2.py \
  progrec_agent/response/replies.py \
  progrec_agent/tests/test_agent_core_v2.py \
  progrec_agent/tests/test_planner_v2.py
git commit -m "feat: wire skill-aware chat planner"
```

Expected: commit contains planner/core wiring only.

---

### Task 10: Return Real Skill Usage From Agent Runner And SSE

**Files:**
- Modify: `progrec_service/runtime/agent_v2_runner.py`
- Modify: `progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Add failing agent runner test**

Append to `progrec_service/tests/test_agent_stream.py`:

```python
    def test_runner_uses_state_skill_trace_in_structured_result(self) -> None:
        class _RuntimeContext:
            model = "demo-model"
            api_key = "sk-test"
            base_url = "https://api.openai.com/v1"

        with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
            llm_client.return_value.complete_json.return_value = {
                "turn_type": "domain_task",
                "task": "recommend_temporary_profile",
                "target_types": ["mentor"],
                "slots": {
                    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
                    "research_topic": {"value": "NLP", "provenance": "explicit"},
                    "program_type": {"value": "undergraduate research", "provenance": "explicit"},
                    "experience_level": {"value": "intermediate", "provenance": "explicit"},
                },
                "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
                "candidate_tools": ["recommend_full_pipeline"],
                "missing_information": [],
                "confidence": 0.96,
                "reasoning_summary": "Complete temporary request.",
            }
            with patch(
                "progrec_agent.runtime.recommendation_runtime.run_recommendation_for_profile",
                return_value={
                    "student_profile": {"student_id": "chat-temp-1"},
                    "skill3_result": {"student_id": "chat-temp-1", "mentor_candidates": [{"mentor_id": "m1"}]},
                    "skill4_result": {"target_student_id": "chat-temp-1"},
                    "skill5_result": {
                        "recommendations": {"mentors": [{"rank": 1}], "projects": [], "teammates": []}
                    },
                },
            ):
                result = agent_v2_runner.run_agent_turn(
                    repo_root=__import__("pathlib").Path("."),
                    dialog_state_payload={},
                    runtime_context=_RuntimeContext(),
                    user_text="Find an NLP mentor.",
                )

        skill_usage = result["structured_result"]["skill_usage"]
        self.assertTrue(skill_usage)
        self.assertIn("/mentor-discovery", [entry["skill_id"] for entry in skill_usage])
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_stream.TestAgentStream.test_runner_uses_state_skill_trace_in_structured_result -v
```

Expected: FAIL because `agent_v2_runner.py` still fabricates skill usage or ignores `state.skill_trace`.

- [ ] **Step 3: Modify dialog state hydration**

In `progrec_service/runtime/agent_v2_runner.py`, update `_dialog_state_from_payload()` constructor call to include:

```python
        skill_trace=list(payload.get("skill_trace", []) or []),
        last_skill_plan=dict(payload.get("last_skill_plan", {}) or {}),
        last_result_summary=str(payload.get("last_result_summary", "")),
```

- [ ] **Step 4: Replace fabricated skill usage**

Remove `_recommendation_skill_usage()` or leave it unused. In `_structured_result_from_state()`, replace:

```python
        "skill_usage": _recommendation_skill_usage(state) if turn_type == "recommendation_result" else [],
```

with:

```python
        "skill_usage": list(state.skill_trace or []),
```

- [ ] **Step 5: Update tests that expected fabricated skill usage**

In `progrec_service/tests/test_agent_stream.py`, keep existing SSE tests that patch `run_agent_turn()` with explicit `skill_usage`. They should still pass because SSE uses the provided structured result.

- [ ] **Step 6: Run agent stream tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_stream -v
```

Expected: PASS.

- [ ] **Step 7: Commit real skill usage runner**

```bash
git add progrec_service/runtime/agent_v2_runner.py progrec_service/tests/test_agent_stream.py
git commit -m "feat: stream real chat skill usage"
```

Expected: commit contains runner and service test changes.

---

### Task 11: Add Follow-Up, Explanation, Validation, And Out-Of-Scope Coverage

**Files:**
- Modify: `progrec_agent/tests/test_agent_core_v2.py`
- Modify: `progrec_agent/tests/test_conversation_e2e_v2.py`
- Modify: `progrec_agent/agent_core_v2.py`
- Modify: `progrec_agent/response/replies.py`

- [ ] **Step 1: Add follow-up tests**

Append to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_meta_question_answers_from_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "meta_question",
                "task": "answer_meta_question",
                "target_types": [],
                "slots": {},
                "candidate_skills": [],
                "candidate_tools": [],
                "missing_information": [],
                "confidence": 0.95,
                "reasoning_summary": "User asked which skills were used.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            state = DialogState(skill_trace=[{"skill_id": "/mentor-discovery", "summary": "Ranked mentor candidates."}])

            reply, updated = core.handle_message(state, "Which skills did you use?")

            self.assertIn("/mentor-discovery", reply)
            self.assertEqual(updated.execution_context.last_turn_type, "meta_answer")

    def test_weather_question_refuses_without_running_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            runtime = Mock()
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "out_of_scope",
                "task": "out_of_scope",
                "target_types": [],
                "slots": {},
                "candidate_skills": [],
                "candidate_tools": [],
                "missing_information": [],
                "confidence": 0.99,
                "reasoning_summary": "Weather is outside ProgRec.",
            }
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)

            reply, updated = core.handle_message(DialogState(), "What is the weather today?")

            self.assertIn("outside ProgRec", reply)
            runtime.run_recommendation_for_profile.assert_not_called()
            self.assertEqual(updated.execution_context.last_turn_type, "refusal")
```

- [ ] **Step 2: Add validation test**

Append to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_validate_resources_records_graph_skill_trace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            validation = Mock()
            validation.validate_resources.return_value = {
                "mode": "graph",
                "students_path": "students.json",
                "mentors_path": "mentors.json",
                "graph_path": "academic_graph.json",
            }
            llm = Mock()
            llm.complete_json.return_value = {
                "turn_type": "resource_validation",
                "task": "validate_resources",
                "target_types": [],
                "slots": {"mode": {"value": "graph", "provenance": "explicit"}},
                "candidate_skills": ["/academic-graph"],
                "candidate_tools": ["debug_graph_mode"],
                "missing_information": [],
                "confidence": 0.92,
                "reasoning_summary": "User wants graph resources validated.",
            }
            core = AgentCoreV2(
                repo_root=Path("."),
                temp_dir=Path(td),
                llm_client=llm,
                validation_runtime=validation,
            )

            reply, state = core.handle_message(DialogState(), "Validate graph mode resources.")

            self.assertIn("validated", reply.lower())
            self.assertEqual(state.skill_trace[0]["skill_id"], "/academic-graph")
```

- [ ] **Step 3: Run follow-up tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 -v
```

Expected: PASS after missing handlers are added.

- [ ] **Step 4: Implement missing handlers**

If meta/refusal/validation handlers are missing from `AgentCoreV2`, add the handlers from Task 9 and Task 8. If validation trace is missing, add:

```python
            working.skill_trace = [
                trace_entry(
                    skill_id="/academic-graph",
                    tool_name="validate_resources",
                    status="succeeded",
                    summary=f"Validated resources for {payload['mode']} mode.",
                    inputs={"mode": payload["mode"]},
                    outputs=payload,
                )
            ]
```

- [ ] **Step 5: Run conversation tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_agent_core_v2 \
  progrec_agent.tests.test_conversation_e2e_v2 \
  -v
```

Expected: PASS.

- [ ] **Step 6: Commit follow-up coverage**

```bash
git add \
  progrec_agent/agent_core_v2.py \
  progrec_agent/response/replies.py \
  progrec_agent/tests/test_agent_core_v2.py \
  progrec_agent/tests/test_conversation_e2e_v2.py
git commit -m "test: cover skill-aware chat followups"
```

Expected: commit contains follow-up handlers and tests.

---

### Task 12: Full Verification

**Files:**
- No planned file changes.

- [ ] **Step 1: Run progrec_agent unit tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest discover -s progrec_agent/tests -v
```

Expected: PASS. If failures occur, fix only files touched by this plan and rerun.

- [ ] **Step 2: Run service agent stream tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_stream -v
```

Expected: PASS.

- [ ] **Step 3: Run focused backend agent route tests**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_routes -v
```

Expected: PASS.

- [ ] **Step 4: Run final status check**

Run:

```bash
git status --short
```

Expected: only unrelated pre-existing modified files remain unstaged, or the working tree is clean if those were handled outside this plan.

- [ ] **Step 5: Commit verification-only fixes if any were needed**

If verification required small fixes, stage only those files:

```bash
git add <exact-fixed-file-paths>
git commit -m "fix: stabilize skill-aware chat tests"
```

Expected: commit succeeds. If no fixes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage:
  - Skill catalog: Task 2.
  - Skill-aware parser/schema: Tasks 3 and 5.
  - Pending-answer parsing: Task 4.
  - Dialog state and planner: Tasks 6 and 9.
  - Temporary profile standardization: Task 7.
  - Real skill trace and service payloads: Tasks 8 and 10.
  - Follow-ups, validation, meta, out-of-scope: Task 11.
  - Verification: Task 12.
- Type consistency:
  - `SkillCard`, `SkillCatalog`, `SkillAwareFrame`, and `SlotValue` names are consistent across tests and implementation snippets.
  - `skill_trace`, `last_skill_plan`, and `last_result_summary` are `DialogState` fields and are hydrated by `agent_v2_runner.py`.
  - Planner actions use `ExecutionPlanV2(action, arguments)`.
- Safety:
  - No plan step gives the LLM shell access.
  - Unknown tool and skill names are rejected by `validate_skill_frame_payload()`.
  - Rebuild actions remain behind existing tool registry confirmation behavior.
