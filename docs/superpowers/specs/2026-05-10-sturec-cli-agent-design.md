# StuRec CLI Agent Design

**Date:** 2026-05-10

## Goal

Build a first-version interactive CLI agent for StuRec that orchestrates the existing five skills end to end. The agent should let a user either choose an existing `student_id` from the dataset or manually enter a student profile, then produce mentor, project, and teammate recommendations with explanation paths that reflect the current Skill 1-5 pipeline.

## Scope

This design covers a CLI-only agent layer that sits on top of the existing repository artifacts and Python modules.

In scope:
- Interactive REPL entrypoint
- Session state across commands
- Orchestration across Skill 1-5
- Support for both dataset-backed and custom manual profiles
- Human-readable terminal output
- Tests for adapters, session behavior, orchestration, and CLI smoke flows

Out of scope:
- Free-form natural language command parsing
- Web UI or chat UI
- Rebuilding or redesigning the core ranking algorithms inside Skills 3-5
- Writing custom manual students back into the Skill 2 graph
- Converting every existing skill into a unified installable package

## Recommended Architecture

The agent should be implemented as a new package directory `sturec_agent/` that acts as a lightweight orchestration layer above the existing five skills.

### Proposed package structure

- `sturec_agent/repl.py`
  Handles the interactive command loop and user prompts.
- `sturec_agent/session.py`
  Stores the current student profile, mode, recent results, temporary file paths, and execution metadata.
- `sturec_agent/orchestrator.py`
  Runs the five-skill pipeline as one agent action and returns a normalized result object for display and inspection.
- `sturec_agent/render.py`
  Formats summaries for terminal output, including top mentors, projects, teammates, and mentor drill-down views.
- `sturec_agent/models.py`
  Defines shared TypedDict or dataclass structures for session state and normalized outputs.
- `sturec_agent/adapters/skill1_adapter.py`
  Normalizes manual input into the Skill 1 compatible schema.
- `sturec_agent/adapters/skill2_adapter.py`
  Resolves graph and standardized resource paths from the two Skill 2 resource layouts.
- `sturec_agent/adapters/skill3_adapter.py`
  Runs mentor discovery using existing Skill 3 Python APIs.
- `sturec_agent/adapters/skill4_adapter.py`
  Runs project and teammate discovery using existing Skill 4 pipeline logic.
- `sturec_agent/adapters/skill5_adapter.py`
  Produces final ranked output from Skill 3 and Skill 4 results using the existing Skill 5 script.

This structure preserves the assignment requirement that the five skills remain distinct while giving the agent a clear home for session, command, and formatting logic.

## Command Model

The first version should provide a small fixed command set instead of free-form command understanding.

Supported commands:
- `recommend`
- `show mentor <id>`
- `show profile`
- `restart`
- `help`
- `exit`

### `recommend`

Starts a guided recommendation flow.

The agent asks the user to choose one of two entry modes:
- existing `student_id`
- manual student profile entry

For `student_id` mode:
- prompt for `student_id`
- load the corresponding standardized profile
- print a short profile summary
- run the recommendation pipeline

For manual profile mode:
- prompt for `grade`
- prompt for `major`
- prompt for comma-separated `skills`
- prompt for comma-separated `interests`
- prompt for `experience_summary`
- prompt for `availability`
- optionally prompt for `resume_text`
- normalize the profile
- print a short summary for confirmation
- run the recommendation pipeline

After execution, the agent should print:
- current mode
- top mentors
- top projects
- top teammates
- a brief Skill 1-5 execution status summary
- a hint to use `show mentor <id>`

### `show mentor <id>`

Shows details for one mentor from the latest session result without recomputing the pipeline.

The output should include:
- mentor name and id
- final rank and final score
- Skill 3 topic/graph signals and reasons
- Skill 4 related projects
- Skill 4 related teammates
- Skill 5 explanation text

### `show profile`

Displays the currently loaded student profile and session mode.

### `restart`

Clears the session, removes temporary result files created by the agent, and returns the REPL to its initial state.

### `help`

Prints a concise command reference.

### `exit`

Exits the REPL cleanly.

## Unified Student Profile Contract

The agent should use one normalized internal student profile structure regardless of input source:

```json
{
  "student_id": "string",
  "grade": "string",
  "major": "string",
  "skills": ["string"],
  "interests": ["string"],
  "experience_summary": "string",
  "availability": "string",
  "resume_text": "string"
}
```

The first seven fields must remain compatible with the existing Skill 1 / Skill 2 / Skill 3 / Skill 4 / Skill 5 contracts. `resume_text` is agent-local metadata and should not be required downstream.

## Two Execution Modes

The agent should explicitly support two operating modes because the current skills do not treat new students and existing graph students the same way.

### Dataset mode

Used when the user starts from an existing `student_id`.

Characteristics:
- uses the current Skill 2 standardized student bundle
- keeps student namespace aligned with Skill 3 and Skill 4
- provides the most faithful end-to-end demonstration of the five-skill system

### Custom profile mode

Used when the user enters a new profile manually.

Characteristics:
- creates a temporary `student_id`, such as `cli-custom-<timestamp>`
- does not require the student to already exist in the Skill 2 graph
- still uses Skill 2 mentor/student/graph resources as context
- relies more on topic/profile signals than graph-node identity
- should be labeled clearly in the output as `custom_profile_mode`

The agent should surface the active mode in results so demo users understand whether graph identity was strict or approximate.

## Skill Integration Strategy

### Skill 1 integration

The repository currently includes Skill 1 artifacts and schema documentation but not a clearly packaged runtime entrypoint for live profile extraction.

The agent should therefore implement a lightweight adapter that:
- normalizes manual strings
- splits comma-separated fields
- lowercases and de-duplicates tags
- fills safe defaults for missing values
- optionally uses `resume_text` to enrich `skills`, `interests`, or `experience_summary` in a minimal way

For dataset mode, using an existing normalized student profile counts as reusing Skill 1 output.

### Skill 2 integration

The agent should read existing Skill 2 outputs rather than rebuild the graph by default.

The Skill 2 adapter should resolve resources from these preferred locations:
1. `skill2_handoff/outputs/...`
2. `skill2_handoff/regenerate_kit/data/processed/...`
3. `data/processed/...`

It should return:
- student bundle path
- mentor bundle path
- graph path if available
- embedding paths if available
- a resolved resource mode string for debugging

### Skill 3 integration

Skill 3 already exposes importable Python logic through:
- `load_standardized_resources(...)`
- `rank_mentors_for_student(...)`

The agent should prefer direct Python API calls over subprocess.

In dataset mode:
- use the standardized student already present in the bundle

In custom profile mode:
- pass the temporary normalized profile directly to mentor ranking
- still load mentors and graph resources from Skill 2

This avoids forcing manual users into the Skill 2 student namespace.

### Skill 4 integration

Skill 4 already exposes internal discovery logic and a CLI wrapper.

The agent should use:
- a higher-level path compatible with existing CLI config in dataset mode when practical
- a lower-level path for custom profile mode, so it can call project and teammate discovery without requiring the target student to already exist in the standardized student bundle

This is important because the default Skill 4 CLI path is stricter about `target_student_id` alignment.

### Skill 5 integration

Skill 5 is currently most stable as a script entrypoint with file-based IO.

The agent should treat it as the final ranking stage by:
- writing Skill 3 and Skill 4 intermediate outputs to temporary JSON files
- invoking the Skill 5 script
- reading the produced final JSON back into session state

This is the safest short-term option because the Skill 5 directory name contains a hyphen and is not currently set up as a normal Python package import path.

## Session Design

The session object should persist enough data to support drill-down commands without rerunning the pipeline.

Required session fields:
- `mode`
- `student_profile`
- `resource_context`
- `skill3_result`
- `skill4_result`
- `skill5_result`
- `latest_summary`
- `temporary_paths`

`show mentor <id>` should resolve data from session state only. It should not call any skill again unless the session is empty and the agent explicitly asks the user to run `recommend` first.

## Rendering Requirements

The terminal output should emphasize readability over raw JSON dumps.

After `recommend`, print:
- a short session header
- mode and target student id
- top mentor table or ranked list
- top project list
- top teammate list
- skill status summary

After `show mentor <id>`, print:
- mentor identity
- final score and rank
- evidence summary from Skill 3
- projects from Skill 4
- teammates from Skill 4
- final explanation from Skill 5

The CLI should remain deterministic and text-based so it is easy to demo and test.

## Error Handling

The agent should fail gracefully and clearly.

Cases to handle explicitly:
- unknown command
- unknown `student_id`
- no active session for `show mentor <id>` or `show profile`
- mentor id not found in the latest recommendation
- missing Skill 2 graph file
- Skill 5 script failure
- malformed intermediate JSON

Behavior rules:
- user input errors should produce concise guidance and keep the REPL alive
- pipeline execution failures should preserve enough error context to debug the failing stage
- missing graph data should degrade to weaker recommendations instead of crashing when existing skills already support fallback behavior

## Testing Strategy

### Unit tests

Add tests for:
- manual profile normalization in `skill1_adapter`
- session state set/reset behavior
- command parsing and command routing
- renderer formatting for mentor detail views

### Integration tests

Add tests for:
- dataset mode end-to-end orchestration using an existing `student_id`
- custom profile mode end-to-end orchestration using a synthetic manual profile
- `show mentor <id>` against cached session results

### CLI smoke tests

Add a small REPL interaction test that simulates:
- `help`
- `recommend` with dataset mode
- `recommend` with manual mode
- `restart`
- `exit`

The goal is not exhaustive conversational testing. The goal is to prove that the first CLI agent works as an interactive wrapper around the five-skill pipeline.

## Non-Goals

The first version should not attempt to solve these:
- general natural language command understanding
- graph mutation for custom students
- full conversation memory beyond the active REPL session
- Web frontend polish
- algorithm changes to Skill 3, Skill 4, or Skill 5 core formulas

Keeping these out of scope is what makes the first version deliverable.

## Implementation Notes

The safest implementation sequence is:
1. add normalized models and session state
2. add the manual-profile Skill 1 adapter
3. add Skill 2 resource resolution
4. wire Skill 3 dataset mode
5. wire Skill 4 dataset mode
6. wire Skill 5 final ranking
7. add custom profile mode support
8. add REPL rendering and drill-down commands
9. add tests and README usage notes

This order minimizes risk by getting one stable dataset-backed path working first, then layering in the more flexible custom profile path.

## Success Criteria

The CLI agent is successful when:
- a user can launch `python -m sturec_agent.repl`
- run a full recommendation session from either an existing `student_id` or manual profile input
- receive mentor, project, and teammate recommendations
- inspect a recommended mentor with `show mentor <id>`
- restart and run another session
- do all of the above without editing the five underlying skills

## Open Design Decisions Resolved

The following decisions are fixed for the first implementation:
- interaction style: REPL, not one-shot CLI
- entry modes: both existing `student_id` and manual input
- manual mode: structured input plus optional `resume_text`
- session behavior: persistent fixed commands, not free-form follow-up parsing
- orchestration style: hybrid agent layer above the five skills
- integration style: Python API where clean, subprocess where safer
