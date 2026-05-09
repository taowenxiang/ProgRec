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

## Notes

- The repository already has a GitHub remote configured at `origin`.
- Local cache files and editor/system artifacts are ignored via `.gitignore`.
- Historical project outputs such as JSON, NPY, ZIP, and PDF files are kept as tracked artifacts unless you decide to move them out of version control later.
