from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from progrec_agent.skill_registry import SKILL_REGISTRY, list_skills
from progrec_agent.tool_registry import TOOLS


_SKILL_DOC_PATHS = {
    "/student-profiling": "skill1_student_profiling/SKILL.md",
    "/academic-graph": "skill2_academic_graph_builder/SKILL.md",
    "/mentor-discovery": "skill3_mentor_discovery/SKILL.md",
    "/project-teammate-discovery": "skill4_program_teammate_discovery/SKILL.md",
    "/social-ranking": "skill5_student_recommendation_ranker/SKILL.md",
}

_SKILL_TOOLS = {
    "/student-profiling": ["recommend_full_pipeline"],
    "/academic-graph": ["recommend_full_pipeline", "debug_graph_mode", "inspect_artifacts", "rebuild_skill2_graph"],
    "/mentor-discovery": ["recommend_full_pipeline"],
    "/project-teammate-discovery": ["recommend_full_pipeline"],
    "/social-ranking": ["recommend_full_pipeline"],
}

_CANNOT_DO = {
    "/student-profiling": ["rank mentors", "recommend projects", "perform final social ranking"],
    "/academic-graph": ["choose mentors by itself", "explain ranked recommendations"],
    "/mentor-discovery": ["recommend projects", "recommend teammates", "perform final joint ranking"],
    "/project-teammate-discovery": ["standardize raw profiles", "perform final joint ranking"],
    "/social-ranking": ["parse raw student stories", "rebuild graph resources"],
}


@dataclass(frozen=True)
class SkillCard:
    skill_id: str
    name: str
    when_to_use: str
    requires: list[str]
    produces: list[str]
    allowed_tools: list[str]
    cannot_do: list[str]

    def to_prompt_block(self) -> str:
        return (
            f"- skill_id: {self.skill_id}\n"
            f"  name: {self.name}\n"
            f"  when_to_use: {self.when_to_use}\n"
            f"  requires: {', '.join(self.requires)}\n"
            f"  produces: {', '.join(self.produces)}\n"
            f"  allowed_tools: {', '.join(self.allowed_tools)}\n"
            f"  cannot_do: {', '.join(self.cannot_do)}"
        )


@dataclass(frozen=True)
class SkillCatalog:
    cards: list[SkillCard]
    allowed_skill_ids: set[str]
    allowed_tool_names: set[str]

    def to_prompt_context(self) -> str:
        return "\n".join(card.to_prompt_block() for card in self.cards)


def _split_contract(value: Any) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = [part.strip(" .") for part in text.replace(";", ",").split(",")]
    return [part for part in parts if part]


def _first_doc_description(repo_root: Path, skill_id: str) -> str:
    doc_path = repo_root / _SKILL_DOC_PATHS.get(skill_id, "")
    if not doc_path.is_file():
        return ""
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            return stripped.removeprefix("description:").strip().strip('"')
    return ""


def _card_from_registry(repo_root: Path, skill_id: str, meta: dict[str, Any]) -> SkillCard:
    doc_description = _first_doc_description(repo_root, skill_id)
    when_to_use = doc_description or str(meta.get("function") or "")
    allowed_tools = [tool for tool in _SKILL_TOOLS.get(skill_id, []) if tool in TOOLS]
    return SkillCard(
        skill_id=skill_id,
        name=str(meta.get("name") or skill_id),
        when_to_use=when_to_use,
        requires=_split_contract(meta.get("input_contract")),
        produces=_split_contract(meta.get("output_contract")),
        allowed_tools=allowed_tools,
        cannot_do=list(_CANNOT_DO.get(skill_id, [])),
    )


def build_skill_catalog(repo_root: Path) -> SkillCatalog:
    cards = [
        _card_from_registry(repo_root, skill_id, dict(SKILL_REGISTRY[skill_id]))
        for skill_id in list_skills()
        if skill_id in SKILL_REGISTRY
    ]
    return SkillCatalog(
        cards=cards,
        allowed_skill_ids={card.skill_id for card in cards},
        allowed_tool_names=set(TOOLS),
    )
