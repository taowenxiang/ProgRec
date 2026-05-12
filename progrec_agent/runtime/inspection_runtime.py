from __future__ import annotations


def get_ranked_entity(*, skill5_result: dict[str, object], entity_type: str, rank: int):
    rows = list((skill5_result.get("recommendations") or {}).get(f"{entity_type}s") or [])
    for row in rows:
        if int(row.get("rank", 0)) == rank:
            return dict(row)
    return {}
