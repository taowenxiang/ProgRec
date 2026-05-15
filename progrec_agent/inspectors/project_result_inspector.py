from __future__ import annotations


def get_project_by_rank(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    rows = list(dict(result_ref_payload.get("payload") or {}).get("projects") or [])
    if rank < 1 or rank > len(rows):
        raise ValueError(f"rank {rank} is out of range for {len(rows)} project candidates")
    row = dict(rows[rank - 1])
    row.setdefault("rank", rank)
    return row


def explain_project_match(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    row = get_project_by_rank(result_ref_payload, rank=rank)
    return {
        "project_id": row.get("project_id"),
        "rank": row.get("rank"),
        "summary": row.get("reason") or row.get("explanation") or "",
    }
