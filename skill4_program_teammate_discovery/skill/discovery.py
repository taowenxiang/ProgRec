"""Skill 4 pipeline: projects per mentor + teammates per path."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill.explanation import build_reason_paths, generate_project_reason, generate_teammate_reason
from skill.project_scoring import (
    compute_difficulty_match_score,
    compute_project_fit_score,
    compute_skill_gap,
    compute_skill_match_score,
    compute_topic_match_score,
    matched_interests_skills,
)
from skill.student_resolution import (
    build_merged_student_index_and_pool,
    format_student_id_error,
    resolve_target_student,
)
from skill.skill2_adapter import (
    build_edge_index,
    extract_projects_for_mentor,
    load_academic_graph,
    load_skill2_mentors,
)
from skill.skill3_adapter import (
    fallback_mentor_candidates_from_skill2,
    load_skill3_mentor_candidates,
    read_skill3_mentor_payload,
)
from skill.teammate_scoring import (
    compute_availability_score,
    compute_complementarity_score,
    compute_graph_relation_score,
    compute_shared_interest_score,
    compute_teammate_score,
    edges_between_students,
)


def _load_mock_projects(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "projects" in raw:
        return list(raw["projects"])
    return []


def discover_projects_for_mentor(
    student_profile: dict[str, Any],
    mentor: dict[str, Any],
    projects: list[dict[str, Any]],
    top_n_projects: int,
    *,
    mentor_project_link_score: float = 1.0,
    projects_from_skill2_graph: bool = True,
) -> list[dict[str, Any]]:
    interests = list(student_profile.get("interests") or [])
    skills = list(student_profile.get("skills") or [])
    grade = str(student_profile.get("grade") or "unknown")
    ranked: list[tuple[float, dict[str, Any]]] = []
    for proj in projects:
        tags = list(proj.get("topic_tags") or [])
        req = list(proj.get("required_skills") or [])
        tm = compute_topic_match_score(interests, tags)
        sm = compute_skill_match_score(skills, req)
        dm = compute_difficulty_match_score(grade, str(proj.get("difficulty") or "medium"))
        fit = compute_project_fit_score(tm, sm, dm, mentor_project_link_score)
        mi, ms = matched_interests_skills(interests, skills, tags, req)
        gap = compute_skill_gap(skills, req)
        ranked.append(
            (
                -fit,
                {
                    "project_id": proj["project_id"],
                    "title": proj.get("title", ""),
                    "fit_score": round(fit, 4),
                    "topic_match_score": round(tm, 4),
                    "skill_match_score": round(sm, 4),
                    "difficulty_match_score": round(dm, 4),
                    "matched_interests": mi,
                    "matched_skills": ms,
                    "missing_skills": gap,
                    "reason": generate_project_reason(
                        interests, mi, ms, gap, projects_from_skill2_graph
                    ),
                },
            )
        )
    ranked.sort(key=lambda x: x[0])
    return [r[1] for r in ranked[: max(0, top_n_projects)]]


def recall_teammate_candidates(
    target_student: dict[str, Any],
    all_students: list[dict[str, Any]],
    max_candidates: int,
    graph: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    tid = str(target_student.get("student_id") or "")
    pool = [s for s in all_students if str(s.get("student_id") or "") != tid]
    if max_candidates > 0:
        pool = pool[:max_candidates]
    return pool


def discover_teammates_for_project(
    target_student: dict[str, Any],
    candidate_students: list[dict[str, Any]],
    missing_skills: list[str],
    top_n_teammates: int,
    graph_context: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    target_id = str(target_student.get("student_id") or "")
    interests = list(target_student.get("interests") or [])
    ranked: list[tuple[float, dict[str, Any]]] = []
    for cand in candidate_students:
        cid = str(cand.get("student_id") or "")
        if not cid:
            continue
        c_interests = list(cand.get("interests") or [])
        c_skills = list(cand.get("skills") or [])
        sis = compute_shared_interest_score(interests, c_interests)
        comp = compute_complementarity_score(missing_skills, c_skills)
        av = compute_availability_score(str(cand.get("availability") or ""))
        e_between = edges_between_students(graph_context, target_id, cid)
        gr = compute_graph_relation_score(e_between)
        has_g = bool(e_between)
        ts = compute_teammate_score(sis, comp, av, gr, has_graph_signal=has_g)
        overlap_i = sorted(
            {str(x).lower() for x in interests} & {str(x).lower() for x in c_interests}
        )
        comp_skills = sorted(
            {str(x).lower() for x in c_skills} & {str(x).lower() for x in missing_skills}
        )
        etypes = [str(e.get("edge_type")) for e in e_between]
        reason = generate_teammate_reason(overlap_i, comp_skills, etypes)
        ranked.append(
            (
                -ts,
                {
                    "student_id": cid,
                    "teammate_score": round(ts, 4),
                    "shared_interest_score": round(sis, 4),
                    "complementarity_score": round(comp, 4),
                    "availability_score": round(av, 4),
                    "graph_relation_score": round(gr, 4),
                    "shared_interests": overlap_i,
                    "complementary_skills": comp_skills,
                    "availability": str(cand.get("availability") or "unknown"),
                    "reason": reason,
                },
            )
        )
    ranked.sort(key=lambda x: x[0])
    return [r[1] for r in ranked[: max(0, top_n_teammates)]]


def discover_projects_and_teammates(
    *,
    target_student_id: str,
    target_student_profile: dict[str, Any],
    all_student_profiles: list[dict[str, Any]],
    mentor_candidates: list[dict[str, Any]],
    graph: dict[str, Any] | None,
    mock_projects_path: Path,
    top_n_projects: int = 3,
    top_n_teammates: int = 3,
    max_candidate_teammates: int = 120,
    data_sources: dict[str, Any] | None = None,
    pipeline_warnings: list[str] | None = None,
) -> dict[str, Any]:
    mock_list = _load_mock_projects(mock_projects_path)
    edge_index = build_edge_index(graph) if graph else None
    graph_context = {"edge_index": edge_index} if edge_index else None

    recommendations: list[dict[str, Any]] = []
    project_sources_used: set[str] = set()
    for mc in mentor_candidates:
        mid = str(mc.get("mentor_id") or "")
        if not mid:
            continue
        base = float(mc.get("final_score", 0.0) or 0.0)
        projects: list[dict[str, Any]] = []
        project_source = "skill2_graph"
        if graph:
            projects = extract_projects_for_mentor(graph, mid)
        if not projects:
            project_source = "mock_projects"
            projects = [p for p in mock_list if str(p.get("mentor_id")) == mid]
        if not projects:
            project_source = "none"
        project_sources_used.add(project_source)

        proj_recs = discover_projects_for_mentor(
            target_student_profile,
            {"mentor_id": mid},
            projects,
            top_n_projects,
            mentor_project_link_score=1.0,
            projects_from_skill2_graph=(project_source == "skill2_graph"),
        )
        union_missing: list[str] = []
        for pr in proj_recs:
            union_missing.extend(pr.get("missing_skills") or [])
        union_missing = sorted(set(str(x).lower() for x in union_missing))

        candidates = recall_teammate_candidates(
            target_student_profile,
            all_student_profiles,
            max_candidate_teammates,
            graph,
        )
        teammate_recs = discover_teammates_for_project(
            target_student_profile,
            candidates,
            union_missing or list(target_student_profile.get("skills") or []),
            top_n_teammates,
            graph_context,
        )

        reason_paths: list[list[str]] = []
        for pr in proj_recs[:2]:
            reason_paths.extend(
                build_reason_paths(
                    target_student_id,
                    mid,
                    str(pr["project_id"]),
                    pr.get("matched_interests") or [],
                    pr.get("missing_skills") or [],
                    teammate_recs,
                )
            )

        block: dict[str, Any] = {
            "mentor_id": mid,
            "mentor_base_score": round(base, 4),
            "topic_score": round(float(mc.get("topic_score", 0.0) or 0.0), 4),
            "graph_score": round(float(mc.get("graph_score", 0.0) or 0.0), 4),
            "community_id": mc.get("community_id"),
            "project_recommendations": proj_recs,
            "teammate_recommendations": teammate_recs,
            "reason_paths": reason_paths[:15],
        }
        if mc.get("activity_score") is not None:
            block["activity_score"] = round(float(mc["activity_score"]), 4)
        if mc.get("centrality_score") is not None:
            block["centrality_score"] = round(float(mc["centrality_score"]), 4)
        if mc.get("network_proximity") is not None:
            block["network_proximity"] = round(float(mc["network_proximity"]), 4)
        if mc.get("mentor_name"):
            block["mentor_name"] = str(mc["mentor_name"])
        rk = mc.get("skill3_rank") if mc.get("skill3_rank") is not None else mc.get("rank")
        if rk is not None:
            try:
                block["skill3_rank"] = int(rk)
            except (TypeError, ValueError):
                pass
        reasons = mc.get("reasons")
        if isinstance(reasons, list) and reasons:
            block["mentor_skill3_reasons"] = [str(x) for x in reasons if str(x).strip()]
        mt = mc.get("matched_topics")
        if isinstance(mt, list) and mt:
            block["matched_topics"] = [str(x) for x in mt]
        mprof = mc.get("mentor_profile")
        if isinstance(mprof, dict) and mprof:
            block["mentor_profile"] = mprof
        recommendations.append(block)

    out_ds = dict(data_sources or {})
    if "mock_projects" in project_sources_used and "skill2_graph" in project_sources_used:
        out_ds["project_source"] = "mixed"
    elif "mock_projects" in project_sources_used:
        out_ds["project_source"] = "mock_projects"
    elif "skill2_graph" in project_sources_used:
        out_ds["project_source"] = "skill2_graph"
    elif "none" in project_sources_used:
        out_ds["project_source"] = "none"

    tp = target_student_profile
    return {
        "target_student_id": target_student_id,
        "target_student_profile": {
            "grade": tp.get("grade") or "unknown",
            "major": tp.get("major") or "",
            "skills": list(tp.get("skills") or []),
            "interests": list(tp.get("interests") or []),
            "availability": tp.get("availability") or "moderate",
        },
        "mentor_project_teammate_recommendations": recommendations,
        "data_sources": out_ds,
        "warnings": list(pipeline_warnings or []),
    }


def run_pipeline_from_cli_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Assemble graph, candidates, and discovery from resolved CLI paths."""
    requested = str(cfg.get("target_student_id") or "").strip()
    s2s = cfg.get("skill2_students_path")
    s1 = cfg.get("skill1_profiles_path")
    strict = bool(cfg.get("strict_target_student"))

    merged, pool, student_src = build_merged_student_index_and_pool(
        Path(s2s) if s2s else None,
        Path(s1) if s1 else None,
    )
    skill3_out = str(cfg.get("skill3_output_path") or "").strip()
    skill3_in_use = bool(skill3_out) and Path(skill3_out).is_file()
    allow_s3_fb = bool(cfg.get("allow_target_fallback_with_skill3"))
    rt = resolve_target_student(
        requested_id=requested,
        merged_index=merged,
        candidate_pool=pool,
        strict=strict,
        print_samples_to_stderr=True,
        skill3_output_blocks_fallback=skill3_in_use,
        allow_target_fallback_with_skill3=allow_s3_fb,
    )
    if rt.resolution == "empty_bundle_no_students" or not rt.effective_student_id:
        raise ValueError(
            "Cannot run Skill 4: no student profiles loaded. "
            f"Check paths: skill2_students={s2s!r}, skill1_profiles={s1!r}. "
            + (rt.warnings[0] if rt.warnings else "")
        )

    target_id = rt.effective_student_id
    target = rt.profile

    graph_path = cfg.get("skill2_graph_path")
    graph = load_academic_graph(Path(graph_path)) if graph_path else None

    mc_path = cfg.get("mentor_candidates_path")
    ments: list[dict[str, Any]] | None = None
    used_skill3_file = False
    skill3_envelope: dict[str, Any] = {}
    if mc_path and Path(str(mc_path)).is_file():
        payload = read_skill3_mentor_payload(mc_path)
        if payload:
            ments = payload["candidates"]
            used_skill3_file = True
            skill3_envelope = {k: v for k, v in payload.items() if k != "candidates"}
    if used_skill3_file:
        d_tgt = str(skill3_envelope.get("skill3_declared_target_student_id") or "").strip()
        d_stu = str(skill3_envelope.get("skill3_declared_student_id") or "").strip()
        problems: list[str] = []
        if d_tgt and d_tgt != target_id:
            problems.append(f"Skill3 target_student_id={d_tgt!r} != effective_target_student_id={target_id!r}")
        if d_stu and d_stu != target_id:
            problems.append(f"Skill3 student_id={d_stu!r} != effective_target_student_id={target_id!r}")
        if problems:
            msg = "skill3_target_student_id_mismatch: " + "; ".join(problems)
            if strict:
                raise ValueError(format_student_id_error(msg, rt.sample_student_ids))
            rt.warnings.append(msg)

    mentor_rows_json: list[dict[str, Any]] | None = None
    mp_path = cfg.get("skill2_mentors_path")
    if mp_path:
        mp_bundle = load_skill2_mentors(Path(mp_path))
        if mp_bundle and isinstance(mp_bundle.get("mentors"), list):
            mentor_rows_json = mp_bundle["mentors"]

    if not ments:
        ments = fallback_mentor_candidates_from_skill2(
            graph,
            mentor_rows_json,
            top_k=int(cfg.get("fallback_mentor_top_k", 10)),
        )
    mock_mc = cfg.get("mock_mentor_candidates_path")
    used_mock_mc = False
    if not ments and mock_mc:
        ments = load_skill3_mentor_candidates(mock_mc)
        if ments:
            used_mock_mc = True

    if used_skill3_file:
        mentor_candidates_label = str(mc_path)
    elif used_mock_mc:
        mentor_candidates_label = str(mock_mc)
    else:
        mentor_candidates_label = "skill2_mentors_or_graph_fallback"

    data_sources: dict[str, Any] = {
        "student_profiles": student_src or None,
        "academic_graph": str(graph_path) if graph_path and graph else None,
        "mentor_candidates": mentor_candidates_label,
        "mentor_candidate_source": (
            "skill3_json" if used_skill3_file else ("mock_json" if used_mock_mc else "skill2_fallback")
        ),
        "project_source": "skill2_graph",
        "target_student_resolution": rt.resolution,
        "requested_target_student_id": rt.requested_student_id or None,
        "effective_target_student_id": rt.effective_student_id,
        "sample_student_ids": rt.sample_student_ids,
    }
    if skill3_envelope.get("graph_status") is not None:
        data_sources["skill3_graph_status"] = skill3_envelope["graph_status"]
    if skill3_envelope.get("graph_notice") is not None:
        data_sources["skill3_graph_notice"] = skill3_envelope["graph_notice"]
    if skill3_envelope.get("target_student_id"):
        data_sources["skill3_target_student_id"] = skill3_envelope["target_student_id"]
    if skill3_envelope.get("skill3_declared_student_id"):
        data_sources["skill3_declared_student_id"] = skill3_envelope["skill3_declared_student_id"]
    if skill3_envelope.get("skill3_declared_target_student_id"):
        data_sources["skill3_declared_target_student_id"] = skill3_envelope[
            "skill3_declared_target_student_id"
        ]
    if skill3_out:
        data_sources["skill3_output_path"] = skill3_out
    data_sources["skill3_output_in_use"] = skill3_in_use
    data_sources["allow_target_fallback_with_skill3"] = allow_s3_fb

    body = discover_projects_and_teammates(
        target_student_id=target_id,
        target_student_profile=target,
        all_student_profiles=pool,
        mentor_candidates=ments,
        graph=graph,
        mock_projects_path=Path(cfg["mock_projects_path"]),
        top_n_projects=int(cfg.get("top_n_projects", 3)),
        top_n_teammates=int(cfg.get("top_n_teammates", 3)),
        max_candidate_teammates=int(cfg.get("max_candidate_teammates", 120)),
        data_sources=data_sources,
        pipeline_warnings=rt.warnings,
    )

    reason_graphs = []
    for block in body.get("mentor_project_teammate_recommendations") or []:
        from skill.graph_utils import build_reason_graph

        reason_graphs.append(build_reason_graph(target_id, block))
    body["reason_graphs"] = reason_graphs
    return body


def try_load_embedding_context(
    npy_path: Path | None,
    ids_path: Path | None,
) -> dict[str, Any] | None:
    """Return aligned embedding matrix + ids if load succeeds; else None (no error)."""
    if not npy_path or not npy_path.is_file() or not ids_path or not ids_path.is_file():
        return None
    try:
        import numpy as np
    except ImportError:
        return None
    try:
        emb = np.load(str(npy_path), allow_pickle=False)
    except Exception:
        return None
    try:
        ids_raw = json.loads(Path(ids_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    ids = ids_raw if isinstance(ids_raw, list) else ids_raw.get("student_ids", [])
    if emb.ndim != 2 or len(ids) != emb.shape[0]:
        return None
    return {"embeddings": emb, "student_ids": [str(x) for x in ids]}
