from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

from sturec_agent.adapters.skill1_adapter import normalize_manual_profile
from sturec_agent.agent_schema import AgentProfile, ExecutionPlan
from sturec_agent.explainer import build_final_response
from sturec_agent.llm_client import LLMClient, LLMConfig
from sturec_agent.orchestrator import StuRecOrchestrator
from sturec_agent.planner import build_execution_plan
from sturec_agent.profile_enricher import build_profiles_from_text
from sturec_agent.render import render_mentor_detail, render_summary
from sturec_agent.result_judge import judge_results
from sturec_agent.session import AgentSession
from sturec_agent.strategy import build_strategy


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
    api_key = (os.getenv("STUREC_AGENT_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        return None
    model = (os.getenv("STUREC_AGENT_MODEL") or "gpt-4.1-mini").strip()
    return LLMClient(LLMConfig(model=model, api_key=api_key))


def _fallback_profiles(user_text: str) -> tuple[dict[str, object], AgentProfile]:
    skill_profile = normalize_manual_profile(
        {
            "grade": "",
            "major": "",
            "skills": "",
            "interests": "",
            "experience_summary": user_text,
            "availability": "moderate",
            "resume_text": user_text,
        }
    )
    agent_profile = AgentProfile(goal=user_text, confidence=0.0)
    return skill_profile, agent_profile


def _fallback_plan() -> ExecutionPlan:
    return ExecutionPlan(
        need_clarification=False,
        run_skill3=True,
        run_skill4=True,
        run_skill5=True,
    )


def run_agent_turn(session: AgentSession, user_text: str, orchestrator: StuRecOrchestrator) -> str:
    session.conversation_history.append({"role": "user", "content": user_text})
    llm_client = _build_llm_client_from_env()
    if llm_client is not None:
        skill_profile, agent_profile = build_profiles_from_text(user_text, llm_client)
        plan = build_execution_plan(asdict(agent_profile), llm_client)
        session.decision_trace.append("Profile drafted from natural-language input via LLM.")
    else:
        skill_profile, agent_profile = _fallback_profiles(user_text)
        plan = _fallback_plan()
        session.decision_trace.append("LLM unavailable; used fallback profile drafting.")

    session.set_student_profile(skill_profile)
    session.set_agent_profile(asdict(agent_profile))
    strategy = build_strategy(asdict(agent_profile))
    session.set_active_strategy(strategy)
    session.set_latest_plan(
        {
            "need_clarification": plan.need_clarification,
            "run_skill3": plan.run_skill3,
            "run_skill4": plan.run_skill4,
            "run_skill5": plan.run_skill5,
        }
    )

    if plan.need_clarification and plan.clarification_questions:
        session.decision_trace.append("Planner requested clarification before running tools.")
        questions = "\n".join(f"- {item.question}" for item in plan.clarification_questions)
        return f"Before I run recommendations, I need a bit more information:\n{questions}"

    session.decision_trace.append("Planner selected the full recommendation pipeline.")
    result = orchestrator.recommend_for_profile(skill_profile, top_k=int(strategy["top_k"]))
    verdict = judge_results(
        skill5_result=result["skill5_result"],
        strategy=strategy,
        rerun_count=session.rerun_count,
    )
    if verdict["rerun_needed"]:
        session.rerun_count += 1
        strategy["top_k"] = max(int(strategy["top_k"]), 8)
        session.set_active_strategy(strategy)
        session.decision_trace.append(f"Reran with adjusted strategy: {', '.join(verdict['reasons'])}")
        result = orchestrator.recommend_for_profile(skill_profile, top_k=int(strategy["top_k"]))

    session.set_mode(result["mode"])
    session.set_resource_context(result["resource_context"])
    session.set_results(
        skill3_result=result["skill3_result"],
        skill4_result=result["skill4_result"],
        skill5_result=result["skill5_result"],
        temporary_paths=result["temporary_paths"],
    )
    return build_final_response(
        agent_profile=asdict(agent_profile),
        skill5_result=result["skill5_result"],
        decision_trace=session.decision_trace,
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    temp_dir = repo_root / ".sturec_agent_tmp"
    temp_dir.mkdir(exist_ok=True)
    session = AgentSession(temp_dir=temp_dir)
    orchestrator = StuRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    print("StuRec Agent CLI")
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
        print(run_agent_turn(session, command, orchestrator))


if __name__ == "__main__":
    raise SystemExit(main())
