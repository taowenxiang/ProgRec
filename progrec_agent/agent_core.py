from __future__ import annotations

import uuid
from pathlib import Path

from progrec_agent.agent_schema import PendingConfirmation
from progrec_agent.intent_router import route_user_message
from progrec_agent.profile_enricher import build_profile_if_needed
from progrec_agent.response_synthesizer import synthesize_reply
from progrec_agent.tool_executor import ToolExecutor
from progrec_agent.tool_registry import get_tool


class AgentCore:
    def __init__(self, *, repo_root: Path, temp_dir: Path, executor=None, llm_client=None) -> None:
        self.repo_root = repo_root
        self.temp_dir = temp_dir
        self.llm_client = llm_client
        self.executor = executor or ToolExecutor(repo_root=repo_root, temp_dir=temp_dir)

    def _route_with_fallback(self, session, user_text: str):
        if self.llm_client is None:
            return route_user_message(user_text, llm_client=None, session=session)
        try:
            return route_user_message(user_text, llm_client=self.llm_client, session=session)
        except Exception as exc:
            session.decision_trace.append(f"LLM routing failed; returned safe blocked response. Error: {exc}")
            return route_user_message(user_text, llm_client=None, session=session)

    def _build_profile_with_fallback(self, session, user_text: str):
        if self.llm_client is None:
            return build_profile_if_needed(user_text, None)
        try:
            return build_profile_if_needed(user_text, self.llm_client)
        except Exception as exc:
            session.decision_trace.append(f"LLM profile drafting failed; used local fallback. Error: {exc}")
            return build_profile_if_needed(user_text, None)

    def handle_message(self, session, user_text: str) -> str:
        normalized = user_text.strip().lower()
        session.conversation_history.append({"role": "user", "content": user_text})

        if session.pending_confirmation_action and normalized in {"no", "n", "cancel"}:
            session.clear_pending_confirmation()
            reply = "Okay, I won't run that rebuild. If you want, I can inspect the current artifacts instead."
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="answer_only",
                tool_name="",
                tool_arguments={},
                result_summary=reply,
            )
            return reply

        if session.pending_confirmation_action and normalized in {"yes", "y", "confirm", "continue"}:
            pending = dict(session.pending_confirmation_action)
            session.clear_pending_confirmation()
            result = self.executor.execute(pending["tool_name"], dict(pending["arguments"]), session=session)
            reply = synthesize_reply(session=session, user_text=user_text, decision=None, result=result)
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="execute_tool",
                tool_name=str(pending["tool_name"]),
                tool_arguments=dict(pending["arguments"]),
                result_summary=reply,
            )
            return reply

        decision = self._route_with_fallback(session, user_text)
        session.set_last_router_decision(decision)
        if decision.answer_only:
            reply = synthesize_reply(session=session, user_text=user_text, decision=decision, result=None)
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="answer_only",
                tool_name="",
                tool_arguments={},
                result_summary=reply,
            )
            return reply

        if decision.needs_clarification and decision.clarification_question:
            session.set_pending_clarification(
                [{"key": "followup", "question": decision.clarification_question}],
                user_text,
            )
            session.decision_trace.append("Asked a clarification question before running tools.")
            session.conversation_history.append({"role": "assistant", "content": decision.clarification_question})
            session.set_last_response_summary(decision.clarification_question)
            session.set_last_action(
                kind="clarify_then_wait",
                tool_name="",
                tool_arguments={},
                result_summary=decision.clarification_question,
            )
            return decision.clarification_question

        tool_name = decision.tool_name or (decision.candidate_tools[0] if decision.candidate_tools else "")
        tool_meta = get_tool(tool_name) if tool_name else {}

        if tool_meta.get("risk_level") == "confirm":
            pending = PendingConfirmation(
                action_id=str(uuid.uuid4()),
                tool_name=tool_name,
                arguments=dict(decision.tool_arguments),
                prompt="I think this requires rebuilding the Skill 2 graph. That may refresh artifacts and take a few minutes. Do you want me to continue?",
            )
            session.set_pending_confirmation(pending)
            session.decision_trace.append(f"Requested confirmation before `{tool_name}`.")
            session.conversation_history.append({"role": "assistant", "content": pending.prompt})
            session.set_last_response_summary(pending.prompt)
            session.set_last_action(
                kind="confirm",
                tool_name=tool_name,
                tool_arguments=dict(decision.tool_arguments),
                result_summary=pending.prompt,
            )
            return pending.prompt

        if tool_name:
            if tool_name == "recommend_full_pipeline" and session.student_profile is None:
                skill_profile, agent_profile = self._build_profile_with_fallback(session, user_text)
                session.set_student_profile(skill_profile)
                session.set_agent_profile(agent_profile.__dict__)
            result = self.executor.execute(tool_name, dict(decision.tool_arguments), session=session)
            reply = synthesize_reply(session=session, user_text=user_text, decision=decision, result=result)
            session.decision_trace.append(f"Executed `{tool_name}` for intent `{decision.intent}`.")
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            session.set_last_action(
                kind="execute_tool",
                tool_name=tool_name,
                tool_arguments=dict(decision.tool_arguments),
                result_summary=reply,
            )
            return reply

        reply = "I need a bit more detail before I can decide what to run."
        session.conversation_history.append({"role": "assistant", "content": reply})
        session.set_last_response_summary(reply)
        session.set_last_action(
            kind="answer_only",
            tool_name="",
            tool_arguments={},
            result_summary=reply,
        )
        return reply
