from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState, ExecutionContext, PendingQuestion
from progrec_agent.llm_client import LLMClient, LLMConfig


def _dialog_state_from_payload(payload: dict[str, object]) -> DialogState:
    pending_question_payload = payload.get("pending_question")
    execution_context_payload = payload.get("execution_context")
    pending_question = None
    if isinstance(pending_question_payload, dict):
        pending_question = PendingQuestion(**pending_question_payload)
    execution_context = ExecutionContext()
    if isinstance(execution_context_payload, dict):
        execution_context = ExecutionContext(**execution_context_payload)
    return DialogState(
        task=str(payload.get("task", "")),
        goal=str(payload.get("goal", "")),
        resolved_slots=dict(payload.get("resolved_slots", {}) or {}),
        candidate_slots=dict(payload.get("candidate_slots", {}) or {}),
        required_slots=list(payload.get("required_slots", []) or []),
        missing_slots=list(payload.get("missing_slots", []) or []),
        pending_question=pending_question,
        conflicts=list(payload.get("conflicts", []) or []),
        execution_context=execution_context,
        clarification_turn_count=int(payload.get("clarification_turn_count", 0) or 0),
        last_user_turn=str(payload.get("last_user_turn", "")),
        last_agent_turn=str(payload.get("last_agent_turn", "")),
    )


def run_agent_turn(*, repo_root: Path, dialog_state_payload: dict[str, object], runtime_context, user_text: str) -> dict[str, object]:
    llm_client = LLMClient(
        LLMConfig(
            model=runtime_context.model,
            api_key=runtime_context.api_key,
            endpoint=runtime_context.base_url,
        )
    )
    state = _dialog_state_from_payload(dialog_state_payload)
    with tempfile.TemporaryDirectory(prefix="progrec_agent_turn_") as tmp_dir:
        agent = AgentCoreV2(
            repo_root=repo_root,
            temp_dir=Path(tmp_dir),
            llm_client=llm_client,
        )
        reply_text, next_state = agent.handle_message(state, user_text)
    return {
        "reply_text": reply_text,
        "structured_result": {"last_result_handle": next_state.execution_context.result_handle},
        "dialog_state_payload": asdict(next_state),
    }
