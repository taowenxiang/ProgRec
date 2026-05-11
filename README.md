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

## ProgRec Conversational Agent CLI

The repository includes a chat-first agent inside `progrec_agent/`.
It keeps the existing multi-skill recommendation core, but adds:

- chat-first natural-language requests
- LLM-first routing and bounded conversation handling
- clarification when intent is ambiguous
- confirmation before graph/profile rebuild actions
- repository-local debugging and inspection help

Set the model configuration before running:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_BASE_URL=https://api.openai.com
export OPENAI_MODEL=gpt-4.1-mini
python3 -m progrec_agent.repl
```

You can also use the ProgRec-specific names instead:

```bash
export PROGREC_AGENT_API_KEY=your_key_here
export PROGREC_AGENT_BASE_URL=https://your-compatible-endpoint
export PROGREC_AGENT_MODEL=gpt-4.1-mini
python3 -m progrec_agent.repl
```

The conversational REPL requires an LLM API key. Without one, startup stops with a configuration error instead of falling back to pretend-smart local routing.

Example prompts:

- `Find me an NLP mentor.`
- `I'm interested in trustworthy AI and only have 4 hours per week.`
- `Show me the current profile of the top mentor.`
- `Why did you recommend this mentor?`
- `Check whether my graph-mode artifacts are valid.`

If you ask a question outside the recommendation workflow, the agent says so clearly instead of guessing.

## Agent-level execution

See [`AGENTS.md`](AGENTS.md) for the full multi-skill Agent contract, stable skill identifiers, demo vs graph mode, and debugging.

Quick start (non-interactive pipeline):

```bash
python3 progrec_agent/run_agent.py \
  --mode demo \
  --output outputs/final_recommendation_demo.json
```

Use `--student-id <id>` when the default (first id in the mode’s student bundle) is not what you want. Graph mode requires a built `academic_graph.json` under `skill2_handoff/regenerate_kit/data/processed/` and routes **Skill 3 and Skill 4** through the same processed student, mentor, and graph files (see `AGENTS.md`).

### Verified Agent Run (graph)

Documented example student and frozen outputs: [`outputs/verified_demo/README.md`](outputs/verified_demo/README.md).

```bash
python3 progrec_agent/run_agent.py \
  --mode graph \
  --student-id jamie-taylor-00008 \
  --top-k 10 \
  --output outputs/final_recommendation_graph.json \
  --artifacts-dir outputs/run_artifacts_graph
python3 progrec_agent/inspect_output.py --output outputs/final_recommendation_graph.json
```

## Notes

- The repository already has a GitHub remote configured at `origin`.
- Local cache files and editor/system artifacts are ignored via `.gitignore`.
- Historical project outputs such as JSON, NPY, ZIP, and PDF files are kept as tracked artifacts unless you decide to move them out of version control later.
