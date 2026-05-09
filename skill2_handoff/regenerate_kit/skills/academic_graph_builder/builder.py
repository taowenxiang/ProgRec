"""Build heterogeneous academic + campus graph from seed CSVs."""

from __future__ import annotations

import csv
import json
import os
import random
import tempfile
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mentor_profiles import load_mentor_profiles_json, merge_mentor_records
from .schema import EdgeRecord, GraphPayload, NodeRef
from .student_skill1 import load_skill1_student_nodes


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _split_pipe(value: str) -> list[str]:
    if not value or not value.strip():
        return []
    return [x.strip() for x in value.split("|") if x.strip()]


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    u = sa | sb
    return len(sa & sb) / len(u)


def _skill_complementarity(skills_a: list[str], skills_b: list[str]) -> float:
    """Higher when skill sets differ but both non-empty (symmetric difference density)."""
    sa, sb = set(skills_a), set(skills_b)
    if not sa and not sb:
        return 0.0
    u = sa | sb
    return len(sa ^ sb) / len(u)


def load_seeds(seeds_dir: Path) -> dict[str, Any]:
    """Load all seed tables from ``data/seeds``."""
    profiles_path = seeds_dir / "mentor_profiles.json"
    mentor_profiles_by_id: dict[str, dict[str, Any]] = {}
    if profiles_path.exists():
        mentor_profiles_by_id = load_mentor_profiles_json(profiles_path)
    return {
        "topics": _read_csv(seeds_dir / "topics.csv"),
        "mentors": _read_csv(seeds_dir / "mentors.csv"),
        "papers": _read_csv(seeds_dir / "papers.csv"),
        "paper_authors": _read_csv(seeds_dir / "paper_authors.csv"),
        "paper_topics": _read_csv(seeds_dir / "paper_topics.csv"),
        "students": _read_csv(seeds_dir / "students.csv"),
        "projects": _read_csv(seeds_dir / "projects.csv"),
        "project_participants": _read_csv(seeds_dir / "project_participants.csv"),
        "advising": _read_csv(seeds_dir / "advising.csv"),
        "entity_aliases": _read_csv(seeds_dir / "entity_aliases.csv"),
        "mentor_profiles_by_id": mentor_profiles_by_id,
        "mentor_profiles_path": profiles_path,
    }


MAX_STUDENTS_FULL_PAIRWISE = 2800


def _synthetic_advising_edges(
    rng: random.Random,
    mentor_rows: list[dict[str, str]],
    student_ids: list[str],
    target_edges: int,
) -> list[dict[str, str]]:
    mids = [r["mentor_id"] for r in mentor_rows]
    out: list[dict[str, str]] = []
    if not mids or not student_ids:
        return out
    for _ in range(min(target_edges, len(student_ids) * max(8, len(mids)))):
        out.append({"mentor_id": rng.choice(mids), "student_id": rng.choice(student_ids)})
    return out


def _synthetic_project_participants(
    rng: random.Random,
    project_rows: list[dict[str, str]],
    student_ids: list[str],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not student_ids:
        return out
    for pr in project_rows:
        k = rng.randint(1, min(4, len(student_ids)))
        for sid in rng.sample(student_ids, k=k):
            out.append({"project_id": pr["project_id"], "student_id": sid})
    return out


def build_graph_from_seeds(
    seeds_dir: Path,
    *,
    skill1_jsonl: Path | None = None,
    skill1_max_students: int = 1800,
    skill1_major_filter: tuple[str, ...] | None = (
        "Computer",
        "Software",
        "Electrical",
        "Data Science",
        "Information",
        "Cyber",
        "Mathematics",
    ),
    skill1_random_seed: int = 42,
) -> GraphPayload:
    """Construct ``GraphPayload`` from CSV seeds (public academic + simulated campus).

    When ``skill1_jsonl`` is provided, student nodes are loaded from Skill 1's
    ``student_profiles_normalized.jsonl`` (subset capped by ``skill1_max_students``).
    Advising / project participation edges are synthesized for ID consistency.
    """
    data = load_seeds(seeds_dir)

    nodes: dict[str, list[dict[str, Any]]] = {
        "mentor": [],
        "paper": [],
        "topic": [],
        "project": [],
        "student": [],
    }
    edges: list[EdgeRecord] = []

    for row in data["topics"]:
        nodes["topic"].append({"topic_id": row["topic_id"], "label": row["label"]})

    profiles_by_id = data.get("mentor_profiles_by_id") or {}
    mentor_profiles_path = data.get("mentor_profiles_path")
    if not profiles_by_id:
        raise FileNotFoundError(
            f"缺少导师画像文件: {mentor_profiles_path} "
            "（请提供 mentor_profiles.json，与 mentors.csv 的 mentor_id 对齐）"
        )
    merged_mentors, profile_warnings = merge_mentor_records(
        data["mentors"],
        profiles_by_id,
        data["projects"],
    )
    if profile_warnings:
        raise ValueError("导师画像校验失败:\n" + "\n".join(profile_warnings))
    nodes["mentor"] = merged_mentors
    for row in data["papers"]:
        nodes["paper"].append(
            {
                "paper_id": row["paper_id"],
                "title": row["title"],
                "year": int(row["year"]),
                "venue": row["venue"],
            }
        )
    student_source = "csv"
    skill1_loaded = 0
    advising_rows: list[dict[str, str]]
    participation_rows: list[dict[str, str]]

    if skill1_jsonl is not None:
        student_source = "skill1_jsonl"
        nodes["student"] = load_skill1_student_nodes(
            skill1_jsonl,
            max_students=skill1_max_students,
            major_contains_any=skill1_major_filter,
        )
        skill1_loaded = len(nodes["student"])
        if skill1_loaded == 0:
            raise ValueError(
                "Skill 1 JSONL produced zero students after filtering. "
                "Try --skill1-no-major-filter, increase --skill1-max-students, or verify the JSONL path."
            )
        rng_sg = random.Random(skill1_random_seed)
        sids = [s["student_id"] for s in nodes["student"]]
        advising_rows = _synthetic_advising_edges(rng_sg, data["mentors"], sids, target_edges=420)
        participation_rows = _synthetic_project_participants(rng_sg, data["projects"], sids)
    else:
        for row in data["students"]:
            skills = _split_pipe(row["skills"])
            interests = _split_pipe(row["interests"])
            nodes["student"].append(
                {
                    "student_id": row["student_id"],
                    "grade": row["grade"],
                    "major": row["major"],
                    "skills": skills,
                    "interests": interests,
                    "experience_summary": "",
                    "availability": "",
                    "profile_text_for_embedding": profile_text_for_embedding_csv(
                        row["major"], skills, interests
                    ),
                    "profile_source": "csv_seed",
                }
            )
        advising_rows = list(data["advising"])
        participation_rows = list(data["project_participants"])
    for row in data["projects"]:
        nodes["project"].append(
            {
                "project_id": row["project_id"],
                "title": row["title"],
                "mentor_id": row["mentor_id"],
                "topic_ids": _split_pipe(row["topic_ids"]),
                "required_skills": _split_pipe(row["required_skills"]),
            }
        )

    paper_to_authors: dict[str, list[str]] = defaultdict(list)
    for row in data["paper_authors"]:
        paper_to_authors[row["paper_id"]].append(row["mentor_id"])

    mentor_topics: dict[str, set[str]] = defaultdict(set)
    for row in data["paper_topics"]:
        pid = row["paper_id"]
        tid = row["topic_id"]
        for mid in paper_to_authors.get(pid, []):
            mentor_topics[mid].add(tid)

    # authored + collaboration + paper_topic + mentor_topic + topic_similarity
    collab_pairs: set[tuple[str, str]] = set()
    for pid, authors in paper_to_authors.items():
        authors_sorted = sorted(authors)
        for i, a in enumerate(authors_sorted):
            edges.append(
                EdgeRecord(
                    "authored",
                    NodeRef("mentor", a),
                    NodeRef("paper", pid),
                    weight=1.0,
                    metadata={"paper_id": pid},
                )
            )
            for b in authors_sorted[i + 1 :]:
                pair = (a, b) if a < b else (b, a)
                collab_pairs.add(pair)
        topic_rows = [r for r in data["paper_topics"] if r["paper_id"] == pid]
        for tr in topic_rows:
            edges.append(
                EdgeRecord(
                    "paper_topic",
                    NodeRef("paper", pid),
                    NodeRef("topic", tr["topic_id"]),
                    weight=1.0,
                    metadata={},
                )
            )

    for m, topics in mentor_topics.items():
        for tid in topics:
            edges.append(
                EdgeRecord(
                    "mentor_topic",
                    NodeRef("mentor", m),
                    NodeRef("topic", tid),
                    weight=1.0,
                    metadata={"via": "paper_aggregation"},
                )
            )

    mentor_list = sorted(mentor_topics.keys())
    for i, m1 in enumerate(mentor_list):
        for m2 in mentor_list[i + 1 :]:
            s1, s2 = mentor_topics[m1], mentor_topics[m2]
            inter = len(s1 & s2)
            union = len(s1 | s2)
            if inter > 0 and union > 0:
                w = inter / union
                edges.append(
                    EdgeRecord(
                        "topic_similarity",
                        NodeRef("mentor", m1),
                        NodeRef("mentor", m2),
                        weight=w,
                        metadata={"shared_topics": sorted(s1 & s2)},
                    )
                )

    for a, b in collab_pairs:
        edges.append(
            EdgeRecord(
                "collaboration",
                NodeRef("mentor", a),
                NodeRef("mentor", b),
                weight=1.0,
                metadata={},
            )
        )

    for row in advising_rows:
        edges.append(
            EdgeRecord(
                "advising",
                NodeRef("mentor", row["mentor_id"]),
                NodeRef("student", row["student_id"]),
                weight=1.0,
                metadata={},
            )
        )

    for row in data["projects"]:
        edges.append(
            EdgeRecord(
                "project_leads",
                NodeRef("mentor", row["mentor_id"]),
                NodeRef("project", row["project_id"]),
                weight=1.0,
                metadata={},
            )
        )

    for row in participation_rows:
        edges.append(
            EdgeRecord(
                "project_participation",
                NodeRef("student", row["student_id"]),
                NodeRef("project", row["project_id"]),
                weight=1.0,
                metadata={},
            )
        )

    students_by_id = {s["student_id"]: s for s in nodes["student"]}
    student_ids = sorted(students_by_id)
    skip_pairwise = len(student_ids) > MAX_STUDENTS_FULL_PAIRWISE
    if not skip_pairwise:
        for i, sid_a in enumerate(student_ids):
            sa = students_by_id[sid_a]
            for sid_b in student_ids[i + 1 :]:
                sb = students_by_id[sid_b]
                comp = _skill_complementarity(sa["skills"], sb["skills"])
                shared = _jaccard(sa["interests"], sb["interests"])
                if comp >= 0.35:
                    edges.append(
                        EdgeRecord(
                            "skill_complementarity",
                            NodeRef("student", sid_a),
                            NodeRef("student", sid_b),
                            weight=float(comp),
                            metadata={"skills_a": sa["skills"], "skills_b": sb["skills"]},
                        )
                    )
                if shared >= 0.25:
                    edges.append(
                        EdgeRecord(
                            "shared_interest",
                            NodeRef("student", sid_a),
                            NodeRef("student", sid_b),
                            weight=float(shared),
                            metadata={
                                "overlap": sorted(set(sa["interests"]) & set(sb["interests"]))
                            },
                        )
                    )

    stats = _compute_edge_counts(edges)
    stats["mentor_profile_fields"] = sorted(
        {k for m in nodes["mentor"] for k in m.keys()}
    )
    stats["student_profile_fields"] = sorted({k for s in nodes["student"] for k in s.keys()})
    stats["student_pairwise_edges_skipped"] = skip_pairwise
    bm: dict[str, Any] = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "seeds_dir": str(seeds_dir.resolve()),
        "mentor_profiles_source": str(
            (data.get("mentor_profiles_path") or (seeds_dir / "mentor_profiles.json")).resolve()
        ),
        "student_source": student_source,
        "skill1_major_filter": list(skill1_major_filter) if skill1_major_filter else None,
        "skill1_max_students": skill1_max_students if skill1_jsonl else None,
        "skill1_pairwise_cap": MAX_STUDENTS_FULL_PAIRWISE,
    }
    if skill1_jsonl is not None:
        bm["skill1_jsonl"] = str(skill1_jsonl.resolve())
        bm["skill1_loaded_count"] = skill1_loaded
        bm["skill1_random_seed"] = skill1_random_seed
    payload = GraphPayload(
        version="1.0",
        nodes=nodes,
        edges=edges,
        statistics=stats,
        build_meta=bm,
    )
    return payload


def profile_text_for_embedding_csv(major: str, skills: list[str], interests: list[str]) -> str:
    """Fallback embedding text for CSV-only seeds (no Skill 1 narrative field)."""
    skills_txt = ", ".join(skills)
    interests_txt = ", ".join(interests)
    return "\n".join(
        [
            f"Major: {major}",
            f"Skills: {skills_txt}",
            f"Interests: {interests_txt}",
            "Experience summary: ",
        ]
    )


def _compute_edge_counts(edges: list[EdgeRecord]) -> dict[str, Any]:
    by_type: dict[str, int] = defaultdict(int)
    for e in edges:
        by_type[e.type] += 1
    return {"edge_counts_by_type": dict(sorted(by_type.items()))}


def save_graph_json(payload: GraphPayload, out_path: Path) -> None:
    """Write graph JSON atomically and enforce strict JSON (no NaN/Infinity tokens).

    Large graphs are slow to serialize; a crash or kill mid-write previously left a
    truncated file that strict parsers reject — downstream then sees "invalid JSON".
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.to_json_dict()
    tmp_path: Path | None = None
    try:
        fd, raw_tmp = tempfile.mkstemp(
            suffix=".json.tmp",
            prefix="academic_graph_",
            dir=out_path.parent,
        )
        tmp_path = Path(raw_tmp)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise
    with out_path.open(encoding="utf-8") as f:
        json.load(f)


def build_default_graph(repo_root: Path | None = None) -> GraphPayload:
    root = repo_root or Path(__file__).resolve().parents[2]
    seeds = root / "data" / "seeds"
    return build_graph_from_seeds(seeds)
