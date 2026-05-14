"""Align Skill 1 ``embeddings.npy`` with graph student subsets via ``student_ids.json``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


def load_full_student_index(student_ids_json: Path) -> tuple[list[str], dict[str, int]]:
    with student_ids_json.open(encoding="utf-8") as f:
        ids_list = json.load(f)
    if not isinstance(ids_list, list):
        raise TypeError("student_ids.json must contain a JSON array of strings")
    idx_map = {str(sid): i for i, sid in enumerate(ids_list)}
    return [str(x) for x in ids_list], idx_map


def export_aligned_student_embeddings(
    *,
    embeddings_npy: Path,
    student_ids_json: Path,
    ordered_student_ids: list[str],
    npy_out: Path,
    ids_json_out: Path,
) -> dict[str, Any]:
    """Slice full embeddings so row ``k`` matches ``ordered_student_ids[k]``."""
    emb = np.load(embeddings_npy)
    full_ids, idx_map = load_full_student_index(student_ids_json)
    if emb.shape[0] != len(full_ids):
        raise ValueError(
            f"embeddings.npy rows ({emb.shape[0]}) != len(student_ids.json) ({len(full_ids)})"
        )
    rows: list[np.ndarray] = []
    missing: list[str] = []
    for sid in ordered_student_ids:
        j = idx_map.get(sid)
        if j is None:
            missing.append(sid)
        else:
            rows.append(emb[j])
    if missing:
        raise ValueError(
            f"{len(missing)} student_ids not found in student_ids.json (example: {missing[:5]})"
        )
    stacked = np.stack(rows, axis=0) if rows else np.zeros((0, emb.shape[1]), dtype=emb.dtype)
    npy_out.parent.mkdir(parents=True, exist_ok=True)
    np.save(npy_out, stacked)
    with ids_json_out.open("w", encoding="utf-8") as f:
        json.dump(ordered_student_ids, f, ensure_ascii=False, indent=2)
    return {
        "embedding_shape": [int(stacked.shape[0]), int(stacked.shape[1]) if stacked.ndim == 2 else 0],
        "dtype": str(stacked.dtype),
        "npy_out": str(npy_out.resolve()),
        "ids_json_out": str(ids_json_out.resolve()),
        "source_embeddings": str(embeddings_npy.resolve()),
        "source_student_ids_json": str(student_ids_json.resolve()),
    }
