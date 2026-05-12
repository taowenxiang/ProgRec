# ProgRec Product-Grade Conversational Agent Redesign

Date: 2026-05-12
Status: Proposed
Owner: Codex

## Goal

Redesign the `progrec_agent/` conversational layer into a product-grade, stateful AI agent that can understand natural language robustly, collect required information before execution, and deliver stable follow-up behavior without relying on brittle prompt-only routing or fixed user phrasing.

This redesign is intentionally larger than a bugfix. The objective is to resolve the accumulated architectural problems in the current chat layer rather than continue adding local patches.

## Problem Summary

The current conversational agent has several structural flaws:

1. Intent routing, clarification, profile drafting, and execution selection are mixed together.
2. Clarification turns are not truly stateful. The agent can ask a question, but the next user turn is often treated as a brand-new request instead of an answer to the pending question.
3. The LLM directly influences control flow too early by selecting tools and generating clarification behavior.
4. Session memory is insufficiently structured for follow-up questions such as `show the top mentor`, `why this mentor`, or `use graph mode`.
5. Existing-profile and temporary-profile recommendation flows are split too early and too inconsistently.
6. Error messaging often falls back to vague replies instead of concrete execution blockers.

The result is an agent that can appear conversational in simple demos but behaves unpredictably under realistic natural-language interaction.

## Product Direction

The redesigned agent will prefer correctness over speed of execution.

Behavior target:

- Do not execute high-impact recommendation actions when required information is missing.
- Ask focused clarification questions tied to explicit missing slots.
- Maintain coherent state across multiple turns.
- Interpret follow-up questions using session context before re-parsing them as brand-new tasks.
- Treat the LLM as a semantic parser and surface real execution blockers clearly.

This corresponds to a strict clarification-first interaction model:

- The agent should gather required inputs before running.
- The agent should avoid silent high-risk assumptions.
- The agent should be explicit about what it knows, what it inferred, and what it still needs.

## Target Architecture

The redesigned agent should be split into six layers:

1. `nlu`
Parses natural language into structured semantic frames.

2. `dialog_state`
Stores the real structured state of the conversation, including confirmed slots, pending questions, conflicts, and execution context.

3. `clarification_policy`
Determines whether clarification is required, which slot to ask about next, and how to interpret the response.

4. `planner`
Maps complete state into a deterministic execution plan.

5. `runtime`
Executes recommendation, inspection, and validation actions against the existing pipeline and artifacts.

6. `response`
Turns structured state or execution results into user-facing replies.

Guiding principle:

- LLM understands language.
- State owns facts.
- Policy controls questions.
- Planner chooses actions.
- Runtime executes tools.
- Response renders results.

## Dialog State Model

The center of the system should be a serializable `DialogState`.

Suggested fields:

- `task`
- `goal`
- `resolved_slots`
- `candidate_slots`
- `required_slots`
- `missing_slots`
- `pending_question`
- `conflicts`
- `execution_context`
- `clarification_turn_count`
- `last_user_turn`
- `last_agent_turn`

### Task

Examples:

- `recommend_existing_student`
- `recommend_temporary_profile`
- `inspect_recommendation`
- `explain_recommendation`
- `validate_resources`

### Resolved Slots

These are confirmed values the system is allowed to rely on. They should come only from:

- explicit user statements
- validated system resources
- low-risk controlled defaults

Examples:

- `student_id`
- `profile_source`
- `mode`
- `target_types`
- `research_topic`
- `subtopic`
- `program_type`
- `experience_level`
- `time_budget`
- `top_k`

### Candidate Slots

These represent model inferences that may be useful but are not yet safe to execute on.

Example:

- user says `I want trustworthy AI research`
- model suggests possible subtopics such as `interpretability`, `fairness`, or `robustness`

These may guide the next clarification question, but they must not be treated as confirmed input.

### Pending Question

Every clarification question must be bound to a slot and an expected answer shape.

Example:

- `slot_name = profile_source`
- `question_type = single_choice`
- `expected_answer_shape = existing_profile | temporary_profile`

The next user turn should first be parsed as an answer to this pending question before being treated as a new request.

### Execution Context

This stores handles to prior successful runs and must anchor follow-up questions.

Examples:

- last recommendation result
- last selected mentor
- last ranked entities
- current mode
- artifact paths
- selected student or temporary profile identifier

## Slot Schema

The redesign should define task-specific slot requirements instead of a single global bag of fields.

### Task: Recommend Using Existing Student

Required:

- `student_id`
- `mode`

Optional:

- `target_types`
- `top_k`

### Task: Recommend Using Temporary Profile

Required:

- `research_topic`
- `program_type`
- `experience_level`

Strongly recommended:

- `subtopic`
- `time_budget`
- `skills`
- `preferences`

### Task: Inspect Recommendation

Required:

- a valid recommendation result in session

Optional:

- `entity_type`
- `rank`
- `entity_id`

### Task: Validate Resources

Required:

- `mode`

Optional:

- `student_id`

## Clarification Policy

Clarification should be policy-driven, not prompt-driven.

Allowed clarification triggers:

1. missing required slot
2. slot conflict
3. invalid reference
4. unsafe ambiguity

The policy should ask at most one clarification question per turn and choose the question with the highest information gain for task resolution.

Suggested priority:

1. task disambiguation
2. profile source
3. student identifier
4. mode
5. research topic or subtopic
6. experience and time constraints
7. display preferences

Rules:

- Do not ask open-ended questions when a bounded question will do.
- Do not ask about optional display preferences before required execution slots are resolved.
- Do not continue indefinite clarification loops.
- Maximum clarification chain should be capped, for example at five turns, after which the agent must summarize what is still missing and why execution cannot proceed.

### Clarification Parsing

If a `pending_question` exists, the next user turn should first be processed by an answer parser tied to that slot.

Examples:

- `use my description` resolves `profile_source = temporary_profile`
- `graph mode` resolves `mode = graph`
- `interpretability` resolves `subtopic = interpretability`

Only if the response cannot reasonably be interpreted as an answer should the system fall back to full re-parsing as a new request.

## Planner and Execution Model

The planner should consume structured state, not raw user text.

Input:

- task
- resolved slots
- conflicts
- execution context
- resource availability

Output:

- a deterministic execution plan

Suggested plan actions:

- `run_existing_profile_recommendation`
- `run_temporary_profile_recommendation`
- `inspect_top_mentor`
- `inspect_ranked_entity`
- `explain_ranked_entity`
- `validate_resources`
- `rebuild_resources_with_confirmation`

### Existing vs Temporary Profile

The distinction between existing-profile and temporary-profile recommendation should live in state and planning, not in early routing.

This means:

- state confirms `profile_source`
- planner maps that to the correct runtime action
- runtime executes the corresponding pipeline path

### Follow-Up Handling

Follow-up requests must prefer execution context over general language re-interpretation.

Examples:

- `show the top mentor`
- `why this mentor`
- `what is the second project`

These should resolve against session results before the system treats them as fresh tasks.

## NLU Strategy

The NLU layer should produce a structured semantic frame rather than directly choosing tools or asking questions.

Suggested `IntentFrame` fields:

- `intent`
- `target_types`
- `entities`
- `constraints`
- `preferences`
- `references`
- `confidence`
- `uncertain_fields`
- `possible_conflicts`
- `provenance`

### Provenance

Each extracted field should distinguish:

- `explicit`
- `inferred`
- `unknown`

This allows the policy layer to decide whether execution is safe or clarification is required.

### Prompting Rule

The semantic parser prompt must explicitly forbid the model from:

- selecting tools
- deciding execution
- inventing missing facts
- generating clarification questions
- pretending inferred fields are confirmed

The model should perform structured information extraction only.

### Validation

All model output must be validated locally against a strict schema.

Examples:

- valid intent whitelist
- valid mode enum
- valid target types
- legal student identifier formats
- rejection of unknown top-level keys

If validation fails, the system must fall back to safe clarification behavior rather than execution.

## Runtime Integration

The recommendation runtime should be wrapped behind task-oriented APIs rather than exposing raw tool selection behavior to higher layers.

Suggested runtime interfaces:

- `run_recommendation_for_student_id(student_id, mode, top_k)`
- `run_recommendation_for_profile(profile, mode, top_k)`
- `get_top_recommended_mentor(result_handle)`
- `get_ranked_entity(result_handle, entity_type, rank_or_id)`
- `explain_entity(result_handle, entity_type, rank_or_id)`
- `validate_resources(mode, student_id=None)`

This preserves the existing Skills 3 to 5 pipeline while making the conversational layer more deterministic and testable.

## Testing Strategy

The redesign requires a broader test strategy than the current mostly component-level checks.

Four layers of testing are required:

1. semantic parse tests
2. dialog state evolution tests
3. clarification policy tests
4. end-to-end conversation tests

### Golden Conversation Fixtures

Add persistent regression fixtures for realistic multi-turn conversations, including:

- existing-profile graph-mode recommendation
- temporary-profile trustworthy-AI recommendation
- top mentor inspection follow-up
- explanation follow-up
- ambiguous `show profile`
- invalid `student_id`
- conflicting instructions
- out-of-scope input

Each fixture should define:

- user turns
- expected clarification sequence
- expected final execution plan
- expected reply shape

## Migration Plan

This redesign should be introduced incrementally behind a feature flag instead of replacing the current agent in one step.

Suggested phases:

1. add new shared state and semantic frame models
2. build a new V2 agent pipeline alongside the current implementation
3. gate V2 behind an environment flag such as `PROGREC_AGENT_V2=1`
4. validate V2 with golden conversation fixtures
5. switch the REPL to V2 by default
6. retain V1 temporarily as fallback
7. remove V1 routing and clarification paths after stabilization

## Compatibility Constraints

The redesign must preserve these boundaries:

1. `run_agent.py` batch execution should remain stable.
2. Skills 3 to 5 core recommendation logic should remain independent of the chat architecture.
3. Existing graph-mode and verified-demo artifact flows must continue to work.

## Success Criteria

The redesign is successful when:

1. users can phrase requests naturally without relying on fixed templates
2. pending clarification answers are consumed as answers, not as unrelated new tasks
3. the agent does not execute recommendation actions while required slots are unresolved
4. follow-up references such as `top one`, `this mentor`, and `second project` work reliably
5. failures are concrete and actionable instead of vague
6. behavior is protected by golden conversation regression tests
7. the system is modular enough to extend explanation and debugging capabilities without re-breaking routing

## Non-Goals

This redesign does not attempt to:

- change the ranking algorithms of Skills 3 to 5
- replace the existing batch runner semantics
- turn ProgRec into a general-purpose chatbot

The redesign is specifically about making the conversational orchestration layer reliable, explainable, and maintainable.

