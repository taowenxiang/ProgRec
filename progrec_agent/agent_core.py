from __future__ import annotations

import uuid
from pathlib import Path

from progrec_agent.agent_schema import PendingConfirmation
from progrec_agent.execution_policy import choose_action
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

    def handle_message(self, session, user_text: str) -> str:
        normalized = user_text.strip().lower()
        session.conversation_history.append({"role": "user", "content": user_text})

        if session.pending_confirmation_action and normalized in {"yes", "y", "confirm", "continue"}:
            pending = dict(session.pending_confirmation_action)
            session.clear_pending_confirmation()
            result = self.executor.execute(pending["tool_name"], dict(pending["arguments"]), session=session)
            reply = synthesize_reply(session=session, user_text=user_text, decision=None, result=result)
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            return reply

        decision = route_user_message(user_text, llm_client=self.llm_client, session=session)
        session.set_last_router_decision(decision)
        tool_name = decision.candidate_tools[0] if decision.candidate_tools else ""
        tool_meta = get_tool(tool_name) if tool_name else {}
        action = choose_action(decision, tool_name=tool_name, tool_meta=tool_meta)

        if action["kind"] == "clarify":
            session.set_pending_clarification([{"key": "followup", "question": action["question"]}], user_text)
            session.decision_trace.append("Asked a clarification question before running tools.")
            session.conversation_history.append({"role": "assistant", "content": action["question"]})
            session.set_last_response_summary(action["question"])
            return action["question"]

        if action["kind"] == "confirm":
            pending = PendingConfirmation(
                action_id=str(uuid.uuid4()),
                tool_name=tool_name,
                arguments={},
                prompt="I think this requires rebuilding the Skill 2 graph. That may refresh artifacts and take a few minutes. Do you want me to continue?",
            )
            session.set_pending_confirmation(pending)
            session.decision_trace.append(f"Requested confirmation before `{tool_name}`.")
            session.conversation_history.append({"role": "assistant", "content": pending.prompt})
            session.set_last_response_summary(pending.prompt)
            return pending.prompt

        if action["kind"] == "execute":
            if tool_name == "recommend_full_pipeline" and session.student_profile is None:
                skill_profile, agent_profile = build_profile_if_needed(user_text, self.llm_client)
                session.set_student_profile(skill_profile)
                session.set_agent_profile(agent_profile.__dict__)
            result = self.executor.execute(tool_name, {}, session=session)
            reply = synthesize_reply(session=session, user_text=user_text, decision=decision, result=result)
            session.decision_trace.append(f"Executed `{tool_name}` for intent `{decision.intent}`.")
            session.conversation_history.append({"role": "assistant", "content": reply})
            session.set_last_response_summary(reply)
            return reply

        reply = "I need a bit more detail before I can decide what to run."
        session.conversation_history.append({"role": "assistant", "content": reply})
        session.set_last_response_summary(reply)
        return reply
