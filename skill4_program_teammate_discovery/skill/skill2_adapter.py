"""Load Skill 2 graph and standardized profiles; build edge indexes and entity extracts."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _safe_float(x: Any, default: float = 1.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def load_academic_graph(graph_path: str | Path) -> dict[str, Any] | None:
    path = Path(graph_path)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    nodes = raw.get("nodes")
    edges = raw.get("edges")
    if not isinstance(nodes, dict) or not isinstance(edges, list):
        return None
    for k in ("mentor", "paper", "topic", "project", "student"):
        nodes.setdefault(k, [])
    return {
        "version": raw.get("version", "1.0"),
        "nodes": nodes,
        "edges": edges,
        "statistics": raw.get("statistics") or {},
        "build_meta": raw.get("build_meta") or {},
    }


def load_skill2_students(student_profiles_standard_path: str | Path) -> dict[str, Any] | None:
    path = Path(student_profiles_standard_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_skill2_mentors(mentor_profiles_standard_path: str | Path) -> dict[str, Any] | None:
    path = Path(mentor_profiles_standard_path)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def normalize_skill2_student(student: dict[str, Any]) -> dict[str, Any]:
    skills = student.get("skills") or []
    interests = student.get("interests") or []
    if not isinstance(skills, list):
        skills = [str(skills)]
    if not isinstance(interests, list):
        interests = [str(interests)]
    skills_l = sorted({str(s).strip().lower() for s in skills if str(s).strip()})
    interests_l = sorted({str(s).strip().lower() for s in interests if str(s).strip()})
    avail = str(student.get("availability") or "").strip().lower()
    if not avail:
        avail = "moderate"
    grade = str(student.get("grade") or "").strip() or "unknown"
    sid = str(student.get("student_id") or "").strip()
    return {
        "student_id": sid,
        "grade": grade,
        "major": str(student.get("major") or "").strip(),
        "skills": skills_l,
        "interests": interests_l,
        "experience_summary": str(student.get("experience_summary") or "").strip(),
        "availability": avail,
        "profile_text_for_embedding": str(student.get("profile_text_for_embedding") or ""),
        "profile_source": str(student.get("profile_source") or ""),
    }


def normalize_skill2_mentor(mentor: dict[str, Any]) -> dict[str, Any]:
    mid = str(mentor.get("mentor_id") or "").strip()
    areas = mentor.get("research_areas") or []
    keywords = mentor.get("keywords") or []
    if not isinstance(areas, list):
        areas = [str(areas)]
    if not isinstance(keywords, list):
        keywords = [str(keywords)]
    req = mentor.get("required_skills") or []
    if not isinstance(req, list):
        req = [str(req)]
    return {
        "mentor_id": mid,
        "name": str(mentor.get("name") or "").strip(),
        "department": str(mentor.get("department") or "").strip(),
        "research_areas": [str(a).strip().lower() for a in areas if str(a).strip()],
        "keywords": [str(k).strip().lower() for k in keywords if str(k).strip()],
        "required_skills": [str(s).strip().lower() for s in req if str(s).strip()],
        "profile_text": str(mentor.get("profile_text") or ""),
    }


def _infer_kind_for_id(nodes: dict[str, list[dict[str, Any]]], node_id: str) -> str | None:
    checks = [
        ("mentor", "mentor_id"),
        ("project", "project_id"),
        ("student", "student_id"),
        ("topic", "topic_id"),
        ("paper", "paper_id"),
    ]
    for kind, pk in checks:
        for row in nodes.get(kind, []):
            if str(row.get(pk, "")) == str(node_id):
                return kind
    return None


def _parse_endpoint(
    raw: Any,
    nodes: dict[str, list[dict[str, Any]]],
) -> tuple[str, str] | None:
    if isinstance(raw, dict) and "type" in raw and "id" in raw:
        return str(raw["type"]), str(raw["id"])
    if isinstance(raw, str):
        k = _infer_kind_for_id(nodes, raw)
        if k:
            return k, raw
        return "unknown", raw
    return None


def _node_key(kind: str, id_: str) -> str:
    return f"{kind}:{id_}"


def build_edge_index(graph: dict[str, Any]) -> dict[str, Any]:
    """Build adjacency indexes over normalized type:id keys."""
    nodes = graph["nodes"]
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    normalized: list[dict[str, Any]] = []

    for e in graph.get("edges", []):
        if not isinstance(e, dict):
            continue
        et = str(e.get("type") or "")
        src = _parse_endpoint(e.get("source"), nodes)
        tgt = _parse_endpoint(e.get("target"), nodes)
        if not src or not tgt:
            continue
        sk, tk = _node_key(*src), _node_key(*tgt)
        w = _safe_float(e.get("weight"), 1.0)
        meta = e.get("metadata") if isinstance(e.get("metadata"), dict) else {}
        rec = {
            "edge_type": et,
            "source_kind": src[0],
            "source_id": src[1],
            "target_kind": tgt[0],
            "target_id": tgt[1],
            "source_key": sk,
            "target_key": tk,
            "weight": w,
            "metadata": meta,
        }
        normalized.append(rec)
        outgoing[sk].append(rec)
        incoming[tk].append(rec)
        by_type[et].append(rec)

    return {
        "outgoing_by_source": dict(outgoing),
        "incoming_by_target": dict(incoming),
        "edges_by_type": dict(by_type),
        "normalized_edges": normalized,
    }


def extract_all_mentors_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return list(graph.get("nodes", {}).get("mentor", []))


def extract_all_projects_from_graph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    return list(graph.get("nodes", {}).get("project", []))


def _topic_id_to_label_map(graph: dict[str, Any]) -> dict[str, str]:
    m: dict[str, str] = {}
    for t in graph.get("nodes", {}).get("topic", []):
        tid = t.get("topic_id")
        if tid is not None:
            m[str(tid)] = str(t.get("label") or tid).strip().lower()
    return m


def extract_project_topics(graph: dict[str, Any], project_id: str) -> list[str]:
    rows = {str(p.get("project_id")): p for p in extract_all_projects_from_graph(graph)}
    row = rows.get(str(project_id)) or {}
    tags = row.get("topic_tags")
    if isinstance(tags, list) and tags:
        return sorted({str(t).strip().lower() for t in tags if str(t).strip()})
    tids = row.get("topic_ids")
    if isinstance(tids, list) and tids:
        label_map = _topic_id_to_label_map(graph)
        out = [label_map.get(str(x), str(x).lower()) for x in tids]
        return sorted({str(x).strip().lower() for x in out if str(x).strip()})
    # Enrich from graph edges: project rarely has direct topic edges in Skill 2 seeds;
    # scan paper_topic / custom edges involving project
    topics: set[str] = set()
    idx = build_edge_index(graph)
    pk = _node_key("project", str(project_id))
    for rec in idx["outgoing_by_source"].get(pk, []) + idx["incoming_by_target"].get(pk, []):
        if rec["edge_type"] in ("paper_topic", "mentor_topic"):
            other_k = rec["target_kind"] if rec["source_key"] == pk else rec["source_kind"]
            other_id = rec["target_id"] if rec["source_key"] == pk else rec["source_id"]
            if other_k == "topic":
                topics.add(_topic_id_to_label_map(graph).get(other_id, other_id.lower()))
    return sorted(topics)


def extract_project_required_skills(graph: dict[str, Any], project_id: str) -> list[str]:
    rows = {str(p.get("project_id")): p for p in extract_all_projects_from_graph(graph)}
    row = rows.get(str(project_id)) or {}
    rs = row.get("required_skills")
    if isinstance(rs, list) and rs:
        return sorted({str(s).strip().lower() for s in rs if str(s).strip()})
    # Optional: metadata on edges (future); none in default Skill 2
    return []


def standardize_project_record(
    graph: dict[str, Any],
    project_row: dict[str, Any],
    mentor_id: str | None,
) -> dict[str, Any]:
    pid = str(project_row.get("project_id") or "").strip()
    mid = str(mentor_id or project_row.get("mentor_id") or "").strip()
    title = str(project_row.get("title") or f"Project {pid}").strip()
    topic_tags = extract_project_topics(graph, pid)
    required_skills = extract_project_required_skills(graph, pid)
    diff = str(project_row.get("difficulty") or "medium").strip().lower()
    if diff not in ("easy", "medium", "hard"):
        diff = "medium"
    desc = str(project_row.get("description") or title).strip()
    return {
        "project_id": pid,
        "mentor_id": mid,
        "title": title,
        "topic_tags": topic_tags,
        "required_skills": required_skills,
        "difficulty": diff,
        "description": desc,
    }


def extract_projects_for_mentor(graph: dict[str, Any], mentor_id: str) -> list[dict[str, Any]]:
    idx = build_edge_index(graph)
    mk = _node_key("mentor", str(mentor_id))
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def add_project_row(proj_row: dict[str, Any], mid: str) -> None:
        pid = str(proj_row.get("project_id") or "")
        if not pid or pid in seen:
            return
        seen.add(pid)
        out.append(standardize_project_record(graph, proj_row, mid))

    for rec in idx["edges_by_type"].get("project_leads", []):
        sk, tk = rec["source_kind"], rec["target_kind"]
        sid, tid = rec["source_id"], rec["target_id"]
        if sk == "mentor" and tk == "project" and sid == str(mentor_id):
            prow = _project_row_by_id(graph, tid)
            if prow:
                add_project_row(prow, sid)
        elif sk == "project" and tk == "mentor" and tid == str(mentor_id):
            prow = _project_row_by_id(graph, sid)
            if prow:
                add_project_row(prow, tid)

    if not out:
        for prow in extract_all_projects_from_graph(graph):
            if str(prow.get("mentor_id")) == str(mentor_id):
                add_project_row(prow, str(mentor_id))
    return out


def _project_row_by_id(graph: dict[str, Any], project_id: str) -> dict[str, Any] | None:
    for p in extract_all_projects_from_graph(graph):
        if str(p.get("project_id")) == str(project_id):
            return p
    return None


def extract_student_graph_neighbors(graph: dict[str, Any], student_id: str) -> dict[str, list[dict[str, Any]]]:
    idx = build_edge_index(graph)
    sk = _node_key("student", str(student_id))
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in idx["outgoing_by_source"].get(sk, []):
        by_type[rec["edge_type"]].append(rec)
    for rec in idx["incoming_by_target"].get(sk, []):
        by_type[rec["edge_type"]].append(rec)
    return dict(by_type)


def extract_student_student_edges(
    graph: dict[str, Any],
    student_id: str,
) -> list[dict[str, Any]]:
    idx = build_edge_index(graph)
    sk = _node_key("student", str(student_id))
    want = {"shared_interest", "skill_complementarity"}
    out: list[dict[str, Any]] = []
    for rec in idx["outgoing_by_source"].get(sk, []):
        if rec["edge_type"] not in want:
            continue
        if rec["target_kind"] != "student":
            continue
        out.append(rec)
    for rec in idx["incoming_by_target"].get(sk, []):
        if rec["edge_type"] not in want:
            continue
        if rec["source_kind"] != "student":
            continue
        out.append(rec)
    return out


def mentor_ids_connected_via_project_leads(graph: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for rec in build_edge_index(graph)["edges_by_type"].get("project_leads", []):
        if rec["source_kind"] == "mentor":
            out.add(rec["source_id"])
        if rec["target_kind"] == "mentor":
            out.add(rec["target_id"])
    return out
