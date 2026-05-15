from __future__ import annotations


def list_mentors(mentor_result_payload: dict[str, object]) -> list[dict[str, object]]:
    return list(dict(mentor_result_payload.get("skill3_result") or {}).get("mentor_candidates") or [])


def get_mentor_by_rank(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    rows = list_mentors(dict(result_ref_payload.get("payload") or {}))
    if rank < 1 or rank > len(rows):
        raise ValueError(f"rank {rank} is out of range for {len(rows)} mentor candidates")
    row = dict(rows[rank - 1])
    row.setdefault("rank", rank)
    return row


def explain_mentor_match(result_ref_payload: dict[str, object], *, rank: int) -> dict[str, object]:
    row = get_mentor_by_rank(result_ref_payload, rank=rank)
    return {
        "mentor_id": row.get("mentor_id"),
        "rank": row.get("rank"),
        "summary": row.get("reason") or row.get("explanation") or "",
    }
