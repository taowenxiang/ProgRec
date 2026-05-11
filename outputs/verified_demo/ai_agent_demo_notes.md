# ProgRec AI Agent Demo Notes

## Suggested Live Demo

1. Start the CLI:

```bash
export OPENAI_API_KEY=your_key_here
python3 -m progrec_agent.repl
```

2. Enter an initial request:

```text
I want an NLP mentor with easy onboarding and a low weekly time commitment.
```

3. If the agent asks for clarification, answer briefly.

4. Show the first recommendation response and then run:

```text
show trace
```

5. Enter a follow-up preference update:

```text
Recommend again, but care more about teammate complementarity than mentor prestige.
```

6. Run `show trace` again to highlight:

- natural-language profile drafting
- planner decisions
- rerun reasoning when result coverage is weak

## Demo Framing

Use this demo to emphasize that ProgRec is no longer a fixed recommendation pipeline.
It is now an AI agent that plans over the existing five SNA skills, adapts its strategy, and explains its decisions.
