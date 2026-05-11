from __future__ import annotations


def synthesize_reply(*, session, user_text: str, decision, result) -> str:
    if not result.ok:
        return f"I tried to run `{result.tool_name}`, but it failed: {result.error}"
    return f"I handled your request with `{result.tool_name}`. tool_name={result.tool_name}"
