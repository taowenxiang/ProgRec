from __future__ import annotations

import os
from pathlib import Path

from progrec_agent.agent_core import AgentCore
from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState
from progrec_agent.llm_client import LLMClient, LLMConfig
from progrec_agent.session import AgentSession

CHAT_INTRO = """ProgRec Agent

I help you explore mentor, project, and teammate recommendations based on your academic interests and goals.

You can talk to me naturally. For example:
- Find me an NLP mentor.
- I'm interested in trustworthy AI and I only have 4 hours per week.
- Show me the current profile of the top mentor.
- Why did you recommend this mentor?
- Check whether my graph-mode artifacts are valid.

If your question is outside the recommendation workflow, I'll tell you clearly instead of guessing.
"""


def _build_llm_client_from_env() -> LLMClient | None:
    api_key = (os.getenv("PROGREC_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    model = (os.getenv("PROGREC_AGENT_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    endpoint = (
        os.getenv("PROGREC_AGENT_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.openai.com/v1/responses"
    ).strip()
    return LLMClient(LLMConfig(model=model, api_key=api_key, endpoint=endpoint))

def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".progrec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    llm_client = _build_llm_client_from_env()
    if llm_client is None:
        raise RuntimeError(
            "LLM configuration is required for the conversational REPL. "
            "Set PROGREC_AGENT_API_KEY or OPENAI_API_KEY before starting it."
        )
    use_v2 = (os.getenv("PROGREC_AGENT_V2") or "").strip() == "1"
    session = AgentSession(temp_dir=temp_dir)
    core = AgentCore(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client)
    core_v2 = AgentCoreV2(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client) if use_v2 else None
    dialog_state = DialogState() if use_v2 else None
    print(CHAT_INTRO)
    while True:
        command = input("> ").strip()
        if command.lower() in {"exit", "quit"}:
            return 0
        if not command:
            continue
        if use_v2 and core_v2 is not None and dialog_state is not None:
            reply, dialog_state = core_v2.handle_message(dialog_state, command)
            print(reply)
        else:
            print(core.handle_message(session, command))


if __name__ == "__main__":
    raise SystemExit(main())
