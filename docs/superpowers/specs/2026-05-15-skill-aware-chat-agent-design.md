# ProgRec Skill-Aware Chat Agent Design

Date: 2026-05-15
Status: Proposed
Owner: Codex

## Goal

Rework the `/chat` conversational agent into a skill-aware planner that behaves closer to Codex with skills: it should read compact skill descriptions, understand natural-language user intent, propose the right ProgRec skill/tool chain, and let deterministic local policy validate and execute that chain.

This is not a small phrase-map fix. The goal is to replace brittle turn handling with a bounded architecture where the LLM understands language and skills, while local code owns state, safety, execution, and traceability.

## Current Diagnosis

The current `/chat` stack is centered on `AgentCoreV2`.

Observed behavior:

- The LLM is only used by `progrec_agent/nlu/parser.py` to return a strict JSON intent frame.
- The parser prompt explicitly says not to choose tools.
- If a pending clarification exists, the next user turn bypasses the LLM and goes through `dialog/answer_parser.py`.
- `answer_parser.py` only accepts exact phrase matches such as `temporary` and `build a temporary profile`.
- A user reply like `build a temporary profile from your description` is stored as the literal `profile_source` value, so `_normalize_recommendation_state()` does not convert the task to `recommend_temporary_profile`.
- The planner then returns `unsupported`, which produces the misleading refusal: "I can only help with ProgRec recommendation tasks..."
- `skill_usage` is currently assembled in `progrec_service/runtime/agent_v2_runner.py` after a recommendation result, so the UI can show skill activity even though the LLM did not actually select those skills.

This means the current agent is a guarded state machine with an LLM parser, not a skill-aware conversational agent.

## Product Target

The new agent should support conversations such as:

1. User: `Help me find a mentor for NLP and trustworthy AI.`
2. Agent: asks one necessary follow-up if it lacks enough profile context.
3. User: `build a temporary profile from your description`
4. Agent: understands this as `profile_source = temporary_profile`, not as an unrelated request.
5. User: provides profile details naturally.
6. Agent: standardizes the temporary profile, runs the needed recommendation skills, returns ranked recommendations, and records the actual skill chain.

Follow-up examples should work without rerunning the pipeline unless needed:

- `show me the top mentor`
- `why did you recommend this mentor?`
- `find teammates instead`
- `validate graph mode resources`
- `which skills did you use?`

Out-of-scope requests such as weather questions should be refused clearly and should not be converted into recommendation work.

## Chosen Approach

Use a skill-aware planner.

The LLM receives compact skill cards derived from the local skill registry and `SKILL.md` files. It returns a semantic proposal: task, slots, candidate skills, candidate tools, missing information, confidence, and a short routing rationale.

Local code remains the authority for:

- slot validation
- pending clarification handling
- deciding whether enough context exists to execute
- allowed tool names
- skill-chain execution
- resource validation
- confirmation gates for rebuild actions
- skill trace persistence
- final refusal decisions

The model suggests. The planner decides. The executor runs only registered ProgRec tools.

## Architecture

The new turn flow is:

```text
User message
  -> SkillCatalog
  -> PendingAnswerParser or SkillAwareParser
  -> DialogState merge
  -> SkillPlanner
  -> Runtime executor
  -> SkillTrace
  -> Response renderer
  -> SSE / persisted assistant message
```

### SkillCatalog

`SkillCatalog` loads local capability metadata and creates compact skill cards for the LLM.

Inputs:

- `progrec_agent/skill_registry.py`
- relevant `SKILL.md` files:
  - `skill1_student_profiling/SKILL.md`
  - `skill2_academic_graph_builder/SKILL.md`
  - `skill3_mentor_discovery/SKILL.md`
  - Skill 4 and Skill 5 docs if present in the repository
- `progrec_agent/tool_registry.py`

Output shape:

```json
{
  "skill_id": "/mentor-discovery",
  "name": "Mentor Discovery",
  "when_to_use": "Use when a student needs ranked mentor candidates.",
  "requires": ["standardized student profile", "Skill 2 mentor/student/graph resources"],
  "produces": ["mentor_candidates"],
  "allowed_tools": ["recommend_full_pipeline"],
  "cannot_do": ["project recommendation", "final joint ranking"]
}
```

The cards must be compact. The LLM does not need the full text of every `SKILL.md` on every turn.

### SkillAwareFrame

The new parser output should be explicit about both natural-language understanding and skill/tool proposals.

Suggested schema:

```json
{
  "turn_type": "domain_task",
  "task": "recommend_temporary_profile",
  "target_types": ["mentor"],
  "slots": {
    "profile_source": {"value": "temporary_profile", "provenance": "explicit"},
    "research_topic": {"value": "NLP and trustworthy AI", "provenance": "explicit"}
  },
  "candidate_skills": ["/student-profiling", "/mentor-discovery", "/social-ranking"],
  "candidate_tools": ["recommend_full_pipeline"],
  "missing_information": ["program_type", "experience_level"],
  "confidence": 0.91,
  "reasoning_summary": "The user wants mentor recommendations and supplied a topic, but the temporary profile is incomplete."
}
```

Allowed `turn_type` values:

- `domain_task`
- `clarification_answer`
- `inspect_previous_result`
- `resource_validation`
- `meta_question`
- `out_of_scope`

Allowed `task` values:

- `recommend_existing_student`
- `recommend_temporary_profile`
- `inspect_recommendation`
- `explain_recommendation`
- `validate_resources`
- `answer_meta_question`
- `out_of_scope`

The validator must reject unknown tools and skills, invalid modes, malformed slot maps, and low-confidence out-of-domain conversions.

### PendingAnswerParser

When `DialogState.pending_question` exists, the next user turn should first be interpreted as an answer to that slot. This parser should use slot-specific rules and, when needed, the same LLM semantic parser with the pending question context.

Slot behavior:

- `profile_source`: accept natural variants such as `temporary`, `use my description`, `build one from what I tell you`, `build a temporary profile from your description`, and `existing student profile`.
- `mode`: accept `demo`, `graph`, `graph mode`, and `use the real graph`.
- `research_topic`: preserve the user's text as a topic unless it is clearly a new unrelated request.
- `program_type`: preserve the answer as free text.
- `experience_level`: normalize obvious values like beginner, intermediate, advanced, but preserve richer descriptions.

If the answer cannot reasonably resolve the pending slot, the system may fall back to full skill-aware parsing as a new user request.

### DialogState

The existing `DialogState` remains the core state object, but it needs a few additions:

- `skill_trace`: list of skill/tool activity entries for the current and previous turn
- `last_skill_plan`: the selected skill plan or last parser proposal
- `last_result_summary`: compact summary for meta-questions

State must continue to store:

- `task`
- `resolved_slots`
- `candidate_slots`
- `missing_slots`
- `pending_question`
- `execution_context.last_result`

Follow-up turns must use `execution_context.last_result` before deciding to rerun recommendation work.

### SkillPlanner

The planner consumes `DialogState`, `SkillAwareFrame`, and `SkillCatalog`. It returns a deterministic execution plan.

Plan actions:

- `ask_clarification`
- `run_existing_profile_recommendation`
- `run_temporary_profile_recommendation`
- `inspect_ranked_entity`
- `explain_ranked_entity`
- `validate_resources`
- `answer_meta_question`
- `refuse_out_of_scope`

Planner rules:

- Do not execute when required slots are missing.
- Do not trust LLM-selected tools unless they exist in the local registry.
- Do not run inspect/explain without a previous recommendation result.
- Do not run existing-student recommendation without `student_id` and `mode`.
- Do not run temporary-profile recommendation until a standardized profile can be built.
- Do not ask optional questions before required execution slots.
- Ask at most one clarification question per turn.
- Prefer using existing conversation context over asking repeated questions.

### Temporary Profile Standardization

Temporary-profile recommendation must produce a standardized student profile before Skill 3 runs.

Minimum standardized fields:

- `student_id`
- `grade`
- `major`
- `skills`
- `interests`
- `experience_summary`
- `availability`

The initial implementation may use the existing profile adapter style, but it must map conversational slots into the standardized schema. For example:

- `research_topic` contributes to `interests`
- `experience_level`, `skills`, and free-form profile details contribute to `experience_summary`
- missing grade/major become `unknown`
- missing availability becomes `moderate`
- generated IDs use a stable prefix such as `chat-temp-`

The runtime should not pass raw planner slots directly to `orchestrator.recommend_for_profile()`.

### Runtime Execution

The runtime continues to use existing orchestrator paths:

- existing student: `ProgRecOrchestrator.recommend_for_student_id()`
- temporary profile: `ProgRecOrchestrator.recommend_for_profile()`
- resource validation: `validation_runtime.validate_resources()`
- inspection: `inspection_runtime.get_ranked_entity()`

The difference is that execution now receives a validated `SkillPlan`, and each runtime step records a `SkillTraceEntry`.

### SkillTrace

Skill trace entries should represent real activity.

Suggested shape:

```json
{
  "skill_id": "/mentor-discovery",
  "tool_name": "recommend_full_pipeline",
  "status": "succeeded",
  "summary": "Ranked mentor candidates for the standardized temporary profile.",
  "inputs": {"student_id": "chat-temp-202605150001", "top_k": 5},
  "outputs": {"mentor_count": 5}
}
```

`agent_v2_runner.py` should stop fabricating the same five skill entries for every recommendation result. It should expose the trace recorded by the planner/runtime.

### Response Rendering

Responses should remain concise and grounded in structured state.

Clarification examples:

- `Should I use an existing student profile from the dataset, or build a temporary profile from your description?`
- `What is your current experience level with NLP or trustworthy AI?`

Recommendation result examples:

- Summarize mentor, project, and teammate counts.
- Mention the top recommendation when available.
- Surface skill activity in structured payload rather than verbose prose.

Meta-question examples:

- `I used student profiling to prepare your profile, mentor discovery to rank mentors, project/teammate discovery to expand matches, and social ranking to produce the final package.`

Refusal example:

- `That is outside ProgRec's recommendation scope. I can help with mentor, project, teammate, ranking explanation, or resource validation questions.`

## Safety and Boundaries

The LLM must not execute commands or arbitrary scripts.

Allowed execution is limited to registered local tools and runtime modules. The planner must reject any tool name not present in `tool_registry.py`.

Rebuild actions keep confirmation gates.

Out-of-scope requests must not be converted into recommendation tasks merely because they contain a topic word like "AI".

## Testing Strategy

Add focused tests at each layer:

1. `SkillCatalog` loads compact cards and includes known skills.
2. `SkillAwareParser` validates skill/tool proposals and rejects unknown names.
3. `PendingAnswerParser` resolves natural profile-source answers, including `build a temporary profile from your description`.
4. Planner asks exactly one clarification when required slots are missing.
5. Planner chooses existing-student recommendation only when `student_id` and `mode` are present.
6. Planner chooses temporary-profile recommendation only after profile standardization can succeed.
7. Runtime records real skill trace entries.
8. `agent_v2_runner` returns real `skill_usage` from state.
9. End-to-end chat tests cover:
   - temporary-profile mentor request
   - existing-student graph request
   - top mentor inspection
   - why/explain follow-up
   - teammate follow-up
   - graph resource validation
   - weather/out-of-scope refusal

## Migration Plan

Implement this in layers so each change is testable:

1. Add tests for the screenshot failure and pending-answer behavior.
2. Add `SkillCatalog` and compact card generation.
3. Add `SkillAwareFrame` schema and validation.
4. Add pending-answer semantic parsing.
5. Replace the old parser prompt with the skill-aware parser.
6. Introduce deterministic `SkillPlanner`.
7. Add temporary profile standardization.
8. Add real skill trace recording.
9. Wire `agent_v2_runner.py` to return real skill usage.
10. Add end-to-end route tests for `/agent/sessions/{id}/messages`.

## Non-Goals

- Do not give the model arbitrary shell access.
- Do not rebuild the entire frontend.
- Do not replace the existing Skill 3/4/5 ranking implementations.
- Do not require full OpenAI function calling support from every compatible runtime profile.
- Do not make ProgRec a general chatbot.

## Acceptance Criteria

The implementation is complete when:

- The screenshot conversation no longer refuses the complete temporary-profile answer.
- The agent can use compact skill cards to classify recommendation, inspection, explanation, validation, and meta questions.
- The selected skill/tool chain is validated locally before execution.
- Temporary profiles are standardized before recommendation runtime execution.
- `skill_usage` reflects real recorded execution steps.
- Follow-up questions use prior result state instead of starting over.
- Out-of-scope questions are refused clearly.
- Layer and end-to-end tests pass.
