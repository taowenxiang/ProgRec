# Semi-Autonomous Skill Agent Design

Date: 2026-05-15

## Goal

Replace the current hard-coded chat pipeline with a semi-autonomous LLM agent that chooses which ProgRec skill to use at each turn.

The chat experience should feel like an intelligent recommendation assistant, not a form wrapped in chat UI. When a user asks for mentor recommendations, the agent should gather only the information needed for that goal, call only the mentor-related skill path, return mentor results, and then offer optional next steps such as project or teammate recommendations.

## Non-Goals

- Do not keep the current hard-flow `AgentCoreV2` behavior as the primary chat path.
- Do not automatically run the full recommendation pipeline when the user only asks for mentors.
- Do not rely on a fixed clarification question bank as the main dialog policy.
- Do not let the LLM call arbitrary code or tools outside the registered ProgRec skill/tool catalog.

## Current Problem

The current agent is skill-aware in name, but the control flow is mostly deterministic:

- The LLM parses the user message into a structured frame.
- `TASK_REQUIRED_SLOTS` decides which fields are mandatory.
- `QUESTION_BANK` decides what question to ask.
- `planner_v2` maps completed fields to a pipeline action.
- A temporary profile request tends to run `recommend_full_pipeline`, producing mentors, projects, and teammates even when the user only requested mentors.

This makes responses repeat across models and makes the chat path behave like a rigid pipeline.

## Target Behavior

Example mentor-only flow:

1. User asks: "Help me find a mentor for NLP and trustworthy AI."
2. Agent plans: mentor recommendation requires student/profile context.
3. Agent asks a natural clarification question based on the relevant skill input needs.
4. User provides context such as program type, background, interests, and experience.
5. Agent builds or updates a temporary profile using student profiling capability.
6. Agent calls mentor discovery only.
7. Agent returns top mentor recommendations.
8. Agent asks whether the user wants related projects, teammates, or a deeper explanation.
9. Agent calls project or teammate skills only if the user asks for them.

## Architecture

Introduce a new semi-autonomous orchestration loop and make it the default chat runtime.

```text
conversation state
+ skill/tool registry
+ latest user message
+ prior skill results
-> LLM action planner
-> backend action validator
-> skill/tool executor or user-facing question
-> response composer
-> persisted dialog state and skill trace
```

The LLM becomes the dialog and skill orchestration policy. Backend code remains responsible for validation, execution, persistence, and safe fallbacks.

## Agent Actions

The planner returns one structured action per step:

- `ask_user`: ask for missing or ambiguous information.
- `call_tool`: call one registered tool with validated arguments.
- `answer_from_context`: answer using existing conversation state or prior results.
- `suggest_next_steps`: offer optional follow-up skills without executing them.
- `stop`: finish the turn without further tool calls.

The runtime may allow a bounded multi-step loop in one user turn, for example:

```text
call_tool(build_temporary_profile)
call_tool(rank_mentors)
answer_from_context
suggest_next_steps
```

The loop must stop when it needs user input, reaches the max step count, or completes a user-facing answer.

## Skill And Tool Catalog

The skill registry should describe capabilities rather than forcing a single full pipeline path.

Initial tool catalog:

- `/student-profiling.build_temporary_profile`
  - Builds a normalized temporary student profile from conversation context.
  - Requires enough user-provided context to produce a useful profile.
- `/student-profiling.update_profile_context`
  - Updates profile state with new user-provided details.
- `/mentor-discovery.rank_mentors`
  - Ranks mentor candidates for a profile and mentor-oriented goal.
- `/project-discovery.recommend_projects`
  - Recommends projects when the user asks for projects or accepts that follow-up.
- `/teammate-discovery.recommend_teammates`
  - Recommends teammates when the user asks for teammates or accepts that follow-up.
- `/social-ranking.rerank_candidates`
  - Reranks a mixed result set when the user asks for broader combined recommendations.

Existing full-pipeline code may remain for the separate pipeline UI and for shared low-level runtime helpers, but the default chat agent must not call it for mentor-only requests.

## Planner Prompt Requirements

The planner prompt must include:

- Available skill/tool catalog and schemas.
- Current dialog state.
- Prior skill trace and result summaries.
- Latest user message.
- Explicit instruction to satisfy the user's current target, not to run extra recommendation categories.
- Explicit instruction to ask the user when required arguments are missing or ambiguous.
- Explicit instruction not to invent student IDs, profile facts, mentor facts, or tool outputs.

The planner must return strict JSON. Invalid JSON or invalid actions go through backend recovery.

## Validation Rules

Backend validation is mandatory:

- Tool name must exist in the registered catalog.
- Tool arguments must match schema.
- Required arguments must be present.
- User identity, student IDs, and profile facts must come from conversation state, datasets, or tool results.
- The agent cannot execute project, teammate, or social ranking tools unless the user requested that target or accepted a suggested next step.
- A bounded step limit prevents infinite agent loops.

Validation failure should not crash the chat. The runtime should ask the LLM for a repaired action once, then fall back to a clear user-facing clarification or error.

## Dialog State

Dialog state should track:

- User goal targets: mentors, projects, teammates, explanations, validation, or meta questions.
- Profile context collected so far.
- Pending user question, if any.
- Last planner action.
- Skill trace.
- Prior tool results and compact summaries.
- Suggested next actions waiting for user confirmation.

This replaces the current slot-first state as the primary control mechanism. Slot fields may remain as compatibility data during migration, but they must not drive the main policy.

## Response Behavior

Responses should be composed after planner/tool execution, not hard-coded from fixed templates.

The response composer should:

- Explain what was done in concise natural language.
- Include mentor results when mentor discovery ran.
- Mention skill activity through structured metadata for the frontend.
- Ask at most one useful follow-up question.
- Offer optional next steps only after satisfying the user's original request.

## API And Frontend Compatibility

Keep the existing chat API shape where possible:

- `reply_text`
- `structured_result.turn_type`
- `structured_result.skill_usage`
- `dialog_state_payload`

Add fields as needed:

- `planner_actions`
- `suggested_next_actions`
- `active_goal`
- `tool_results_summary`

The frontend can continue rendering skill activity cards from `skill_usage`.

## Migration Plan

Directly replace the default chat runtime with the semi-autonomous agent. Do not keep the hard-flow version as the primary chat behavior.

Implementation can still preserve old modules temporarily for tests or reference, but they should not control `/agent/sessions/{session_id}/messages`.

Expected changes:

- Rewrite the default chat core around the semi-autonomous loop. If an `AgentCoreV3` class is introduced during implementation, `/agent/sessions/{session_id}/messages` must be wired to it immediately and the old `AgentCoreV2` hard-flow path must be removed from default chat execution.
- Demote `policy/clarification.py` and `dialog/slots.py` to legacy fallback or remove their use from the default path.
- Replace `planner_v2` with an LLM action planner.
- Expand `skill_catalog.py` or `skill_registry.py` with executable tool schemas.
- Split runtime execution so mentor-only, project-only, and teammate-only calls are separate from full pipeline execution.
- Update tests from fixed-question assertions to behavior assertions.

## Testing

Unit tests:

- Planner validates known actions and rejects unknown tools.
- Mentor-only request does not call project or teammate tools.
- Missing profile context produces `ask_user`.
- User acceptance of project follow-up calls project discovery.
- Invalid planner output triggers repair or safe fallback.

Integration tests:

- First turn mentor request asks for profile context.
- After enough context, mentor-only recommendations are returned.
- Skill trace includes only the executed tools.
- Follow-up project request reuses existing profile context.
- Meta question can explain which skills were used.

Regression tests:

- No hard-coded `program_type` and `experience_level` question sequence in the default chat path.
- No automatic full pipeline for mentor-only requests.

## Implementation Decisions

- The first implementation should use a bounded maximum of 4 planner/tool steps per user turn.
- The initial response composer should be LLM-based with a deterministic fallback for invalid or unavailable LLM output.
- Existing full-pipeline runtime may remain for the separate pipeline UI, but chat should use target-specific tools.
