from __future__ import annotations

from progrec_agent.nlu.validators import build_safe_fallback_frame, validate_parse_payload

SEMANTIC_PARSE_PROMPT = """
Return strict JSON describing the user's request.
Do not choose tools.
Do not ask clarification questions.
Do not invent facts.
""".strip()


def parse_user_message(user_text: str, *, dialog_state, llm_client):
    if llm_client is None:
        return build_safe_fallback_frame("missing_llm")
    payload = llm_client.complete_json(
        f"{SEMANTIC_PARSE_PROMPT}\nDialog state: {dialog_state}\nUser message: {user_text}"
    )
    return validate_parse_payload(dict(payload))
