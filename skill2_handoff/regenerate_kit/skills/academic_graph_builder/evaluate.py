"""Coverage, alignment, and connectivity metrics for Skill 2."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import networkx as nx

from .builder import load_seeds
from .schema import GraphPayload


def _node_keys_by_kind(payload: GraphPayload) -> dict[str, set[str]]:
    keys: dict[str, set[str]] = {}
    id_field = {
        "mentor": "mentor_id",
        "paper": "paper_id",
        "topic": "topic_id",
        "project": "project_id",
        "student": "student_id",
    }
    for kind, rows in payload.nodes.items():
        fid = id_field[kind]
        keys[kind] = {row[fid] for row in rows}
    return keys


def compute_coverage(payload: GraphPayload, seeds_dir: Path) -> dict[str, Any]:
    """Fraction of seed entities present in built graph nodes."""
    seeds = load_seeds(seeds_dir)
    expected = {
        "mentor": {r["mentor_id"] for r in seeds["mentors"]},
        "paper": {r["paper_id"] for r in seeds["papers"]},
        "topic": {r["topic_id"] for r in seeds["topics"]},
        "project": {r["project_id"] for r in seeds["projects"]},
        "student": {r["student_id"] for r in seeds["students"]},
    }
    actual = _node_keys_by_kind(payload)
    per_kind: dict[str, dict[str, Any]] = {}
    for kind in expected:
        if kind == "student" and payload.build_meta.get("student_source") == "skill1_jsonl":
            exp_n = int(payload.build_meta.get("skill1_loaded_count", 0))
            act = actual.get("student", set())
            hit = len(act)
            per_kind[kind] = {
                "expected": exp_n,
                "matched": hit,
                "coverage": hit / exp_n if exp_n else 1.0,
                "note": "Skill 1 JSONL subset; CSV students.csv not used for expected IDs.",
            }
            continue
        exp = expected[kind]
        act = actual.get(kind, set())
        hit = len(exp & act)
        per_kind[kind] = {
            "expected": len(exp),
            "matched": hit,
            "coverage": hit / len(exp) if exp else 1.0,
        }
    overall_hit = sum(v["matched"] for v in per_kind.values())
    overall_exp = sum(v["expected"] for v in per_kind.values())
    return {
        "per_kind": per_kind,
        "overall_coverage": overall_hit / overall_exp if overall_exp else 1.0,
    }


def compute_alignment_rate(seeds_dir: Path) -> dict[str, Any]:
    """Alias rows successfully mapped to canonical campus IDs (simulated alignment)."""
    path = seeds_dir / "entity_aliases.csv"
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    # Every alias row should resolve to an existing canonical entity in seeds.
    mentors = {r["mentor_id"] for r in _read_csv_simple(seeds_dir / "mentors.csv")}
    papers = {r["paper_id"] for r in _read_csv_simple(seeds_dir / "papers.csv")}
    ok = 0
    details: list[dict[str, str]] = []
    for r in rows:
        ctype, cid = r["canonical_type"], r["canonical_id"]
        resolved = ctype == "mentor" and cid in mentors
        resolved |= ctype == "paper" and cid in papers
        if resolved:
            ok += 1
        details.append({"canonical_id": cid, "resolved": resolved})
    return {
        "alias_rows": len(rows),
        "resolved": ok,
        "alignment_success_rate": ok / len(rows) if rows else 1.0,
        "details": details,
    }


def _read_csv_simple(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute_connectivity(payload: GraphPayload) -> dict[str, Any]:
    """Undirected connectivity summary on the full heterogeneous edge list."""
    g = nx.Graph()
    for e in payload.edges:
        g.add_edge(e.source.key(), e.target.key(), type=e.type)
    n = g.number_of_nodes()
    if n == 0:
        return {"num_nodes": 0, "num_edges": 0, "num_components": 0, "largest_component_frac": 0.0}
    comps = list(nx.connected_components(g))
    largest = max(len(c) for c in comps)
    degrees = dict(g.degree())
    return {
        "num_nodes": n,
        "num_edges": g.number_of_edges(),
        "num_components": len(comps),
        "largest_component_frac": largest / n,
        "avg_degree": sum(degrees.values()) / n,
        "density": nx.density(g),
    }


def evaluate_payload(payload: GraphPayload, seeds_dir: Path) -> dict[str, Any]:
    return {
        "coverage": compute_coverage(payload, seeds_dir),
        "alignment": compute_alignment_rate(seeds_dir),
        "connectivity": compute_connectivity(payload),
    }
