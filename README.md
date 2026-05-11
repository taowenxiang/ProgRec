# ProgRec

Course project repository for the recommendation pipeline handoff, including:

- `skill1_handoff/`: normalized student profile artifacts
- `skill2_handoff/`: graph-building outputs and the regenerate kit
- `skill3_mentor_discovery/`: mentor retrieval and ranking logic
- `tests/`: unit tests for the Skill 3 pipeline

## Repository Structure

```text
ProgRec/
├── skill1_handoff/
├── skill2_handoff/
│   ├── outputs/
│   └── regenerate_kit/
├── skill3_mentor_discovery/
├── tests/
├── PLAN.md
└── FinalProjectGuidance.pdf
```

## Quick Start

Run mentor discovery from the repository root:

```bash
python3 skill3_mentor_discovery/run_skill3.py --student-id <student_id> --top-k 5
```

Run the evaluation script:

```bash
python3 -m skill3_mentor_discovery.evaluate
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## StuRec Agent CLI

Run the interactive CLI agent from the repository root:

```bash
python3 -m sturec_agent.repl
```

The first version supports two recommendation entry modes:

- existing `student_id` from the current standardized student bundle
- manual profile entry with structured fields and optional `resume_text`

Supported commands:

- `recommend`
- `show mentor <id>`
- `show profile`
- `restart`
- `help`
- `exit`

Manual profile runs are labeled `custom_profile_mode`. They still use the existing Skill 2-5 resources, but the student is treated as a temporary profile instead of a graph-native student node.

## StuRec AI Agent CLI

The repository now also includes an AI-agent upgrade path inside `sturec_agent/`.
This version keeps the existing multi-skill recommendation core, but adds:

- natural-language user input
- LLM-based profile drafting when an API key is available
- planner-driven clarification and execution decisions
- decision traces and bounded rerun behavior

Set an API key before running if you want LLM-backed profile drafting:

```bash
export OPENAI_API_KEY=your_key_here
python3 -m sturec_agent.repl
```

Without an API key, the CLI still starts and falls back to a lightweight local profile-drafting path.

Example prompts:

- `I want a mentor in trustworthy AI and NLP.`
- `I only have three hours per week.`
- `Recommend again, but prioritize teammate complementarity.`

Useful commands:

- `show profile`
- `show trace`
- `show mentor <id>`
- `restart`

## Agent-level execution

See [`AGENTS.md`](AGENTS.md) for the full multi-skill Agent contract, stable skill identifiers, demo vs graph mode, and debugging.

Quick start (non-interactive pipeline):

```bash
python3 sturec_agent/run_agent.py \
  --mode demo \
  --output outputs/final_recommendation_demo.json
```

Use `--student-id <id>` when the default (first id in the mode’s student bundle) is not what you want. Graph mode requires a built `academic_graph.json` under `skill2_handoff/regenerate_kit/data/processed/` and routes **Skill 3 and Skill 4** through the same processed student, mentor, and graph files (see `AGENTS.md`).

### Verified Agent Run (graph)

Documented example student and frozen outputs: [`outputs/verified_demo/README.md`](outputs/verified_demo/README.md).

```bash
python3 sturec_agent/run_agent.py \
  --mode graph \
  --student-id jamie-taylor-00008 \
  --top-k 10 \
  --output outputs/final_recommendation_graph.json \
  --artifacts-dir outputs/run_artifacts_graph
python3 sturec_agent/inspect_output.py --output outputs/final_recommendation_graph.json
```

## Notes

- The repository already has a GitHub remote configured at `origin`.
- Local cache files and editor/system artifacts are ignored via `.gitignore`.
- Historical project outputs such as JSON, NPY, ZIP, and PDF files are kept as tracked artifacts unless you decide to move them out of version control later.
