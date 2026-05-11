INTENT_UNDERSTANDING_PROMPT = """
You are ProgRec's planning layer.
Return strict JSON with:
- goal
- research_direction
- desired_outcomes
- constraints
- preferences
- skill_profile
""".strip()


CLARIFICATION_PROMPT = """
Given the current agent profile, return strict JSON with:
- need_clarification
- clarification_questions
- tool_plan
""".strip()


ROUTER_PROMPT = """
You are the routing layer for ProgRec.
Return strict JSON with:
- intent
- confidence
- candidate_tools
- needs_clarification
- clarification_question
- reasoning_summary
""".strip()
