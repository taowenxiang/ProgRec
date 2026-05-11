# ProgRec Conversational Agent Design

## Goal

Upgrade `progrec_agent` from a mixed command/summary CLI into a chat-first agent that feels closer to Codex: it should understand natural-language requests, decide whether to answer, ask a clarifying question, request confirmation for risky work, or invoke one or more ProgRec skills and helper tools.

The first delivery target is the terminal REPL, but the new architecture should center on an `agent core` that can later support other frontends such as a web UI or API without rewriting the decision logic.

## Scope

In scope:

- a chat-first interaction model for `python3 -m progrec_agent.repl`
- routing across repository-specific tasks such as recommendation, explanation, inspection, debugging, and rebuild decisions
- unified tool metadata and execution for Skill 1 through Skill 5 plus read-only helper actions
- risk-based confirmation rules, especially for expensive or artifact-changing Skill 1 and Skill 2 operations
- session state that supports multi-turn clarification, confirmation, and context reuse
- tests for routing, policy, execution flow, and representative conversation scripts

Out of scope for the first implementation:

- a polished GUI or browser-native chat interface
- arbitrary filesystem or shell autonomy outside the ProgRec repository domain
- replacing the core algorithms inside Skill 1 through Skill 5
- turning the system into a general-purpose coding agent

## Product Direction

The target experience is a pure-chat interaction model:

- the user talks to the agent in natural language instead of learning commands
- the agent keeps its toolchain mostly in the background
- the agent asks follow-up questions only when confidence is low or information is missing
- the agent pauses for confirmation only when a planned action is high-impact

The capability boundary is "repository-local general agent". That means the agent is not limited to producing recommendations. It should also inspect outputs, explain why a result happened, diagnose common graph-mode failures, and tell the user when a rebuild is needed.

## Current State

The repository already contains the beginnings of an AI-agent upgrade path:

- `progrec_agent/repl.py` accepts free-form text and can call `run_agent_turn()`
- `progrec_agent/profile_enricher.py` drafts a profile from natural language via LLM output
- `progrec_agent/planner.py` produces an execution plan with optional clarification questions
- `progrec_agent/orchestrator.py` executes the current Skill 3 -> Skill 4 -> Skill 5 recommendation chain

The main limitation is that this flow is still effectively hard-coded around recommendations. The plan fields are stored but not used to route execution. The current session records history, but the history is not yet the driver of a real agent loop.

## Architecture Overview

The upgraded design separates the chat frontend from the decision-making core.

### 1. Chat Frontend

`repl.py` should become a thin terminal frontend:

- read user input
- display agent responses
- render optional detail views such as a mentor card or trace summary
- hand all message handling to a reusable `agent core`

The REPL should stop making direct routing decisions about when to run recommendation logic.

### 2. Agent Core

`agent_core` becomes the orchestrator for one conversation turn. For each user message it should:

1. load session state
2. compose the current conversational context
3. call the intent router
4. apply execution policy
5. execute tools if needed
6. synthesize a natural-language response
7. write updated state back to the session

This module is the stable center that later frontends can reuse.

### 3. Intent Router

The router classifies what the user is trying to do and how confident the system is about that judgment.

Expected top-level intents:

- `recommend`
- `explain`
- `inspect`
- `debug`
- `rebuild`
- `help`
- `chat`

The router should return structured output, not prose:

- `intent`
- `confidence`
- `candidate_tools`
- `needs_clarification`
- `clarification_question`
- `reasoning_summary`

The router does not execute anything. It only proposes the next action.

### 4. Tool Registry

All skills and repository helper actions should be represented through a common tool definition. Each tool record should include:

- `name`
- `purpose`
- `intent_tags`
- `input_schema`
- `risk_level`
- `requires_confirmation`
- `side_effects`
- `executor_name`

This is the bridge between conversational reasoning and concrete execution.

### 5. Execution Policy

The policy layer decides what happens after routing:

- direct answer without tools
- ask one clarifying question
- ask for confirmation
- auto-run a safe tool
- refuse or defer unsupported work

This keeps risk logic and UX rules out of the router and out of the tool executor.

### 6. Tool Executor

The executor owns the mechanics of invoking skills and helper routines. It should adapt a tool call into the appropriate local implementation:

- Skill 3 adapter
- Skill 4 adapter
- Skill 5 adapter
- Skill 1 and Skill 2 rebuild entrypoints
- output inspection helpers
- student listing helpers
- graph validation helpers

The executor should return structured result envelopes that are suitable for both logging and response synthesis.

### 7. Response Synthesizer

The synthesizer converts internal decisions and tool results into a natural reply. It should answer like an assistant, not like a raw JSON dumper.

Responses should include:

- what the agent understood
- what it did, if it ran anything
- the important findings
- a next-step suggestion when useful

For confirmation prompts, the synthesizer should clearly explain impact, duration, and what artifacts may change.

## Session Model

`AgentSession` should evolve into a first-class conversation state container with four groups of fields.

### Conversation State

- recent user and assistant turns
- last interpreted intent
- last response summary
- pending clarification question
- pending confirmation action

### User Preferences

- preference for fewer questions
- preference for more explanation versus more action
- any session-local choices that affect decision thresholds

### Working Context

- active `student_id` if any
- active mode such as `demo`, `graph`, or `custom_profile_mode`
- last used artifacts
- last selected resource bundle
- last recommendation result handles

### Safety State

- whether there is an unconfirmed high-risk action
- a short confirmation token or action id
- whether the session is in fallback mode after a failure

The session should be lightweight and local, but explicit enough that a later API frontend could serialize it.

## Tooling Model and Risk Tiers

The system should classify tools by risk and side effects rather than by skill number alone.

### Level A: Safe Auto-Run

These tools can run automatically when confidence is high:

- mentor/project/teammate recommendation flows using Skill 3, Skill 4, and Skill 5
- explanation of an existing recommendation
- read-only profile inspection
- listing available students
- artifact inspection
- graph-mode diagnostics that only read files

### Level B: Confirm Before Run

These tools need explicit user confirmation before execution:

- rebuilding normalized profiles through Skill 1 workflows
- rebuilding or regenerating the Skill 2 academic graph
- any batch action that refreshes processed outputs
- any tool that may overwrite artifacts or take significant time

The confirmation should be natural language, for example:

> I think this requires rebuilding the Skill 2 graph. That will refresh processed artifacts and may take several minutes. Do you want me to continue?

### Level C: Restricted or Future Admin Tools

This tier is reserved for future destructive or operationally risky actions such as bulk cleanup or deletion. The first implementation can define the category without exposing any such tools yet.

## Turn Lifecycle

Every chat turn should use the same state machine.

1. The frontend receives a user message.
2. The agent core loads the session and working context.
3. The intent router emits structured intent and confidence.
4. The execution policy chooses one of:
   - answer directly
   - ask a clarifying question
   - ask for confirmation
   - execute a tool
5. The tool executor performs any approved action.
6. The response synthesizer produces the assistant reply.
7. The session is updated for the next turn.

This state machine replaces the current implicit behavior where free-form input usually falls into one recommendation path.

## Representative Interaction Examples

### Recommendation Request

User:

> I want a mentor in trustworthy AI and NLP.

System behavior:

- router classifies `recommend`
- policy finds no need for confirmation
- executor runs the recommendation toolchain
- synthesizer returns top findings and rationale

### Clarification Case

User:

> Recommend something low-commitment for me.

System behavior:

- router identifies missing information such as time budget or target area
- policy asks one minimal question
- session stores pending clarification
- next user message resumes the same planned path

### Read-Only Debug Case

User:

> Why does graph mode return nothing for jamie-taylor-00008?

System behavior:

- router classifies `debug`
- policy selects read-only diagnostic tools
- executor checks processed graph presence, bundle alignment, and recent artifacts
- synthesizer explains the likely failure and proposes the next step

### High-Risk Rebuild Case

User:

> Rebuild the graph using the latest processed profiles.

System behavior:

- router classifies `rebuild`
- policy identifies a Level B action
- synthesizer asks for confirmation
- only after user confirms does the executor invoke the Skill 2 rebuild tool

## File and Module Plan

The first implementation should preserve the current adapters and skill code while refactoring the agent layer around them.

### New or Split Modules

- `progrec_agent/agent_core.py`
- `progrec_agent/intent_router.py`
- `progrec_agent/execution_policy.py`
- `progrec_agent/tool_registry.py`
- `progrec_agent/tool_executor.py`
- `progrec_agent/response_synthesizer.py`

### Existing Modules Likely to Change

- `progrec_agent/repl.py`
- `progrec_agent/session.py`
- `progrec_agent/orchestrator.py`
- `progrec_agent/tools.py`
- `progrec_agent/prompts.py`
- `progrec_agent/llm_client.py`

### Modules That Should Mostly Stay Stable

- `progrec_agent/adapters/skill1_adapter.py`
- `progrec_agent/adapters/skill2_adapter.py`
- `progrec_agent/adapters/skill3_adapter.py`
- `progrec_agent/adapters/skill4_adapter.py`
- `progrec_agent/adapters/skill5_adapter.py`
- the actual Skill 1 through Skill 5 trees outside `progrec_agent/`

## Error Handling

The agent should degrade gracefully when information or infrastructure is missing.

### No LLM Available

If no API key is configured, the agent should still support a reduced local mode:

- simpler routing heuristics
- narrower intent coverage
- explicit user messaging that the system is using fallback reasoning

### Tool Failure

If a tool fails:

- the executor returns a structured error
- the session records the failure context
- the synthesizer explains the failure in natural language
- the response should suggest the most useful next action, such as checking graph artifacts or confirming a rebuild

### Ambiguous Intent

If confidence is below threshold:

- ask one concise clarifying question
- avoid speculative tool execution
- keep the question narrow enough to unblock action in the next turn

### Confirmation Timeout or Drift

If the user changes topic instead of answering a confirmation request:

- the old pending action should be invalidated or explicitly superseded
- the new message should be routed fresh rather than silently applying the old confirmation

## Testing Strategy

Testing should move from single-function checks toward conversation-flow validation.

### Unit Tests

Test each decision component in isolation:

- router intent classification
- policy decisions for confidence and risk
- tool registry metadata
- session transition helpers

### Integration Tests with Mocked Tools

Run full-turn tests through `agent_core` with fake tool results:

- direct recommendation flow
- clarification then resume
- confirmation then execute
- confirmation declined
- debug request with read-only diagnostics

### Repository Integration Tests

Keep a smaller number of tests wired to real repository resources:

- recommendation path still integrates correctly with Skill 3, Skill 4, and Skill 5
- graph-mode routing still respects existing alignment guardrails
- rebuild flows only execute after confirmation

### Golden Conversation Tests

Store representative multi-turn scripts and expected action traces. This gives the team confidence that the assistant still "feels" correct after refactors.

## Delivery Phases

### Phase 1: Extract Agent Core Skeleton

Create the new core modules and move turn-handling logic out of `repl.py`. Preserve current recommendation behavior while changing the structure.

### Phase 2: Toolify Existing Capabilities

Wrap current recommendation and inspection actions in a unified tool registry and executor. Start routing across recommendation, explanation, inspect, and debug paths.

### Phase 3: Add Confirmation and Stronger Session Flow

Introduce pending confirmation actions, improved clarification state, and richer context reuse across turns.

### Phase 4: Expand Repository-Local Generality

Broaden the tool set so the agent can explain outputs, diagnose graph problems, and recommend rebuild actions without becoming a general-purpose external agent.

## Success Criteria

The first milestone is successful when all of the following are true:

- users can interact in natural language without typing `recommend`
- the system no longer defaults every free-form request into Skill 3 -> Skill 4 -> Skill 5
- the agent can distinguish recommendation, explanation, inspection, debugging, and rebuild intents
- high-impact Skill 1 and Skill 2 actions require explicit confirmation
- the REPL is only a frontend and the core logic is reusable elsewhere

## Open Implementation Notes

- The first version should prefer deterministic, testable routing scaffolding over overly flexible prompting.
- The system should keep existing student alignment safeguards intact, especially around Skill 3, Skill 4, and Skill 5 handoff boundaries.
- The response layer should stay conversational, but all execution decisions should remain inspectable through trace data for debugging and tests.
