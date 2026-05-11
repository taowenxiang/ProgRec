INTENT_UNDERSTANDING_PROMPT = """
You are StuRec's planning layer.
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
