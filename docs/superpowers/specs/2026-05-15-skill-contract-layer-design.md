# Skill Contract Layer Design

Date: 2026-05-15
Status: Proposed
Owner: Codex

## Goal

Introduce a Skill Contract Layer for the ProgRec chat agent so the LLM no longer reasons over raw scripts, file paths, or nested artifact payloads. The new layer should expose each ProgRec skill as a small set of structured capabilities that the agent can call and inspect through stable contracts.

This design targets the approved thin-wrapper version of Scheme B:

- keep the internal implementations of Skills 1-5
- add a structured capability layer around them
- include follow-up inspection in the contract surface
- defer deeper algorithm and storage rewrites to later phases

## Why This Exists

The current chat runtime still behaves too much like a guarded state machine. Even after recent fixes, the agent often answers follow-up questions poorly because it does not operate on stable result references. It knows how to trigger recommendation work, but it does not reliably know:

- what result was produced in the previous turn
- where that result lives
- how to inspect the first mentor, a specific project, or a teammate candidate
- which follow-up actions are valid on the current result

The Skill Contract Layer addresses this by replacing direct reasoning over raw skill internals with:

- capability contracts
- capability adapters
- result references
- explicit inspect capabilities

## Scope

This design covers:

- a unified capability contract format
- action and inspect capability surfaces for all five skills
- a result reference model for chaining follow-up requests
- thin adapters that bind existing skill runtimes into the new contract layer

This design does not cover:

- a full planner/runtime rewrite
- persistent session storage implementation details
- deep output-schema rewrites inside Skills 3-5
- algorithm changes for ranking quality
- a full unification of demo mode and graph mode behavior

Those belong to later Result/State Layer and Agent Runtime Layer work.

## Design Principles

1. The LLM should reason about capabilities, not scripts.
2. Follow-up inspection must be a first-class capability, not planner glue code.
3. Internal skill implementations remain the source of execution truth in phase 1.
4. The chat agent should pass references between capabilities instead of raw payloads whenever possible.
5. Thin wrappers should isolate existing path, mode, and artifact complexity from the planner.

## Layer Overview

The new architecture inserts a contract layer between the agent and the current skill runtimes:

```text
LLM planner
  -> capability registry
  -> capability contract
  -> capability adapter
  -> existing skill runtime
  -> result reference
  -> inspect capability
```

The planner will see only:

- capability ids
- capability kinds
- required inputs
- result types
- allowed follow-ups

It will not directly see:

- CLI commands
- script paths
- output file names
- nested internal JSON structures

## Core Objects

### Capability Contract

Each capability should be represented by a structured object with a stable identity and bounded semantics.

Minimum fields:

```json
{
  "capability_id": "/mentor-discovery.recommend_mentors",
  "kind": "action",
  "owner_skill": "/mentor-discovery",
  "when_to_use": "Use when a student profile is ready and the user wants mentor recommendations.",
  "requires": ["student_profile_ref"],
  "returns": "mentor_result",
  "side_effects": ["creates_result_ref"],
  "can_follow": ["student_profile"],
  "failure_modes": ["missing_profile", "resource_mismatch", "unknown_student_id"],
  "executor_binding": "mentor_discovery.run_recommend_mentors"
}
```

`kind` must be one of:

- `action`
- `inspect`

### Result Reference

All action capabilities should return a result reference object rather than exposing raw artifacts to the planner.

Minimum shape:

```json
{
  "result_ref": "rr_mentor_20260515_001",
  "result_type": "mentor_result",
  "owner_skill": "/mentor-discovery",
  "created_at": "2026-05-15T15:22:11Z",
  "session_id": "sess_123",
  "input_refs": ["sp_20260515_001"],
  "summary": {
    "target_student_id": "chat-temp-202605151522",
    "count": 5,
    "top_ids": ["m_001", "m_014", "m_022"]
  },
  "followups": [
    "/mentor-discovery.get_mentor_by_rank",
    "/mentor-discovery.explain_mentor_match",
    "/project-teammate-discovery.recommend_projects",
    "/project-teammate-discovery.recommend_teammates"
  ]
}
```

### Result Types

Phase 1 should constrain result types to a small fixed set:

- `student_profile`
- `resource_validation`
- `mentor_result`
- `project_result`
- `teammate_result`
- `bundle_result`
- `report_artifact`

### Payload Access

Each result ref may point to a full payload, but the planner should reason first from lightweight metadata:

- `summary`
- `count`
- `top_ids`
- `followups`
- `owner_skill`
- `input_refs`

Detailed payload reads should happen through inspect capabilities.

## Capability Surfaces Per Skill

### Skill 1: `/student-profiling`

Role in phase 1: runtime helper skill for profile construction and inspection.

Action capabilities:

- `/student-profiling.build_temporary_profile`
- `/student-profiling.update_profile_context`

Inspect capabilities:

- `/student-profiling.show_profile_summary`
- `/student-profiling.explain_profile_fields`

Expected action output:

- `student_profile_ref`

Skill 1 must not own recommendation execution.

### Skill 2: `/academic-graph`

Role in phase 1: resource and environment inspection layer.

Action capabilities:

- `/academic-graph.validate_graph_resources`

Inspect capabilities:

- `/academic-graph.show_resource_status`
- `/academic-graph.list_available_student_spaces`

Optional management capability, not part of default chat flow:

- `/academic-graph.rebuild_graph_resources`

Expected action output:

- `resource_validation_ref`

Skill 2 should not be treated as a normal conversation-time recommendation skill.

### Skill 3: `/mentor-discovery`

Role in phase 1: primary mentor recommendation runtime skill.

Action capabilities:

- `/mentor-discovery.recommend_mentors`

Inspect capabilities:

- `/mentor-discovery.list_mentors`
- `/mentor-discovery.get_mentor_by_rank`
- `/mentor-discovery.get_mentor_by_id`
- `/mentor-discovery.explain_mentor_match`
- `/mentor-discovery.list_followups`

Expected action output:

- `mentor_result_ref`

This skill is the first-class owner of requests like:

- "show me the first mentor"
- "show the top mentor profile"
- "why did you recommend this mentor?"

### Skill 4: `/project-teammate-discovery`

Role in phase 1: project and teammate expansion skill, exposed as two clean capability faces.

Action capabilities:

- `/project-teammate-discovery.recommend_projects`
- `/project-teammate-discovery.recommend_teammates`

Project inspect capabilities:

- `/project-teammate-discovery.list_projects`
- `/project-teammate-discovery.get_project_by_rank`
- `/project-teammate-discovery.explain_project_match`

Teammate inspect capabilities:

- `/project-teammate-discovery.list_teammates`
- `/project-teammate-discovery.get_teammate_by_rank`
- `/project-teammate-discovery.explain_teammate_match`

Shared inspect capability:

- `/project-teammate-discovery.list_followups`

Expected action outputs:

- `project_result_ref`
- `teammate_result_ref`

Even if the underlying implementation still runs one larger pipeline, the contract layer must expose project and teammate operations separately.

### Skill 5: `/social-ranking`

Role in phase 1: bundle-level ranking and report coordination.

Action capabilities:

- `/social-ranking.rerank_bundle`

Inspect capabilities:

- `/social-ranking.show_bundle_summary`
- `/social-ranking.list_bundle_entities`
- `/social-ranking.explain_bundle_ranking`
- `/social-ranking.export_report`

Expected action outputs:

- `bundle_result_ref`
- `report_artifact_ref`

Skill 5 should no longer be presented to the planner as only a report-emitting script.

## Follow-Up Interaction Model

Follow-up user requests should chain off existing result refs rather than trigger fresh recommendation work by default.

Examples:

### "Show me the first mentor's profile"

Expected contract flow:

1. resolve the latest `mentor_result_ref`
2. call `/mentor-discovery.get_mentor_by_rank(rank=1, mentor_result_ref=...)`
3. answer from inspect payload

### "Why this mentor?"

Expected contract flow:

1. resolve the active mentor entity or the most recently shown mentor
2. call `/mentor-discovery.explain_mentor_match(...)`
3. answer from explanation payload

### "Recommend projects too"

Expected contract flow:

1. resolve the latest `student_profile_ref`
2. resolve the latest `mentor_result_ref`
3. call `/project-teammate-discovery.recommend_projects(...)`
4. return a new `project_result_ref`

The agent should not rerun mentor recommendation for these follow-up requests unless required inputs are no longer available or the user asks to refresh results.

## Adapter Layer

Phase 1 should introduce an explicit adapter layer rather than rewriting skill internals.

Suggested structure:

```text
progrec_agent/
  contracts/
    capability_schema.py
    result_refs.py
    registry.py
  capability_adapters/
    student_profiling.py
    academic_graph.py
    mentor_discovery.py
    project_teammate_discovery.py
    social_ranking.py
  inspectors/
    mentor_result_inspector.py
    project_result_inspector.py
    teammate_result_inspector.py
    bundle_result_inspector.py
```

Responsibilities:

- `contracts/`: schemas and registry metadata
- `capability_adapters/`: bind action capabilities to existing runtimes
- `inspectors/`: read result payloads and resource bundles for follow-up requests

## Thin-Wrapper Binding Strategy

### Skill 1 binding

- bind temporary profile construction to current standardization logic
- bind update behavior to current profile merge logic
- keep explanatory provenance lightweight in phase 1

### Skill 2 binding

- bind validation to current resource resolution and validation helpers
- hide path selection and mode-specific fallbacks behind the adapter

### Skill 3 binding

- bind recommendation to the current mentor runtime helper
- implement inspect capabilities by reading `mentor_candidates[]` first
- supplement profile detail from mentor bundle lookups when needed

### Skill 4 binding

- call existing project/teammate runtime code
- split returned payload into project and teammate result refs
- keep separate inspect surfaces even if one internal call produced both

### Skill 5 binding

- bind bundle ranking to the existing ranker path
- expose explanations and exports through inspect capabilities
- avoid requiring the planner to read markdown files directly

## Migration Plan

### Phase 1

- add contract schemas, adapters, and inspectors
- preserve current skill implementations
- wire the chat path to capabilities and result refs
- keep pipeline UI and legacy CLI behavior intact

### Phase 2

- make chat runtime fully capability-native
- reduce direct runtime calls from planner/runtime code
- decide which internal payload shapes are worth standardizing further

## Explicit Non-Goals For Phase 1

- rewrite Skill 3 ranking
- rewrite Skill 4 graph logic
- rewrite Skill 5 scoring formulas
- merge all five skills into one super-skill
- eliminate all demo mode vs graph mode distinctions
- replace all CLIs with new agent-native executors

## Risks And Constraints

### Skill 4 complexity

Skill 4 remains the heaviest adapter surface because its current payload combines projects, teammates, graph evidence, and multiple fallback modes. The contract layer must hide this complexity without pretending it does not exist.

### Skill 5 report orientation

Skill 5 is currently biased toward final artifact generation. Phase 1 should expose inspection and summary capabilities, but rich bundle inspection may remain limited compared with future phases.

### Resource-space inconsistency

Skill 2, Skill 3, and Skill 4 still operate across demo mode and graph mode bundles. Phase 1 should isolate this through adapters and validation, not eliminate it.

## Success Criteria

The Skill Contract Layer is successful when all of the following are true:

1. The planner can select capabilities without reasoning over script paths or CLI syntax.
2. The agent can answer "show me the first mentor" without rerunning recommendation.
3. The agent can continue from mentor results into projects or teammates using result refs.
4. The planner no longer depends on raw artifact file names or nested JSON field knowledge.
5. Existing internal skill implementations remain largely unchanged in phase 1.

## Next Dependency

Once approved, the next design project should define the Result/State Layer that stores:

- result refs
- active ref selection
- latest refs per result type
- last shown entities
- follow-up resolution state

That layer will supply the runtime substrate required for these contracts to work consistently across turns.
