from __future__ import annotations

import os
from pathlib import Path

from progrec_agent.adapters.skill1_adapter import normalize_manual_profile
from progrec_agent.agent_core import AgentCore
from progrec_agent.llm_client import LLMClient, LLMConfig
from progrec_agent.orchestrator import ProgRecOrchestrator
from progrec_agent.render import render_mentor_detail, render_summary
from progrec_agent.session import AgentSession


HELP_TEXT = "Commands: recommend, show mentor <id>, show profile, show trace, restart, help, exit"


def _manual_profile_prompt() -> dict[str, object]:
    raw = {
        "grade": input("grade: ").strip(),
        "major": input("major: ").strip(),
        "skills": input("skills: ").strip(),
        "interests": input("interests: ").strip(),
        "experience_summary": input("experience_summary: ").strip(),
        "availability": input("availability: ").strip(),
        "resume_text": input("resume_text (optional): ").strip(),
    }
    return normalize_manual_profile(raw)


def _build_llm_client_from_env() -> LLMClient | None:
    api_key = (os.getenv("PROGREC_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    model = (os.getenv("PROGREC_AGENT_MODEL") or "gpt-4.1-mini").strip()
    return LLMClient(LLMConfig(model=model, api_key=api_key))

def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".progrec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    session = AgentSession(temp_dir=temp_dir)
    llm_client = _build_llm_client_from_env()
    core = AgentCore(repo_root=repo_root, temp_dir=temp_dir, llm_client=llm_client)
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    print("ProgRec Agent CLI")
    print(HELP_TEXT)
    while True:
        command = input("> ").strip()
        if command == "exit":
            return 0
        if command == "help":
            print(HELP_TEXT)
            continue
        if command == "restart":
            session.reset()
            print("Session cleared.")
            continue
        if command == "show profile":
            print(session.student_profile or "No active profile.")
            continue
        if command == "show trace":
            print("\n".join(session.decision_trace) if session.decision_trace else "No trace available.")
            continue
        if command.startswith("show mentor "):
            mentor_id = command.removeprefix("show mentor ").strip()
            if not session.skill5_result or not session.skill4_result:
                print("Run recommend first.")
                continue
            mentors = session.skill5_result["recommendations"]["mentors"]
            mentor = next((item for item in mentors if item["mentor_id"] == mentor_id), None)
            bundles = session.skill4_result["mentor_project_teammate_recommendations"]
            bundle = next((item for item in bundles if item["mentor_id"] == mentor_id), {})
            print(render_mentor_detail(mentor, bundle) if mentor else "Mentor not found.")
            continue
        if command == "recommend":
            print("1) existing student_id")
            print("2) manual profile")
            choice = input("Select mode: ").strip()
            if choice == "1":
                student_id = input("student_id: ").strip()
                result = orchestrator.recommend_for_student_id(student_id)
            else:
                result = orchestrator.recommend_for_profile(_manual_profile_prompt())
            session.set_mode(result["mode"])
            session.set_student_profile(result["student_profile"])
            session.set_resource_context(result["resource_context"])
            session.set_results(
                skill3_result=result["skill3_result"],
                skill4_result=result["skill4_result"],
                skill5_result=result["skill5_result"],
                temporary_paths=result["temporary_paths"],
            )
            print(render_summary(result))
            continue
        print(core.handle_message(session, command))


if __name__ == "__main__":
    raise SystemExit(main())
