"""Optional NetworkX reason graph (node-link JSON)."""

from __future__ import annotations

from typing import Any


def build_reason_graph(target_student: str, mentor_result: dict[str, Any]) -> dict[str, Any]:
    """Return node-link structure; pure-dict fallback if NetworkX is unavailable."""
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    nid = 0

    def add_node(kind: str, label: str, extra: dict[str, Any] | None = None) -> int:
        nonlocal nid
        i = nid
        nid += 1
        n: dict[str, Any] = {"id": i, "kind": kind, "label": label}
        if extra:
            n.update(extra)
        nodes.append(n)
        return i

    ts = add_node("student", target_student, {"role": "target"})
    mid = str(mentor_result.get("mentor_id") or "")
    mn = add_node("mentor", mid or "mentor")

    for pr in mentor_result.get("project_recommendations") or []:
        pid = str(pr.get("project_id") or "")
        pn = add_node("project", pid, {"title": pr.get("title", "")})
        links.append({"source": mn, "target": pn, "relation": "project_leads"})
        for sk in pr.get("missing_skills") or []:
            sn = add_node("skill", sk)
            links.append({"source": pn, "target": sn, "relation": "requires_skill"})
            links.append({"source": ts, "target": sn, "relation": "lacks_skill"})
        for it in pr.get("matched_interests") or []:
            inn = add_node("interest", it)
            links.append({"source": ts, "target": inn, "relation": "has_interest"})

    for tm in mentor_result.get("teammate_recommendations") or []:
        tid = str(tm.get("student_id") or "")
        tn = add_node("teammate", tid)
        links.append({"source": ts, "target": tn, "relation": "potential_teammate"})
        for sk in tm.get("complementary_skills") or []:
            skn = add_node("skill", sk)
            links.append({"source": tn, "target": skn, "relation": "has_skill"})
        reason = str(tm.get("reason") or "")
        if "shared_interest" in reason.lower():
            links.append({"source": ts, "target": tn, "relation": "shared_interest"})
        if "skill_complementarity" in reason.lower() or "complement" in reason.lower():
            links.append({"source": ts, "target": tn, "relation": "skill_complementarity"})

    payload = {"nodes": nodes, "links": links}

    try:
        import networkx as nx
    except ImportError:
        return {"format": "node_link", "directed": True, **payload}

    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], kind=n.get("kind"), label=n.get("label"))
    for j, e in enumerate(links):
        G.add_edge(e["source"], e["target"], relation=e.get("relation", ""), key=j)
    try:
        data = nx.node_link_data(G)
        data["format"] = "networkx_node_link"
        return data
    except Exception:
        return {"format": "node_link", "directed": True, **payload}
