# Skill Contract Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a thin-wrapper Skill Contract Layer so the ProgRec chat agent reasons over structured action and inspect capabilities, returns stable result references, and can answer follow-up inspection requests without rerunning recommendation flows.

**Architecture:** Add contract primitives, a capability registry, thin skill adapters, and result inspectors in front of the existing Skill 1-5 runtimes. Keep the current internal recommendation logic intact in phase 1, but change the chat planner and executor to work with capability ids and session-scoped result references instead of raw payload guesses.

**Tech Stack:** Python 3.12, stdlib `unittest`, dataclasses, existing `progrec_agent` runtime modules, existing `progrec_service` serialization path, current LLM planner contract.

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

- `progrec_agent/contracts/__init__.py`: Package exports for capability and result-ref primitives.
- `progrec_agent/contracts/capability_schema.py`: Dataclasses and helpers for `CapabilityContract`, `CapabilityInput`, and planner-facing summaries.
- `progrec_agent/contracts/result_refs.py`: Result-ref dataclasses, in-memory session registry helpers, and serialization helpers.
- `progrec_agent/contracts/registry.py`: Central capability registry builder for all phase-1 action and inspect capabilities.
- `progrec_agent/capability_adapters/__init__.py`: Package exports for phase-1 adapters.
- `progrec_agent/capability_adapters/student_profiling.py`: Thin wrappers for Skill 1 action and inspect capabilities.
- `progrec_agent/capability_adapters/academic_graph.py`: Thin wrappers for Skill 2 validation and resource inspection capabilities.
- `progrec_agent/capability_adapters/mentor_discovery.py`: Thin wrappers for Skill 3 action capability.
- `progrec_agent/capability_adapters/project_teammate_discovery.py`: Thin wrappers for Skill 4 project and teammate action capabilities.
- `progrec_agent/capability_adapters/social_ranking.py`: Thin wrappers for Skill 5 bundle rerank and report-export capabilities.
- `progrec_agent/inspectors/__init__.py`: Package exports for result inspectors.
- `progrec_agent/inspectors/mentor_result_inspector.py`: Inspect helpers for list/get/explain mentor follow-ups.
- `progrec_agent/inspectors/project_result_inspector.py`: Inspect helpers for project follow-ups.
- `progrec_agent/inspectors/teammate_result_inspector.py`: Inspect helpers for teammate follow-ups.
- `progrec_agent/inspectors/bundle_result_inspector.py`: Inspect helpers for bundle-level follow-ups and report metadata.
- `progrec_agent/tests/test_capability_schema.py`: Unit tests for capability dataclasses and planner prompt formatting.
- `progrec_agent/tests/test_result_refs.py`: Unit tests for result-ref creation, follow-up metadata, and registry lookup.
- `progrec_agent/tests/test_contract_registry.py`: Unit tests for the phase-1 capability registry.
- `progrec_agent/tests/test_result_inspectors.py`: Unit tests for mentor, project, teammate, and bundle inspectors.

Modify:

- `progrec_agent/chat_tool_registry.py`: Convert the current action-only registry into a compatibility facade over the new capability registry.
- `progrec_agent/agent_planner.py`: Feed planner prompt context from capability contracts and include result-ref state in the planner snapshot.
- `progrec_agent/runtime/chat_tool_executor.py`: Replace tool-specific branching with capability-adapter dispatch and result-ref creation.
- `progrec_agent/dialog/state.py`: Extend `ExecutionContext` with session result-ref state needed for follow-up inspection.
- `progrec_agent/agent_core_v2.py`: Record capability results, resolve inspect follow-ups, and stop rerunning recommendations for simple inspection requests.
- `progrec_service/runtime/agent_v2_runner.py`: Serialize and deserialize the new execution-context fields and expose latest result refs in `structured_result`.
- `progrec_agent/tests/test_chat_tool_registry.py`: Update registry expectations to cover action and inspect capabilities.
- `progrec_agent/tests/test_chat_tool_executor.py`: Update executor tests to assert result-ref payloads and adapter dispatch.
- `progrec_agent/tests/test_agent_planner.py`: Add planner-context and allowed-capability validation tests.
- `progrec_agent/tests/test_agent_core_v2.py`: Add follow-up inspection regression tests.
- `progrec_agent/tests/test_conversation_e2e_v2.py`: Add end-to-end dialog coverage for inspection and continuation flows.

---

### Task 1: Add Contract Primitives And Result-Ref Foundations

**Files:**
- Create: `progrec_agent/contracts/__init__.py`
- Create: `progrec_agent/contracts/capability_schema.py`
- Create: `progrec_agent/contracts/result_refs.py`
- Create: `progrec_agent/tests/test_capability_schema.py`
- Create: `progrec_agent/tests/test_result_refs.py`

- [ ] **Step 1: Write the failing contract tests**

Create `progrec_agent/tests/test_capability_schema.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.contracts.capability_schema import CapabilityContract, CapabilityInput


class TestCapabilitySchema(unittest.TestCase):
    def test_action_contract_formats_prompt_context(self) -> None:
        contract = CapabilityContract(
            capability_id="/mentor-discovery.recommend_mentors",
            kind="action",
            owner_skill="/mentor-discovery",
            when_to_use="Use when a student profile is ready and the user wants mentor recommendations.",
            requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
            returns="mentor_result",
            can_follow=["student_profile"],
            followups=["/mentor-discovery.get_mentor_by_rank"],
            failure_modes=["missing_profile"],
            executor_binding="mentor_discovery.run_recommend_mentors",
        )

        prompt_line = contract.to_prompt_block()

        self.assertIn("/mentor-discovery.recommend_mentors", prompt_line)
        self.assertIn("kind: action", prompt_line)
        self.assertIn("student_profile_ref", prompt_line)


if __name__ == "__main__":
    unittest.main()
```

Create `progrec_agent/tests/test_result_refs.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.contracts.result_refs import ResultReference, ResultRegistry


class TestResultRefs(unittest.TestCase):
    def test_registry_tracks_latest_refs_by_result_type(self) -> None:
        registry = ResultRegistry()
        mentor_ref = ResultReference(
            result_ref="rr_mentor_001",
            result_type="mentor_result",
            owner_skill="/mentor-discovery",
            session_id="sess_1",
            input_refs=["sp_001"],
            summary={"count": 2, "top_ids": ["m1", "m2"]},
            followups=["/mentor-discovery.get_mentor_by_rank"],
            payload={"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]}},
        )

        registry.store(mentor_ref)

        self.assertEqual(registry.latest_ref("mentor_result"), "rr_mentor_001")
        self.assertEqual(registry.get("rr_mentor_001").summary["count"], 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_capability_schema \
  progrec_agent.tests.test_result_refs \
  -v
```

Expected: FAIL with `ModuleNotFoundError` for `progrec_agent.contracts`.

- [ ] **Step 3: Implement the minimal contract and result-ref modules**

Create `progrec_agent/contracts/capability_schema.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityInput:
    name: str
    value_type: str
    required: bool = True


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    kind: str
    owner_skill: str
    when_to_use: str
    requires: list[CapabilityInput]
    returns: str
    can_follow: list[str] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    executor_binding: str = ""

    def to_prompt_block(self) -> str:
        requires = ", ".join(
            f"{item.name}:{item.value_type}{'' if item.required else '?'}" for item in self.requires
        ) or "none"
        followups = ", ".join(self.followups) or "none"
        return "\n".join(
            [
                f"capability: {self.capability_id}",
                f"kind: {self.kind}",
                f"owner_skill: {self.owner_skill}",
                f"requires: {requires}",
                f"returns: {self.returns}",
                f"followups: {followups}",
                f"when_to_use: {self.when_to_use}",
            ]
        )
```

Create `progrec_agent/contracts/result_refs.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResultReference:
    result_ref: str
    result_type: str
    owner_skill: str
    session_id: str
    input_refs: list[str]
    summary: dict[str, object]
    followups: list[str]
    payload: dict[str, object] = field(default_factory=dict)


class ResultRegistry:
    def __init__(self) -> None:
        self._refs: dict[str, ResultReference] = {}
        self._latest_by_type: dict[str, str] = {}

    def store(self, result: ResultReference) -> None:
        self._refs[result.result_ref] = result
        self._latest_by_type[result.result_type] = result.result_ref

    def get(self, result_ref: str) -> ResultReference:
        return self._refs[result_ref]

    def latest_ref(self, result_type: str) -> str | None:
        return self._latest_by_type.get(result_type)
```

Create `progrec_agent/contracts/__init__.py`:

```python
from progrec_agent.contracts.capability_schema import CapabilityContract, CapabilityInput
from progrec_agent.contracts.result_refs import ResultReference, ResultRegistry

__all__ = [
    "CapabilityContract",
    "CapabilityInput",
    "ResultReference",
    "ResultRegistry",
]
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_capability_schema \
  progrec_agent.tests.test_result_refs \
  -v
```

Expected: PASS for both test modules.

- [ ] **Step 5: Commit the contract foundation**

```bash
git add \
  progrec_agent/contracts/__init__.py \
  progrec_agent/contracts/capability_schema.py \
  progrec_agent/contracts/result_refs.py \
  progrec_agent/tests/test_capability_schema.py \
  progrec_agent/tests/test_result_refs.py
git commit -m "feat: add skill contract primitives"
```

Expected: commit succeeds with only the new contract files staged.

---

### Task 2: Add The Capability Registry And Planner-Facing Contract Context

**Files:**
- Create: `progrec_agent/contracts/registry.py`
- Create: `progrec_agent/capability_adapters/__init__.py`
- Create: `progrec_agent/capability_adapters/student_profiling.py`
- Create: `progrec_agent/capability_adapters/academic_graph.py`
- Create: `progrec_agent/capability_adapters/mentor_discovery.py`
- Create: `progrec_agent/capability_adapters/project_teammate_discovery.py`
- Create: `progrec_agent/capability_adapters/social_ranking.py`
- Create: `progrec_agent/tests/test_contract_registry.py`
- Modify: `progrec_agent/chat_tool_registry.py`
- Modify: `progrec_agent/agent_planner.py`
- Modify: `progrec_agent/tests/test_chat_tool_registry.py`
- Modify: `progrec_agent/tests/test_agent_planner.py`

- [ ] **Step 1: Write failing registry and planner-context tests**

Create `progrec_agent/tests/test_contract_registry.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.contracts.registry import get_capability, list_capabilities, planner_capability_context


class TestContractRegistry(unittest.TestCase):
    def test_registry_exposes_action_and_inspect_capabilities(self) -> None:
        capability_ids = [item.capability_id for item in list_capabilities()]

        self.assertIn("/student-profiling.build_temporary_profile", capability_ids)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", capability_ids)
        self.assertIn("/project-teammate-discovery.recommend_projects", capability_ids)
        self.assertIn("/social-ranking.rerank_bundle", capability_ids)

    def test_planner_context_mentions_followups(self) -> None:
        context = planner_capability_context()

        self.assertIn("/mentor-discovery.recommend_mentors", context)
        self.assertIn("/mentor-discovery.get_mentor_by_rank", context)
        self.assertIn("followups", context)


if __name__ == "__main__":
    unittest.main()
```

Update the imports at the top of `progrec_agent/tests/test_agent_planner.py` and append this test:

```python
from progrec_agent.agent_planner import AgentPlanner, _planner_state_snapshot

    def test_state_snapshot_exposes_latest_result_refs(self) -> None:
        state = DialogState()
        state.execution_context.latest_result_refs = {"mentor_result": "rr_mentor_001"}

        snapshot = _planner_state_snapshot(state)

        self.assertEqual(snapshot["latest_result_refs"]["mentor_result"], "rr_mentor_001")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_contract_registry \
  progrec_agent.tests.test_chat_tool_registry \
  progrec_agent.tests.test_agent_planner \
  -v
```

Expected: FAIL because `contracts.registry` does not exist and the planner snapshot has no `latest_result_refs`.

- [ ] **Step 3: Implement the registry, adapter skeletons, and compatibility facade**

Create `progrec_agent/contracts/registry.py`:

```python
from __future__ import annotations

from progrec_agent.contracts.capability_schema import CapabilityContract, CapabilityInput


_CAPABILITIES = {
    "/student-profiling.build_temporary_profile": CapabilityContract(
        capability_id="/student-profiling.build_temporary_profile",
        kind="action",
        owner_skill="/student-profiling",
        when_to_use="Use when the user has provided background information and the chat needs a temporary normalized profile.",
        requires=[CapabilityInput(name="profile_context", value_type="object", required=True)],
        returns="student_profile",
        followups=["/student-profiling.show_profile_summary", "/mentor-discovery.recommend_mentors"],
        executor_binding="student_profiling.build_temporary_profile",
    ),
    "/mentor-discovery.recommend_mentors": CapabilityContract(
        capability_id="/mentor-discovery.recommend_mentors",
        kind="action",
        owner_skill="/mentor-discovery",
        when_to_use="Use when a temporary or persisted student profile is available and the user wants mentor recommendations.",
        requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
        returns="mentor_result",
        can_follow=["student_profile"],
        followups=[
            "/mentor-discovery.list_mentors",
            "/mentor-discovery.get_mentor_by_rank",
            "/mentor-discovery.explain_mentor_match",
            "/project-teammate-discovery.recommend_projects",
            "/project-teammate-discovery.recommend_teammates",
        ],
        executor_binding="mentor_discovery.recommend_mentors",
    ),
    "/mentor-discovery.get_mentor_by_rank": CapabilityContract(
        capability_id="/mentor-discovery.get_mentor_by_rank",
        kind="inspect",
        owner_skill="/mentor-discovery",
        when_to_use="Use when the user refers to a ranked mentor from the latest mentor result.",
        requires=[
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="mentor_result",
        can_follow=["mentor_result"],
        executor_binding="mentor_result_inspector.get_by_rank",
    ),
    "/project-teammate-discovery.recommend_projects": CapabilityContract(
        capability_id="/project-teammate-discovery.recommend_projects",
        kind="action",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user wants project recommendations after a profile or mentor result already exists.",
        requires=[
            CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True),
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=False),
        ],
        returns="project_result",
        can_follow=["student_profile", "mentor_result"],
        followups=["/project-teammate-discovery.get_project_by_rank", "/project-teammate-discovery.explain_project_match"],
        executor_binding="project_teammate_discovery.recommend_projects",
    ),
    "/project-teammate-discovery.recommend_teammates": CapabilityContract(
        capability_id="/project-teammate-discovery.recommend_teammates",
        kind="action",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user wants teammate recommendations after a profile or mentor result already exists.",
        requires=[
            CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True),
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=False),
        ],
        returns="teammate_result",
        can_follow=["student_profile", "mentor_result"],
        followups=["/project-teammate-discovery.get_teammate_by_rank", "/project-teammate-discovery.explain_teammate_match"],
        executor_binding="project_teammate_discovery.recommend_teammates",
    ),
    "/social-ranking.rerank_bundle": CapabilityContract(
        capability_id="/social-ranking.rerank_bundle",
        kind="action",
        owner_skill="/social-ranking",
        when_to_use="Use when the user wants a combined recommendation bundle reranked across mentors, projects, and teammates.",
        requires=[
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
        ],
        returns="bundle_result",
        can_follow=["mentor_result", "project_result", "teammate_result"],
        followups=["/social-ranking.show_bundle_summary", "/social-ranking.export_report"],
        executor_binding="social_ranking.rerank_bundle",
    ),
    "/academic-graph.validate_graph_resources": CapabilityContract(
        capability_id="/academic-graph.validate_graph_resources",
        kind="action",
        owner_skill="/academic-graph",
        when_to_use="Use when the runtime needs to validate graph resources or student-id namespace alignment.",
        requires=[CapabilityInput(name="mode", value_type="string", required=True)],
        returns="resource_validation",
        followups=["/academic-graph.show_resource_status", "/academic-graph.list_available_student_spaces"],
        executor_binding="academic_graph.validate_graph_resources",
    ),
    "/student-profiling.show_profile_summary": CapabilityContract(
        capability_id="/student-profiling.show_profile_summary",
        kind="inspect",
        owner_skill="/student-profiling",
        when_to_use="Use when the user asks to see the current normalized profile.",
        requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
        returns="student_profile",
        can_follow=["student_profile"],
        executor_binding="student_profiling.show_profile_summary",
    ),
}


def list_capabilities() -> list[CapabilityContract]:
    return list(_CAPABILITIES.values())


def get_capability(capability_id: str) -> CapabilityContract:
    return _CAPABILITIES[capability_id]


def allowed_capability_ids() -> set[str]:
    return set(_CAPABILITIES)


def planner_capability_context() -> str:
    return "\n\n".join(item.to_prompt_block() for item in list_capabilities())
```

In the same file, add the remaining phase-1 entries before moving on so the registry covers the full Scheme B surface:

```python
_CAPABILITIES.update(
    {
        "/student-profiling.update_profile_context": CapabilityContract(
            capability_id="/student-profiling.update_profile_context",
            kind="action",
            owner_skill="/student-profiling",
            when_to_use="Use when the user provides new profile details after an earlier clarification.",
            requires=[CapabilityInput(name="profile_context", value_type="object", required=True)],
            returns="student_profile",
            can_follow=["student_profile"],
            followups=["/student-profiling.show_profile_summary", "/student-profiling.explain_profile_fields"],
            executor_binding="student_profiling.update_profile_context",
        ),
        "/student-profiling.explain_profile_fields": CapabilityContract(
            capability_id="/student-profiling.explain_profile_fields",
            kind="inspect",
            owner_skill="/student-profiling",
            when_to_use="Use when the user asks where the normalized profile fields came from.",
            requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
            returns="student_profile",
            can_follow=["student_profile"],
            executor_binding="student_profiling.explain_profile_fields",
        ),
        "/academic-graph.show_resource_status": CapabilityContract(
            capability_id="/academic-graph.show_resource_status",
            kind="inspect",
            owner_skill="/academic-graph",
            when_to_use="Use when the user asks which graph resources or namespaces are active.",
            requires=[CapabilityInput(name="resource_validation_ref", value_type="result_ref", required=True)],
            returns="resource_validation",
            can_follow=["resource_validation"],
            executor_binding="academic_graph.show_resource_status",
        ),
        "/academic-graph.list_available_student_spaces": CapabilityContract(
            capability_id="/academic-graph.list_available_student_spaces",
            kind="inspect",
            owner_skill="/academic-graph",
            when_to_use="Use when the user asks which student-id spaces are available in the current resources.",
            requires=[CapabilityInput(name="resource_validation_ref", value_type="result_ref", required=True)],
            returns="resource_validation",
            can_follow=["resource_validation"],
            executor_binding="academic_graph.list_available_student_spaces",
        ),
        "/mentor-discovery.list_mentors": CapabilityContract(
            capability_id="/mentor-discovery.list_mentors",
            kind="inspect",
            owner_skill="/mentor-discovery",
            when_to_use="Use when the user asks to list the current mentor results without expanding a single mentor.",
            requires=[CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True)],
            returns="mentor_result",
            can_follow=["mentor_result"],
            executor_binding="mentor_result_inspector.list_mentors",
        ),
        "/mentor-discovery.explain_mentor_match": CapabilityContract(
            capability_id="/mentor-discovery.explain_mentor_match",
            kind="inspect",
            owner_skill="/mentor-discovery",
            when_to_use="Use when the user asks why a mentor was recommended.",
            requires=[
                CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
                CapabilityInput(name="rank", value_type="int", required=True),
            ],
            returns="mentor_result",
            can_follow=["mentor_result"],
            executor_binding="mentor_result_inspector.explain_mentor_match",
        ),
        "/project-teammate-discovery.get_project_by_rank": CapabilityContract(
            capability_id="/project-teammate-discovery.get_project_by_rank",
            kind="inspect",
            owner_skill="/project-teammate-discovery",
            when_to_use="Use when the user asks to inspect a specific ranked project candidate.",
            requires=[
                CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
                CapabilityInput(name="rank", value_type="int", required=True),
            ],
            returns="project_result",
            can_follow=["project_result"],
            executor_binding="project_result_inspector.get_project_by_rank",
        ),
        "/project-teammate-discovery.explain_project_match": CapabilityContract(
            capability_id="/project-teammate-discovery.explain_project_match",
            kind="inspect",
            owner_skill="/project-teammate-discovery",
            when_to_use="Use when the user asks why a project was recommended.",
            requires=[
                CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
                CapabilityInput(name="rank", value_type="int", required=True),
            ],
            returns="project_result",
            can_follow=["project_result"],
            executor_binding="project_result_inspector.explain_project_match",
        ),
        "/project-teammate-discovery.get_teammate_by_rank": CapabilityContract(
            capability_id="/project-teammate-discovery.get_teammate_by_rank",
            kind="inspect",
            owner_skill="/project-teammate-discovery",
            when_to_use="Use when the user asks to inspect a specific ranked teammate candidate.",
            requires=[
                CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
                CapabilityInput(name="rank", value_type="int", required=True),
            ],
            returns="teammate_result",
            can_follow=["teammate_result"],
            executor_binding="teammate_result_inspector.get_teammate_by_rank",
        ),
        "/project-teammate-discovery.explain_teammate_match": CapabilityContract(
            capability_id="/project-teammate-discovery.explain_teammate_match",
            kind="inspect",
            owner_skill="/project-teammate-discovery",
            when_to_use="Use when the user asks why a teammate was recommended.",
            requires=[
                CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
                CapabilityInput(name="rank", value_type="int", required=True),
            ],
            returns="teammate_result",
            can_follow=["teammate_result"],
            executor_binding="teammate_result_inspector.explain_teammate_match",
        ),
        "/social-ranking.show_bundle_summary": CapabilityContract(
            capability_id="/social-ranking.show_bundle_summary",
            kind="inspect",
            owner_skill="/social-ranking",
            when_to_use="Use when the user asks for the current combined recommendation bundle summary.",
            requires=[CapabilityInput(name="bundle_result_ref", value_type="result_ref", required=True)],
            returns="bundle_result",
            can_follow=["bundle_result"],
            executor_binding="bundle_result_inspector.show_bundle_summary",
        ),
        "/social-ranking.export_report": CapabilityContract(
            capability_id="/social-ranking.export_report",
            kind="inspect",
            owner_skill="/social-ranking",
            when_to_use="Use when the user asks for a report artifact for the current recommendation bundle.",
            requires=[CapabilityInput(name="bundle_result_ref", value_type="result_ref", required=True)],
            returns="report_artifact",
            can_follow=["bundle_result"],
            executor_binding="bundle_result_inspector.export_report",
        ),
    }
)
```

Create `progrec_agent/capability_adapters/__init__.py`:

```python
from progrec_agent.capability_adapters import (
    academic_graph,
    mentor_discovery,
    project_teammate_discovery,
    social_ranking,
    student_profiling,
)

__all__ = [
    "academic_graph",
    "mentor_discovery",
    "project_teammate_discovery",
    "social_ranking",
    "student_profiling",
]
```

Create one skeleton adapter per skill, for example `progrec_agent/capability_adapters/student_profiling.py`:

```python
from __future__ import annotations


def build_temporary_profile(*, profile_context, executor_context):
    raise NotImplementedError


def update_profile_context(*, profile_context, executor_context):
    raise NotImplementedError
```

Create `progrec_agent/capability_adapters/mentor_discovery.py`:

```python
from __future__ import annotations


def recommend_mentors(*, student_profile_ref, top_k, executor_context):
    raise NotImplementedError
```

Create `progrec_agent/capability_adapters/project_teammate_discovery.py`:

```python
from __future__ import annotations


def recommend_projects(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context):
    raise NotImplementedError


def recommend_teammates(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context):
    raise NotImplementedError
```

Create `progrec_agent/capability_adapters/social_ranking.py`:

```python
from __future__ import annotations


def rerank_bundle(*, mentor_result_ref, project_result_ref, teammate_result_ref, executor_context):
    raise NotImplementedError
```

Update `progrec_agent/chat_tool_registry.py` so the public API stays stable but reads from the capability registry:

```python
from __future__ import annotations

from dataclasses import dataclass

from progrec_agent.contracts.registry import allowed_capability_ids, get_capability, list_capabilities, planner_capability_context


@dataclass(frozen=True)
class ChatTool:
    name: str
    skill_id: str
    description: str
    required_arguments: list[str]
    optional_arguments: list[str]
    allowed_targets: list[str]
    planner_notes: str


def list_chat_tools() -> list[ChatTool]:
    tools: list[ChatTool] = []
    for contract in list_capabilities():
        required_arguments = [item.name for item in contract.requires if item.required]
        optional_arguments = [item.name for item in contract.requires if not item.required]
        tools.append(
            ChatTool(
                name=contract.capability_id,
                skill_id=contract.owner_skill,
                description=contract.when_to_use,
                required_arguments=required_arguments,
                optional_arguments=optional_arguments,
                allowed_targets=[],
                planner_notes=f"kind={contract.kind}; returns={contract.returns}",
            )
        )
    return tools


def get_chat_tool(name: str) -> ChatTool:
    contract = get_capability(name)
    required_arguments = [item.name for item in contract.requires if item.required]
    optional_arguments = [item.name for item in contract.requires if not item.required]
    return ChatTool(
        name=contract.capability_id,
        skill_id=contract.owner_skill,
        description=contract.when_to_use,
        required_arguments=required_arguments,
        optional_arguments=optional_arguments,
        allowed_targets=[],
        planner_notes=f"kind={contract.kind}; returns={contract.returns}",
    )


def allowed_tool_names() -> set[str]:
    return allowed_capability_ids()


def planner_tool_context() -> str:
    return planner_capability_context()
```

Update `progrec_agent/agent_planner.py` to keep its current public behavior while reading capability context:

```python
from progrec_agent.chat_tool_registry import allowed_tool_names, planner_tool_context


def _planner_state_snapshot(state) -> dict[str, object]:
    return {
        "task": state.task,
        "goal": state.goal,
        "active_goal": state.active_goal,
        "goal_targets": list(state.goal_targets),
        "profile_context": dict(state.profile_context),
        "tool_results_summary": dict(state.tool_results_summary),
        "latest_result_refs": dict(state.execution_context.latest_result_refs),
        "active_result_ref": state.execution_context.active_result_ref,
        "last_shown_entities": dict(state.execution_context.last_shown_entities),
        "has_result": bool(state.execution_context.result_handle or state.execution_context.latest_result_refs),
    }
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_contract_registry \
  progrec_agent.tests.test_chat_tool_registry \
  progrec_agent.tests.test_agent_planner \
  -v
```

Expected: PASS, including registry coverage for inspect capability ids and planner snapshot coverage for latest result refs.

- [ ] **Step 5: Commit the registry layer**

```bash
git add \
  progrec_agent/contracts/registry.py \
  progrec_agent/capability_adapters/__init__.py \
  progrec_agent/capability_adapters/student_profiling.py \
  progrec_agent/capability_adapters/academic_graph.py \
  progrec_agent/capability_adapters/mentor_discovery.py \
  progrec_agent/capability_adapters/project_teammate_discovery.py \
  progrec_agent/capability_adapters/social_ranking.py \
  progrec_agent/chat_tool_registry.py \
  progrec_agent/agent_planner.py \
  progrec_agent/tests/test_contract_registry.py \
  progrec_agent/tests/test_chat_tool_registry.py \
  progrec_agent/tests/test_agent_planner.py
git commit -m "feat: add capability registry for skill contracts"
```

Expected: commit succeeds with only the registry and planner-context files staged.

---

### Task 3: Refactor The Chat Executor Around Capability Adapters

**Files:**
- Modify: `progrec_agent/runtime/chat_tool_executor.py`
- Modify: `progrec_agent/capability_adapters/student_profiling.py`
- Modify: `progrec_agent/capability_adapters/academic_graph.py`
- Modify: `progrec_agent/capability_adapters/mentor_discovery.py`
- Modify: `progrec_agent/capability_adapters/project_teammate_discovery.py`
- Modify: `progrec_agent/capability_adapters/social_ranking.py`
- Modify: `progrec_agent/tests/test_chat_tool_executor.py`

- [ ] **Step 1: Add failing executor tests for action capabilities and result refs**

Append these tests to `progrec_agent/tests/test_chat_tool_executor.py`:

```python
    def test_recommend_mentors_returns_result_reference_metadata(self) -> None:
        runtime = Mock()
        runtime.run_mentor_recommendation_for_profile.return_value = {
            "student_profile": {"student_id": "chat-temp-1"},
            "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]},
        }
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=runtime)
            result = executor.execute(
                "/mentor-discovery.recommend_mentors",
                {
                    "student_profile_ref": {
                        "result_ref": "sp_001",
                        "payload": {"profile": {"student_id": "chat-temp-1"}},
                    },
                    "top_k": 5,
                },
            )

        self.assertEqual(result.skill_id, "/mentor-discovery")
        self.assertEqual(result.payload["result_type"], "mentor_result")
        self.assertEqual(result.payload["summary"]["count"], 2)

    def test_build_temporary_profile_returns_student_profile_result_ref(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            executor = ChatToolExecutor(repo_root=Path("."), temp_dir=Path(td), recommendation_runtime=Mock())
            result = executor.execute(
                "/student-profiling.build_temporary_profile",
                {"profile_context": {"research_topic": "NLP", "program_type": "undergraduate"}},
            )

        self.assertEqual(result.payload["result_type"], "student_profile")
        self.assertEqual(result.payload["owner_skill"], "/student-profiling")
        self.assertIn("profile", result.payload["payload"])
```

- [ ] **Step 2: Run the executor tests to verify they fail**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_chat_tool_executor -v
```

Expected: FAIL because `/mentor-discovery.recommend_mentors` is not implemented and the executor still returns raw action payloads.

- [ ] **Step 3: Implement adapter-backed execution with result-ref creation**

Update `progrec_agent/runtime/chat_tool_executor.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

from progrec_agent.capability_adapters import mentor_discovery, project_teammate_discovery, social_ranking, student_profiling
from progrec_agent.contracts.registry import get_capability


@dataclass
class ToolExecutionResult:
    tool_name: str
    skill_id: str
    status: str
    summary: str
    payload: dict[str, Any]
```

Implement the adapter functions instead of leaving runtime logic inline. Update `progrec_agent/capability_adapters/mentor_discovery.py`:

```python
from __future__ import annotations


def recommend_mentors(*, student_profile_ref, top_k, executor_context):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    return executor_context.recommendation_runtime.run_mentor_recommendation_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        top_k=int(top_k or 5),
    )
```

Update `progrec_agent/capability_adapters/project_teammate_discovery.py`:

```python
from __future__ import annotations


def recommend_projects(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    mentor_payload = mentor_result_ref.get("payload") if isinstance(mentor_result_ref, dict) else None
    return executor_context.recommendation_runtime.run_project_recommendations_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        mentor_result=mentor_payload,
        top_k=int(top_k or 5),
    )


def recommend_teammates(*, student_profile_ref, mentor_result_ref=None, top_k=5, executor_context):
    profile = dict(student_profile_ref.get("payload", {}).get("profile") or {})
    mentor_payload = mentor_result_ref.get("payload") if isinstance(mentor_result_ref, dict) else None
    return executor_context.recommendation_runtime.run_teammate_recommendations_for_profile(
        repo_root=executor_context.repo_root,
        temp_dir=executor_context.temp_dir,
        profile=profile,
        mentor_result=mentor_payload,
        top_k=int(top_k or 5),
    )
```

Add a helper for action results in the same file:

```python
    def _make_result_payload(
        self,
        *,
        result_type: str,
        owner_skill: str,
        input_refs: list[str],
        summary: dict[str, object],
        followups: list[str],
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "result_ref": f"rr_{result_type}_{uuid.uuid4().hex[:8]}",
            "result_type": result_type,
            "owner_skill": owner_skill,
            "input_refs": list(input_refs),
            "summary": dict(summary),
            "followups": list(followups),
            "payload": dict(payload),
        }
```

Replace the action-specific branching with capability ids:

```python
        if tool_name == "/student-profiling.build_temporary_profile":
            profile_context = _coerce_profile_context(arguments["profile_context"])
            profile = standardize_temporary_profile(profile_context)
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/student-profiling",
                status="succeeded",
                summary="Built a temporary student profile from the conversation context.",
                payload=self._make_result_payload(
                    result_type="student_profile",
                    owner_skill="/student-profiling",
                    input_refs=[],
                    summary={"student_id": profile["student_id"]},
                    followups=[
                        "/student-profiling.show_profile_summary",
                        "/mentor-discovery.recommend_mentors",
                        "/project-teammate-discovery.recommend_projects",
                        "/project-teammate-discovery.recommend_teammates",
                    ],
                    payload={"profile": profile},
                ),
            )

        if tool_name == "/mentor-discovery.recommend_mentors":
            profile_ref = dict(arguments["student_profile_ref"])
            payload = mentor_discovery.recommend_mentors(
                student_profile_ref=profile_ref,
                top_k=arguments.get("top_k") or 5,
                executor_context=self,
            )
            candidates = list(dict(payload.get("skill3_result") or {}).get("mentor_candidates") or [])
            contract = get_capability(tool_name)
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/mentor-discovery",
                status="succeeded",
                summary="Ranked mentor candidates for the current student profile.",
                payload=self._make_result_payload(
                    result_type="mentor_result",
                    owner_skill="/mentor-discovery",
                    input_refs=[str(profile_ref.get("result_ref") or "")],
                    summary={"count": len(candidates), "top_ids": [item.get("mentor_id") for item in candidates[:3]]},
                    followups=contract.followups,
                    payload=dict(payload),
                ),
            )
```

Add matching branches for:

- `/project-teammate-discovery.recommend_projects`
- `/project-teammate-discovery.recommend_teammates`
- `/social-ranking.rerank_bundle`
- `/academic-graph.validate_graph_resources`

Each branch must return the same action envelope shape. Use this concrete example for the project branch:

```python
{
    "result_ref": "rr_project_ab12cd34",
    "result_type": "project_result",
    "owner_skill": "/project-teammate-discovery",
    "input_refs": ["sp_001", "rr_mentor_001"],
    "summary": {"count": 5, "top_ids": ["p1", "p2", "p3"]},
    "followups": [
        "/project-teammate-discovery.get_project_by_rank",
        "/project-teammate-discovery.explain_project_match",
    ],
    "payload": {"projects": [{"project_id": "p1"}, {"project_id": "p2"}]},
}
```

- [ ] **Step 4: Run the executor tests to verify they pass**

Run:

```bash
PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_chat_tool_executor -v
```

Expected: PASS, including the new assertions for action result-ref payloads.

- [ ] **Step 5: Commit the executor refactor**

```bash
git add \
  progrec_agent/runtime/chat_tool_executor.py \
  progrec_agent/capability_adapters/student_profiling.py \
  progrec_agent/capability_adapters/academic_graph.py \
  progrec_agent/capability_adapters/mentor_discovery.py \
  progrec_agent/capability_adapters/project_teammate_discovery.py \
  progrec_agent/capability_adapters/social_ranking.py \
  progrec_agent/tests/test_chat_tool_executor.py
git commit -m "feat: route chat execution through capability adapters"
```

Expected: commit succeeds with the executor and adapter files staged.

---

### Task 4: Add Inspectors And Execution-State Result Tracking

**Files:**
- Create: `progrec_agent/inspectors/__init__.py`
- Create: `progrec_agent/inspectors/mentor_result_inspector.py`
- Create: `progrec_agent/inspectors/project_result_inspector.py`
- Create: `progrec_agent/inspectors/teammate_result_inspector.py`
- Create: `progrec_agent/inspectors/bundle_result_inspector.py`
- Create: `progrec_agent/tests/test_result_inspectors.py`
- Modify: `progrec_agent/runtime/chat_tool_executor.py`
- Modify: `progrec_agent/dialog/state.py`
- Modify: `progrec_service/runtime/agent_v2_runner.py`

- [ ] **Step 1: Write failing inspector and state-serialization tests**

Create `progrec_agent/tests/test_result_inspectors.py`:

```python
from __future__ import annotations

import unittest

from progrec_agent.inspectors.mentor_result_inspector import get_mentor_by_rank


class TestResultInspectors(unittest.TestCase):
    def test_get_mentor_by_rank_returns_first_candidate_profile(self) -> None:
        mentor_result = {
            "result_ref": "rr_mentor_001",
            "payload": {
                "skill3_result": {
                    "mentor_candidates": [
                        {"mentor_id": "m1", "mentor_name": "Prof A", "rank": 1},
                        {"mentor_id": "m2", "mentor_name": "Prof B", "rank": 2},
                    ]
                }
            },
        }

        card = get_mentor_by_rank(mentor_result, rank=1)

        self.assertEqual(card["mentor_id"], "m1")
        self.assertEqual(card["rank"], 1)


if __name__ == "__main__":
    unittest.main()
```

Update the imports at the top of `progrec_agent/tests/test_agent_core_v2.py` and append this test:

```python
from progrec_agent.runtime.chat_tool_executor import ToolExecutionResult

    def test_record_tool_result_tracks_latest_result_refs(self) -> None:
        state = DialogState()
        result = ToolExecutionResult(
            tool_name="/mentor-discovery.recommend_mentors",
            skill_id="/mentor-discovery",
            status="succeeded",
            summary="Ranked mentor candidates.",
            payload={
                "result_ref": "rr_mentor_001",
                "result_type": "mentor_result",
                "summary": {"count": 2},
                "payload": {"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}, {"mentor_id": "m2"}]}},
            },
        )
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=Mock())

        core._record_tool_result(state, result)

        self.assertEqual(state.execution_context.latest_result_refs["mentor_result"], "rr_mentor_001")
        self.assertEqual(state.execution_context.active_result_ref, "rr_mentor_001")
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_result_inspectors \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: FAIL because the inspector module does not exist and `ExecutionContext` does not yet track latest result refs.

- [ ] **Step 3: Implement inspectors and extend execution state**

Create `progrec_agent/inspectors/mentor_result_inspector.py`:

```python
from __future__ import annotations


def list_mentors(mentor_result_payload: dict[str, object]) -> list[dict[str, object]]:
    return list(dict(mentor_result_payload.get("skill3_result") or {}).get("mentor_candidates") or [])


def get_mentor_by_rank(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    rows = list_mentors(dict(result_ref_payload.get("payload") or {}))
    if rank < 1 or rank > len(rows):
        raise ValueError(f"rank {rank} is out of range for {len(rows)} mentor candidates")
    row = dict(rows[rank - 1])
    row.setdefault("rank", rank)
    return row


def explain_mentor_match(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    row = get_mentor_by_rank(result_ref_payload, rank=rank)
    return {
        "mentor_id": row.get("mentor_id"),
        "rank": row.get("rank"),
        "summary": row.get("reason") or row.get("explanation") or "",
    }
```

Create `progrec_agent/inspectors/project_result_inspector.py`:

```python
from __future__ import annotations


def get_project_by_rank(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    rows = list(dict(result_ref_payload.get("payload") or {}).get("projects") or [])
    if rank < 1 or rank > len(rows):
        raise ValueError(f"rank {rank} is out of range for {len(rows)} project candidates")
    row = dict(rows[rank - 1])
    row.setdefault("rank", rank)
    return row
```

Create `progrec_agent/inspectors/teammate_result_inspector.py`:

```python
from __future__ import annotations


def get_teammate_by_rank(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    rows = list(dict(result_ref_payload.get("payload") or {}).get("teammates") or [])
    if rank < 1 or rank > len(rows):
        raise ValueError(f"rank {rank} is out of range for {len(rows)} teammate candidates")
    row = dict(rows[rank - 1])
    row.setdefault("rank", rank)
    return row
```

Create `progrec_agent/inspectors/bundle_result_inspector.py`:

```python
from __future__ import annotations


def show_bundle_summary(result_ref_payload: dict[str, object]) -> dict[str, object]:
    payload = dict(result_ref_payload.get("payload") or {})
    return dict(payload.get("final_recommendation") or {})
```

Update `progrec_agent/runtime/chat_tool_executor.py` to dispatch inspect capabilities:

```python
from progrec_agent.inspectors import bundle_result_inspector, mentor_result_inspector, project_result_inspector, teammate_result_inspector

        if tool_name == "/mentor-discovery.get_mentor_by_rank":
            card = mentor_result_inspector.get_mentor_by_rank(
                dict(arguments["mentor_result_ref"]),
                rank=int(arguments["rank"]),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                skill_id="/mentor-discovery",
                status="succeeded",
                summary="Expanded the selected mentor from the current mentor result.",
                payload={"payload": card},
            )
```

Add parallel inspect branches for:

- `/project-teammate-discovery.get_project_by_rank`
- `/project-teammate-discovery.get_teammate_by_rank`
- `/social-ranking.show_bundle_summary`

Each inspect branch should return a lightweight payload without minting a new `result_ref`.

Update `progrec_agent/dialog/state.py`:

```python
@dataclass
class ExecutionContext:
    result_handle: str | None = None
    selected_entity_type: str | None = None
    selected_entity_id: str | None = None
    last_result: dict[str, object] = field(default_factory=dict)
    last_turn_type: str = ""
    next_question: str = ""
    latest_result_refs: dict[str, str] = field(default_factory=dict)
    active_result_ref: str = ""
    last_shown_entities: dict[str, str] = field(default_factory=dict)
    result_ref_payloads: dict[str, dict[str, object]] = field(default_factory=dict)
```

Update `progrec_service/runtime/agent_v2_runner.py` so serialization preserves the new fields:

```python
    structured: dict[str, object] = {
        "turn_type": turn_type,
        "intent": state.active_goal or state.task,
        "active_goal": state.active_goal,
        "last_result_handle": state.execution_context.result_handle,
        "latest_result_refs": dict(state.execution_context.latest_result_refs),
        "active_result_ref": state.execution_context.active_result_ref,
        "last_shown_entities": dict(state.execution_context.last_shown_entities),
        "skill_usage": list(state.skill_trace or []),
        "planner_actions": list(state.planner_actions or []),
    }
```

- [ ] **Step 4: Run the targeted tests to verify they pass**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_result_inspectors \
  progrec_agent.tests.test_agent_core_v2 \
  -v
```

Expected: PASS, including serialization-safe execution-state fields.

- [ ] **Step 5: Commit the inspector layer**

```bash
git add \
  progrec_agent/inspectors/__init__.py \
  progrec_agent/inspectors/mentor_result_inspector.py \
  progrec_agent/inspectors/project_result_inspector.py \
  progrec_agent/inspectors/teammate_result_inspector.py \
  progrec_agent/inspectors/bundle_result_inspector.py \
  progrec_agent/dialog/state.py \
  progrec_service/runtime/agent_v2_runner.py \
  progrec_agent/tests/test_result_inspectors.py \
  progrec_agent/tests/test_agent_core_v2.py
git commit -m "feat: add result inspectors and state refs"
```

Expected: commit succeeds with the inspector and execution-state files staged.

---

### Task 5: Wire AgentCore V2 To Inspect Results Instead Of Rerunning Recommendations

**Files:**
- Modify: `progrec_agent/agent_core_v2.py`
- Modify: `progrec_agent/agent_planner.py`
- Modify: `progrec_agent/tests/test_agent_core_v2.py`
- Modify: `progrec_agent/tests/test_conversation_e2e_v2.py`

- [ ] **Step 1: Add failing follow-up regression tests**

Append these tests to `progrec_agent/tests/test_agent_core_v2.py`:

```python
    def test_followup_first_mentor_profile_uses_existing_mentor_result(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            llm = Mock()
            llm.complete_json.side_effect = [
                {
                    "action": "call_tool",
                    "tool_name": "/mentor-discovery.get_mentor_by_rank",
                    "arguments": {"mentor_result_ref": "rr_mentor_001", "rank": 1},
                    "reasoning_summary": "User asked to inspect the first mentor from the previous result.",
                },
                {
                    "action": "answer_from_context",
                    "message": "Here is the first mentor from your last result.",
                    "reasoning_summary": "The inspection result already answered the user.",
                },
            ]
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
            state = DialogState()
            state.execution_context.latest_result_refs = {"mentor_result": "rr_mentor_001"}
            state.execution_context.active_result_ref = "rr_mentor_001"
            state.execution_context.result_ref_payloads = {
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "payload": {
                        "skill3_result": {
                            "mentor_candidates": [{"mentor_id": "m1", "mentor_name": "Prof A"}]
                        }
                    },
                }
            }

            reply, updated = core.handle_message(state, "I want to see the first mentor's profile.")

        self.assertIn("first mentor", reply)
        self.assertEqual(updated.execution_context.last_shown_entities["mentor"], "m1")
```

Append this test to `progrec_agent/tests/test_conversation_e2e_v2.py`:

```python
    def test_followup_projects_reuses_existing_profile_and_mentor_refs(self) -> None:
        llm = Mock()
        llm.complete_json.side_effect = [
            {
                "action": "call_tool",
                "tool_name": "/project-teammate-discovery.recommend_projects",
                "arguments": {
                    "student_profile_ref": "sp_001",
                    "mentor_result_ref": "rr_mentor_001",
                    "top_k": 5,
                },
                "reasoning_summary": "Use the last profile and mentor result to expand into projects.",
            },
            {
                "action": "suggest_next_steps",
                "message": "I found related projects. Want teammate matches too?",
                "suggested_next_actions": [{"target": "teammate", "label": "Find teammates"}],
                "reasoning_summary": "Projects are now available.",
            },
        ]
        runtime = Mock()
        runtime.run_project_recommendations_for_profile.return_value = {
            "projects": [{"project_id": "p1"}, {"project_id": "p2"}],
        }
        with tempfile.TemporaryDirectory() as td:
            core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm, recommendation_runtime=runtime)
            state = DialogState()
            state.execution_context.latest_result_refs = {
                "student_profile": "sp_001",
                "mentor_result": "rr_mentor_001",
            }
            state.execution_context.result_ref_payloads = {
                "sp_001": {"result_ref": "sp_001", "payload": {"profile": {"student_id": "chat-temp-1"}}},
                "rr_mentor_001": {"result_ref": "rr_mentor_001", "payload": {"skill3_result": {"mentor_candidates": []}}},
            }

            reply, updated = core.handle_message(state, "Recommend projects too.")

        self.assertIn("projects", reply.lower())
        self.assertEqual(updated.tool_results_summary["project_count"], 2)
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_agent_core_v2 \
  progrec_agent.tests.test_conversation_e2e_v2 \
  -v
```

Expected: FAIL because the current executor does not resolve inspect capabilities and `AgentCoreV2` does not update `last_shown_entities`.

- [ ] **Step 3: Implement inspect execution and result-ref-aware state recording**

Update `progrec_agent/agent_core_v2.py` so `_record_tool_result()` stores result refs and follow-up context:

```python
    def _record_tool_result(self, state: DialogState, result: ToolExecutionResult) -> None:
        state.skill_trace.append(result.to_skill_trace_entry())
        payload = dict(result.payload)
        result_ref = str(payload.get("result_ref") or "").strip()
        result_type = str(payload.get("result_type") or "").strip()
        if result_ref and result_type:
            state.execution_context.latest_result_refs[result_type] = result_ref
            state.execution_context.active_result_ref = result_ref
            state.execution_context.result_ref_payloads[result_ref] = payload
            state.execution_context.result_handle = result_ref
            state.execution_context.last_result = payload
```

Add a resolver in `AgentCoreV2` for inspect capability arguments before dispatch:

```python
    def _hydrate_capability_arguments(self, state: DialogState, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
        hydrated = dict(arguments)
        if tool_name == "/mentor-discovery.get_mentor_by_rank" and "mentor_result_ref" in hydrated:
            ref_id = str(hydrated["mentor_result_ref"])
            hydrated["mentor_result_ref"] = dict(state.execution_context.result_ref_payloads[ref_id])
        if tool_name == "/project-teammate-discovery.recommend_projects":
            profile_ref_id = str(hydrated["student_profile_ref"])
            mentor_ref_id = str(hydrated.get("mentor_result_ref") or "")
            hydrated["student_profile_ref"] = dict(state.execution_context.result_ref_payloads[profile_ref_id])
            if mentor_ref_id:
                hydrated["mentor_result_ref"] = dict(state.execution_context.result_ref_payloads[mentor_ref_id])
        return hydrated
```

Call that resolver just before `self.executor.execute(...)`:

```python
                call_arguments = self._hydrate_capability_arguments(working, action.tool_name, action.arguments)
                result = self.executor.execute(action.tool_name, call_arguments)
```

When an inspect result returns a mentor card, record it:

```python
        if result.tool_name == "/mentor-discovery.get_mentor_by_rank":
            mentor_payload = dict(payload.get("payload") or payload)
            mentor_id = str(mentor_payload.get("mentor_id") or "").strip()
            if mentor_id:
                state.execution_context.last_shown_entities["mentor"] = mentor_id
```

- [ ] **Step 4: Run the full phase-1 regression set**

Run:

```bash
PYTHONPATH=. python3 -m unittest \
  progrec_agent.tests.test_capability_schema \
  progrec_agent.tests.test_result_refs \
  progrec_agent.tests.test_contract_registry \
  progrec_agent.tests.test_chat_tool_registry \
  progrec_agent.tests.test_agent_planner \
  progrec_agent.tests.test_chat_tool_executor \
  progrec_agent.tests.test_result_inspectors \
  progrec_agent.tests.test_agent_core_v2 \
  progrec_agent.tests.test_conversation_e2e_v2 \
  -v
```

Expected: PASS, including the new follow-up behavior tests and the earlier action-capability coverage.

- [ ] **Step 5: Commit the agent wiring**

```bash
git add \
  progrec_agent/agent_core_v2.py \
  progrec_agent/agent_planner.py \
  progrec_agent/tests/test_agent_core_v2.py \
  progrec_agent/tests/test_conversation_e2e_v2.py
git commit -m "feat: support result-ref followups in chat agent"
```

Expected: commit succeeds with the agent wiring and regression tests staged.

---

## Spec Coverage Check

- Unified capability contract format: covered by Task 1 and Task 2.
- Action and inspect capability surfaces for all five skills: covered by Task 2 and Task 3.
- Result reference model for follow-up chaining: covered by Task 1, Task 3, and Task 4.
- Thin adapters over existing skill runtimes: covered by Task 2 and Task 3.
- Follow-up inspection instead of rerunning recommendation: covered by Task 4 and Task 5.
- Result-ref exposure in chat runtime serialization: covered by Task 4.

## Placeholder Scan

- No `TODO`, `TBD`, or “similar to above” placeholders remain.
- Every task includes concrete files, commands, and code snippets.
- Every verification step uses exact `unittest` commands already used in this repo.

## Type Consistency Check

- Capability ids consistently use the Scheme B names:
  - `/mentor-discovery.recommend_mentors`
  - `/mentor-discovery.get_mentor_by_rank`
  - `/project-teammate-discovery.recommend_projects`
  - `/project-teammate-discovery.recommend_teammates`
  - `/social-ranking.rerank_bundle`
- Result types consistently use:
  - `student_profile`
  - `mentor_result`
  - `project_result`
  - `teammate_result`
  - `bundle_result`
