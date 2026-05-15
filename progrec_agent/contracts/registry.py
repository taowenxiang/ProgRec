from __future__ import annotations

from progrec_agent.contracts.capability_schema import CapabilityContract, CapabilityInput


_CAPABILITIES: dict[str, CapabilityContract] = {
    "/student-profiling.build_temporary_profile": CapabilityContract(
        capability_id="/student-profiling.build_temporary_profile",
        kind="action",
        owner_skill="/student-profiling",
        when_to_use="Use when the user has provided background information and the chat needs a temporary normalized profile.",
        requires=[CapabilityInput(name="profile_context", value_type="object", required=True)],
        returns="student_profile",
        followups=["/student-profiling.show_profile_summary", "/mentor-discovery.recommend_mentors"],
        executor_binding="student_profiling.build_temporary_profile",
    ),
    "/student-profiling.update_profile_context": CapabilityContract(
        capability_id="/student-profiling.update_profile_context",
        kind="action",
        owner_skill="/student-profiling",
        when_to_use="Use when the user provides new profile details after an earlier clarification.",
        requires=[CapabilityInput(name="profile_context", value_type="object", required=True)],
        returns="student_profile",
        can_follow=["student_profile"],
        followups=["/student-profiling.show_profile_summary", "/student-profiling.explain_profile_fields"],
        executor_binding="student_profiling.update_profile_context",
    ),
    "/student-profiling.show_profile_summary": CapabilityContract(
        capability_id="/student-profiling.show_profile_summary",
        kind="inspect",
        owner_skill="/student-profiling",
        when_to_use="Use when the user asks to see the current normalized profile.",
        requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
        returns="student_profile",
        can_follow=["student_profile"],
        executor_binding="student_profiling.show_profile_summary",
    ),
    "/student-profiling.explain_profile_fields": CapabilityContract(
        capability_id="/student-profiling.explain_profile_fields",
        kind="inspect",
        owner_skill="/student-profiling",
        when_to_use="Use when the user asks where the normalized profile fields came from.",
        requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
        returns="student_profile",
        can_follow=["student_profile"],
        executor_binding="student_profiling.explain_profile_fields",
    ),
    "/academic-graph.validate_graph_resources": CapabilityContract(
        capability_id="/academic-graph.validate_graph_resources",
        kind="action",
        owner_skill="/academic-graph",
        when_to_use="Use when the runtime needs to validate graph resources or student-id namespace alignment.",
        requires=[CapabilityInput(name="mode", value_type="string", required=True)],
        returns="resource_validation",
        followups=["/academic-graph.show_resource_status", "/academic-graph.list_available_student_spaces"],
        executor_binding="academic_graph.validate_graph_resources",
    ),
    "/academic-graph.show_resource_status": CapabilityContract(
        capability_id="/academic-graph.show_resource_status",
        kind="inspect",
        owner_skill="/academic-graph",
        when_to_use="Use when the user asks which graph resources or namespaces are active.",
        requires=[CapabilityInput(name="resource_validation_ref", value_type="result_ref", required=True)],
        returns="resource_validation",
        can_follow=["resource_validation"],
        executor_binding="academic_graph.show_resource_status",
    ),
    "/academic-graph.list_available_student_spaces": CapabilityContract(
        capability_id="/academic-graph.list_available_student_spaces",
        kind="inspect",
        owner_skill="/academic-graph",
        when_to_use="Use when the user asks which student-id spaces are available in the current resources.",
        requires=[CapabilityInput(name="resource_validation_ref", value_type="result_ref", required=True)],
        returns="resource_validation",
        can_follow=["resource_validation"],
        executor_binding="academic_graph.list_available_student_spaces",
    ),
    "/mentor-discovery.recommend_mentors": CapabilityContract(
        capability_id="/mentor-discovery.recommend_mentors",
        kind="action",
        owner_skill="/mentor-discovery",
        when_to_use="Use when a temporary or persisted student profile is available and the user wants mentor recommendations.",
        requires=[CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True)],
        returns="mentor_result",
        can_follow=["student_profile"],
        followups=[
            "/mentor-discovery.list_mentors",
            "/mentor-discovery.get_mentor_by_rank",
            "/mentor-discovery.explain_mentor_match",
            "/project-teammate-discovery.recommend_projects",
            "/project-teammate-discovery.recommend_teammates",
        ],
        executor_binding="mentor_discovery.recommend_mentors",
    ),
    "/mentor-discovery.list_mentors": CapabilityContract(
        capability_id="/mentor-discovery.list_mentors",
        kind="inspect",
        owner_skill="/mentor-discovery",
        when_to_use="Use when the user asks to list the current mentor results without expanding a single mentor.",
        requires=[CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True)],
        returns="mentor_result",
        can_follow=["mentor_result"],
        executor_binding="mentor_result_inspector.list_mentors",
    ),
    "/mentor-discovery.get_mentor_by_rank": CapabilityContract(
        capability_id="/mentor-discovery.get_mentor_by_rank",
        kind="inspect",
        owner_skill="/mentor-discovery",
        when_to_use="Use when the user refers to a ranked mentor from the latest mentor result.",
        requires=[
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="mentor_result",
        can_follow=["mentor_result"],
        executor_binding="mentor_result_inspector.get_by_rank",
    ),
    "/mentor-discovery.explain_mentor_match": CapabilityContract(
        capability_id="/mentor-discovery.explain_mentor_match",
        kind="inspect",
        owner_skill="/mentor-discovery",
        when_to_use="Use when the user asks why a mentor was recommended.",
        requires=[
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="mentor_result",
        can_follow=["mentor_result"],
        executor_binding="mentor_result_inspector.explain_mentor_match",
    ),
    "/project-teammate-discovery.recommend_projects": CapabilityContract(
        capability_id="/project-teammate-discovery.recommend_projects",
        kind="action",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user wants project recommendations after a profile or mentor result already exists.",
        requires=[
            CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True),
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=False),
        ],
        returns="project_result",
        can_follow=["student_profile", "mentor_result"],
        followups=[
            "/project-teammate-discovery.get_project_by_rank",
            "/project-teammate-discovery.explain_project_match",
        ],
        executor_binding="project_teammate_discovery.recommend_projects",
    ),
    "/project-teammate-discovery.get_project_by_rank": CapabilityContract(
        capability_id="/project-teammate-discovery.get_project_by_rank",
        kind="inspect",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user asks to inspect a specific ranked project candidate.",
        requires=[
            CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="project_result",
        can_follow=["project_result"],
        executor_binding="project_result_inspector.get_project_by_rank",
    ),
    "/project-teammate-discovery.explain_project_match": CapabilityContract(
        capability_id="/project-teammate-discovery.explain_project_match",
        kind="inspect",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user asks why a project was recommended.",
        requires=[
            CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="project_result",
        can_follow=["project_result"],
        executor_binding="project_result_inspector.explain_project_match",
    ),
    "/project-teammate-discovery.recommend_teammates": CapabilityContract(
        capability_id="/project-teammate-discovery.recommend_teammates",
        kind="action",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user wants teammate recommendations after a profile or mentor result already exists.",
        requires=[
            CapabilityInput(name="student_profile_ref", value_type="result_ref", required=True),
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=False),
        ],
        returns="teammate_result",
        can_follow=["student_profile", "mentor_result"],
        followups=[
            "/project-teammate-discovery.get_teammate_by_rank",
            "/project-teammate-discovery.explain_teammate_match",
        ],
        executor_binding="project_teammate_discovery.recommend_teammates",
    ),
    "/project-teammate-discovery.get_teammate_by_rank": CapabilityContract(
        capability_id="/project-teammate-discovery.get_teammate_by_rank",
        kind="inspect",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user asks to inspect a specific ranked teammate candidate.",
        requires=[
            CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="teammate_result",
        can_follow=["teammate_result"],
        executor_binding="teammate_result_inspector.get_teammate_by_rank",
    ),
    "/project-teammate-discovery.explain_teammate_match": CapabilityContract(
        capability_id="/project-teammate-discovery.explain_teammate_match",
        kind="inspect",
        owner_skill="/project-teammate-discovery",
        when_to_use="Use when the user asks why a teammate was recommended.",
        requires=[
            CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="rank", value_type="int", required=True),
        ],
        returns="teammate_result",
        can_follow=["teammate_result"],
        executor_binding="teammate_result_inspector.explain_teammate_match",
    ),
    "/social-ranking.rerank_bundle": CapabilityContract(
        capability_id="/social-ranking.rerank_bundle",
        kind="action",
        owner_skill="/social-ranking",
        when_to_use="Use when the user wants a combined recommendation bundle reranked across mentors, projects, and teammates.",
        requires=[
            CapabilityInput(name="mentor_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="project_result_ref", value_type="result_ref", required=True),
            CapabilityInput(name="teammate_result_ref", value_type="result_ref", required=True),
        ],
        returns="bundle_result",
        can_follow=["mentor_result", "project_result", "teammate_result"],
        followups=["/social-ranking.show_bundle_summary", "/social-ranking.export_report"],
        executor_binding="social_ranking.rerank_bundle",
    ),
    "/social-ranking.show_bundle_summary": CapabilityContract(
        capability_id="/social-ranking.show_bundle_summary",
        kind="inspect",
        owner_skill="/social-ranking",
        when_to_use="Use when the user asks for the current combined recommendation bundle summary.",
        requires=[CapabilityInput(name="bundle_result_ref", value_type="result_ref", required=True)],
        returns="bundle_result",
        can_follow=["bundle_result"],
        executor_binding="bundle_result_inspector.show_bundle_summary",
    ),
    "/social-ranking.export_report": CapabilityContract(
        capability_id="/social-ranking.export_report",
        kind="inspect",
        owner_skill="/social-ranking",
        when_to_use="Use when the user asks for a report artifact for the current recommendation bundle.",
        requires=[CapabilityInput(name="bundle_result_ref", value_type="result_ref", required=True)],
        returns="report_artifact",
        can_follow=["bundle_result"],
        executor_binding="bundle_result_inspector.export_report",
    ),
}

_LEGACY_ALIASES = {
    "/mentor-discovery.rank_mentors": "/mentor-discovery.recommend_mentors",
    "/social-ranking.rerank_candidates": "/social-ranking.rerank_bundle",
}


def list_capabilities() -> list[CapabilityContract]:
    return list(_CAPABILITIES.values())


def get_capability(capability_id: str) -> CapabilityContract:
    resolved_id = _LEGACY_ALIASES.get(capability_id, capability_id)
    if resolved_id not in _CAPABILITIES:
        raise KeyError(f"Unknown capability {capability_id!r}. Known capabilities: {sorted(allowed_capability_ids())}")
    return _CAPABILITIES[resolved_id]


def allowed_capability_ids() -> set[str]:
    return set(_CAPABILITIES) | set(_LEGACY_ALIASES)


def planner_capability_context() -> str:
    return "\n\n".join(item.to_prompt_block() for item in list_capabilities())
