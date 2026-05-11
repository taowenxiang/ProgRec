# StuRec AI Agent Design

**Date:** 2026-05-11

## Goal

Upgrade the current `sturec_agent` from a fixed CLI orchestration wrapper into a true AI agent that plans over the existing five StuRec skills, interacts through natural language, and adaptively re-runs recommendation steps when user goals or recommendation quality require it.

## Project Context

The current repository already contains a functioning multi-skill recommendation stack:

- Skill 1 provides normalized student profiles and embeddings through handoff artifacts.
- Skill 2 provides academic graph artifacts and standardized mentor and student bundles.
- Skill 3 retrieves and ranks mentor candidates with trust-aware graph signals.
- Skill 4 expands mentor candidates into projects and teammates.
- Skill 5 performs final joint ranking across mentors, projects, and teammates.

The current `sturec_agent/` package wraps these skills into an interactive CLI and batch runner, but it is still fundamentally a deterministic pipeline:

- the command model is fixed
- the execution flow is fixed
- user intent is not understood from natural language
- missing information is not actively clarified
- ranking strategy is not adapted based on user preferences or result quality

For a course project in social network analysis with an AI focus, this is not enough. The upgraded system should preserve the graph-based and SNA-based recommendation core while adding an LLM-driven decision layer that behaves like an agent rather than a script runner.

## Design Goal

The new StuRec system should be framed as:

**An LLM-driven tool-using AI agent that plans over five specialized social-network-analysis recommendation skills.**

This means:

- the existing five skills remain distinct and continue to own the core recommendation logic
- a new LLM-based agent layer owns intent understanding, clarification, planning, adaptation, and explanation
- the agent decides how to use the skills rather than always executing a fixed pipeline

## Scope

In scope:

- natural-language CLI interaction
- LLM-based user intent understanding
- LLM-based profile extraction and enrichment
- clarification questions when key information is missing
- planner logic that decides when to run Skill 3 only versus Skill 3 to 5
- strategy-aware reruns when results do not match user constraints or are too homogeneous
- natural-language recommendation explanations and agent decision traces
- preservation of existing Skill 3, 4, and 5 ranking behavior as the core recommendation engine

Out of scope:

- replacing Skills 3 to 5 with end-to-end LLM ranking
- rebuilding the Skill 2 graph inside the agent loop
- adding a web UI in the first version
- full autonomous open-ended conversation without guardrails
- unrestricted multi-step self-reflection loops

## Recommended Product Direction

The approved direction is:

- mainline architecture: **Tool-Calling Agent**
- partial enhancement from a deeper AI direction: **LLM-assisted profile extraction and strategy-level reranking decisions**
- primary interaction surface: **CLI**

This produces a system that looks materially different from the current wrapper while staying technically grounded in the repository's strongest assets.

## Why This Is an AI Agent

The upgraded system is an AI agent because it adds four capabilities that the current wrapper does not have:

1. **Goal understanding**  
   The user can describe goals in natural language and the system extracts structured objectives and constraints.

2. **Clarification before action**  
   The system can detect missing information and ask targeted follow-up questions before invoking the recommendation tools.

3. **Dynamic tool planning**  
   The system decides which skills to run, in what order, and whether to run a partial or full recommendation flow.

4. **Adaptive rerun behavior**  
   The system can adjust recommendation strategy and re-run selected steps when the first pass does not satisfy the user's needs.

The AI layer does not replace the graph-based and trust-aware SNA core. It plans over that core.

## Architecture Overview

The new architecture should be:

```text
natural-language CLI
  -> planner
  -> orchestrator / tool executor
  -> skills 1 to 5
  -> result judge
  -> explainer
  -> user-facing response
```

Compared with the current architecture:

```text
fixed CLI command
  -> orchestrator
  -> skills 3 to 5
```

the critical change is that planning and adaptation become first-class responsibilities.

## Layered Responsibilities

### 1. Conversation Layer

The CLI should become the natural-language interaction surface. The user should be able to say things like:

- "I want a mentor in trustworthy AI or NLP."
- "I only have three hours a week."
- "Recommend again, but care more about teammate complementarity than mentor prestige."

The CLI should still retain a few explicit support commands:

- `help`
- `show profile`
- `show trace`
- `show mentor <id>`
- `exit`

### 2. Agent Brain

The LLM-driven agent layer should own:

- intent understanding
- profile extraction
- clarification decisions
- tool planning
- rerun decisions
- strategy adjustments
- explanation synthesis

This layer should produce structured decisions rather than free-form text only.

### 3. Skill Tool Layer

The five existing skills remain the specialized tools:

- Skill 1: student profile schema and profile compatibility
- Skill 2: resource and graph bundle provider
- Skill 3: mentor discovery
- Skill 4: project and teammate discovery
- Skill 5: final social ranking

The agent uses these skills as tools instead of replacing them.

## Responsibility Split Between LLM and Existing Skills

### Responsibilities owned by the LLM layer

- extracting user goals from natural language
- identifying missing constraints
- asking clarification questions
- generating an execution plan
- mapping user preferences to ranking strategy
- deciding whether to re-run with updated strategy
- synthesizing final recommendation explanations
- summarizing why the agent chose the final path

### Responsibilities owned by existing skills

- normalized profile compatibility with downstream contracts
- graph resource loading and validation
- mentor retrieval and graph-aware ranking
- project and teammate expansion
- final joint ranking and diversity-aware scoring

This split preserves interpretability and makes the AI contribution easy to explain in a course setting.

## Data Model

The agent should maintain two profile layers.

### Skill profile

This remains compatible with the existing Skill 1 and downstream contracts:

```json
{
  "student_id": "string",
  "grade": "string",
  "major": "string",
  "skills": ["string"],
  "interests": ["string"],
  "experience_summary": "string",
  "availability": "string"
}
```

### Agent profile

This is maintained only by the agent layer and is not required by Skills 3 to 5:

```json
{
  "goal": "string",
  "research_direction": ["string"],
  "constraints": {
    "time_budget_hours_per_week": 0,
    "difficulty_preference": "string",
    "exclude_topics": ["string"]
  },
  "preferences": {
    "prefer_diversity": false,
    "prefer_low_commitment": false,
    "prefer_fast_onboarding": false,
    "collaboration_focus": "mentor|project|teammate|balanced"
  },
  "desired_outcomes": ["string"],
  "confidence": 0.0
}
```

The agent profile captures user intent in a way that the existing skill schema does not.

## Proposed New Modules

The new agent behavior should be introduced inside `sturec_agent/` without destabilizing the existing skill trees.

### New files

- `sturec_agent/llm_client.py`  
  Unified wrapper for external LLM calls, model selection, retries, and structured output parsing.

- `sturec_agent/agent_schema.py`  
  Data classes or typed dictionaries for `AgentProfile`, `ExecutionPlan`, `RecommendationStrategy`, `DecisionTrace`, and clarification structures.

- `sturec_agent/profile_enricher.py`  
  Converts user natural-language input into `skill_profile` plus `agent_profile`.

- `sturec_agent/planner.py`  
  Decides whether to ask clarification questions, which tools to run, and whether to re-run with adjusted strategy.

- `sturec_agent/strategy.py`  
  Maps user preferences into concrete ranking settings and tool configuration.

- `sturec_agent/result_judge.py`  
  Evaluates whether output quality satisfies user constraints and whether a rerun is justified.

- `sturec_agent/explainer.py`  
  Produces final advisor-style explanations and summaries of why recommendations were selected.

- `sturec_agent/prompts.py`  
  Stores prompt templates for intent understanding, profile extraction, clarification, planning, judging, and explanation.

- `sturec_agent/tools.py`  
  Presents Skills 1, 3, 4, and 5 as standardized agent tools.

### Existing files to modify

- `sturec_agent/repl.py`  
  Upgrade from fixed command flow to natural-language-first interaction while preserving a few diagnostic commands.

- `sturec_agent/session.py`  
  Add memory for conversation history, agent profile, latest plan, strategy, rerun count, and decision trace.

- `sturec_agent/orchestrator.py`  
  Narrow responsibility from fixed pipeline owner to tool execution layer used by the planner.

### Files to avoid destabilizing

The following should be changed minimally in the first version:

- `skill3_mentor_discovery/`
- `skill4_handoff/`
- `skill5_student-recommendation-ranker/`
- `sturec_agent/config.py`
- `sturec_agent/schemas.py`

The AI layer should be additive rather than a rewrite of the SNA core.

## Tool Interface Direction

The agent should interact with existing logic through thin tool wrappers rather than embedding all logic into the planner.

Recommended tool abstractions:

- `build_student_profile_tool`
- `run_mentor_discovery_tool`
- `run_project_teammate_tool`
- `run_social_ranking_tool`

This keeps planner code clean and makes tool usage easy to trace in logs and demos.

## Natural-Language Interaction Model

The first version should support three user interaction patterns:

1. **Initial request**
   - "I want a mentor in trustworthy AI."

2. **Constraint update**
   - "I only have three hours per week."

3. **Strategy update or rerun request**
   - "Recommend again, but prioritize easier onboarding."

The user should not need to switch into a separate form-filling mode unless debugging.

## Agent State Machine

The execution flow should be modeled as a bounded state machine:

- `idle`
- `collecting_user_goal`
- `profile_drafting`
- `waiting_for_clarification`
- `planning_tools`
- `running_skill3`
- `running_skill4`
- `running_skill5`
- `evaluating_results`
- `rerun_with_adjustment`
- `done`

The system should feel flexible, but the state transitions should remain explicit for safety and debuggability.

## Clarification Policy

The agent should only ask questions that materially affect recommendation strategy.

The high-value information slots are:

- `research_direction`
- `time_budget`
- `goal_type`
- `difficulty_preference`
- `collaboration_preference`

Policy:

- if two or more of these are missing, ask clarification before running tools
- if only one is missing and enough information exists to start, run once and clarify later if needed
- ask at most two clarification rounds
- ask at most one or two questions per round
- if the user declines to provide more information, fall back to sensible defaults and continue

This makes the system proactive without turning it into a questionnaire.

## Tool Planning Policy

The planner should decide between partial and full execution.

### Run Skill 3 only when:

- the user has only expressed a broad research direction
- the system wants to quickly inspect mentor-space quality before full expansion
- mentor-level results are needed to infer useful next-step clarification

### Run Skill 3 to 5 when:

- the profile is sufficiently complete
- the user is explicitly asking for final recommendations
- constraints are coherent enough to justify the full pipeline

Even if the first implementation often runs the full stack, the decision should be explicit and recorded in the trace.

## Rerun Policy

Adaptive reruns are the main behavioral difference between the old wrapper and the new agent.

Reruns should only occur in four situations:

- recommendation lists are too homogeneous
- returned options violate a hard user constraint
- coverage is too weak in one recommendation category
- the user adds a new meaningful preference after an initial run

The first version should allow:

- at most two reruns
- limited strategy changes per rerun
- clear trace messages explaining why rerun happened

## Strategy Adjustment Policy

The agent should not freely mutate low-level algorithm internals. It should only adjust a small and interpretable strategy surface, such as:

- `top_k`
- mentor pool width
- diversity emphasis
- low-commitment emphasis
- fast-onboarding emphasis
- include and exclude topic constraints
- collaboration focus bias

These adjustments should feed into Skill 5 parameters or tool-level filtering rules, not rewrite core graph logic.

## Result Quality Policy

The result judge should combine simple guardrails with LLM-based interpretation.

### Code-level guardrails

- maximum rerun count
- no Skill 4 or Skill 5 without valid Skill 3 output
- existing `student_id` alignment checks remain mandatory
- graph-mode and resource validation continue to use existing hard checks

### Quality heuristics

The first version should consider results acceptable when:

- at least three mentors are available
- at least three projects are available when graph coverage permits
- at least three teammates are available, or the system can clearly explain why not
- no major hard constraint is violated
- result diversity is above a defined threshold or explicitly justified

## LLM Decision Contract

The LLM should be asked to return structured JSON for decision-making. Typical fields should include:

- `need_clarification`
- `clarification_questions`
- `tool_plan`
- `strategy_adjustments`
- `rerun_needed`
- `stop_reason`

Python code should validate and constrain these decisions before execution.

This ensures the LLM is used for judgment while the codebase retains operational control.

## Session Design Changes

`sturec_agent/session.py` should persist enough information for multi-turn agent behavior.

Additional session fields should include:

- `conversation_history`
- `agent_profile`
- `latest_plan`
- `active_strategy`
- `decision_trace`
- `rerun_count`

This lets the user refine an earlier run without restating all preferences.

## CLI Output Design

The final response should show both recommendation content and agent behavior.

Recommended output sections:

- interpreted user goal
- key constraints and preferences
- top mentors
- top projects
- top teammates
- explanation of why those results fit
- decision trace summary
- optional next-step advice

Recommended diagnostic command:

- `show trace`

This is especially useful for live demos and grading.

## Minimum Viable Version

The first version should prioritize the following six capabilities:

1. natural-language CLI input
2. LLM-based profile extraction
3. clarification loop
4. planner-controlled tool invocation
5. strategy-aware rerun
6. final explanation plus decision trace

If these six are working, the system will already feel like a genuine AI agent rather than a pipeline wrapper.

## Implementation Sequence

### Phase A — Agent skeleton

Add the new `sturec_agent/` modules and refactor the current flow into:

`repl -> planner -> orchestrator -> result_judge -> explainer`

### Phase B — LLM profile understanding

Connect the LLM client and implement:

- natural-language profile extraction
- agent profile creation
- clarification question generation

### Phase C — Planner and rerun behavior

Implement:

- explicit tool planning
- strategy mapping
- bounded rerun decisions

### Phase D — Explanation and demo polish

Add:

- advisor-style output
- decision trace reporting
- demo-friendly examples and scripts

## Risks and Mitigations

### Risk 1: The LLM overwhelms the SNA contribution

Mitigation:

- keep Skills 3 to 5 as the ranking core
- keep graph-based evidence and trust-aware ranking visible in explanations

### Risk 2: The system becomes a chat wrapper rather than an agent

Mitigation:

- require explicit tool planning decisions
- require clarification and rerun logic
- expose decision trace

### Risk 3: Too much freedom causes unstable behavior

Mitigation:

- restrict the LLM to structured outputs
- cap clarification rounds
- cap rerun count
- preserve existing alignment and resource hard checks

### Risk 4: Development scope expands too much

Mitigation:

- keep the first version CLI-only
- do not rewrite Skill 3 to 5
- focus the MVP on planning and adaptation, not maximum conversational breadth

## Demo Narrative Recommendation

The recommended live demo should show one student request across two turns:

1. initial request for a direction such as trustworthy AI or NLP with limited weekly time
2. first recommendation run with an explanation of the chosen strategy
3. follow-up user preference update such as stronger teammate complementarity
4. planner-triggered rerun with changed strategy and visibly different output

This demo best illustrates that the system is planning and adapting rather than simply printing a static ranking.

## Success Criteria

The design is successful when:

- a user can interact through natural language in the CLI
- the agent extracts structured goals and constraints
- the agent asks targeted clarification questions when necessary
- the agent explicitly decides how to use the existing skills
- the agent can perform a bounded rerun with adjusted strategy
- the final output includes both recommendations and a decision trace
- the system can be defended as an AI agent built on top of specialized SNA tools

## Final Positioning

The final project should be presented as:

**StuRec is no longer just a recommendation pipeline. It is an AI agent that understands user goals, plans over five specialized SNA skills, adapts recommendation strategy interactively, and explains its choices.**
