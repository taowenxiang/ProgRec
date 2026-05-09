#!/usr/bin/env python3
"""
Inspect / visualize the heterogeneous academic graph built by Skill 2.

Examples:
  python3 scripts/inspect_graph.py summary
  python3 scripts/inspect_graph.py ego --mentor m_001 --hops 1 --out data/processed/ego_m001.png
  python3 scripts/inspect_graph.py graphml --mentor m_001 --hops 1 --out data/processed/ego_m001.graphml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH = _REPO / "data" / "processed" / "academic_graph.json"

KIND_COLORS = {
    "student": "#7fc97f",
    "mentor": "#beaed4",
    "project": "#fdc086",
    "paper": "#386cb0",
    "topic": "#f0027f",
}


def _node_key(kind: str, id_: str) -> str:
    return f"{kind}:{id_}"


def load_networkx(path: Path):
    import networkx as nx

    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    G = nx.Graph()
    id_field = {
        "mentor": "mentor_id",
        "paper": "paper_id",
        "topic": "topic_id",
        "project": "project_id",
        "student": "student_id",
    }
    for kind, rows in data["nodes"].items():
        fk = id_field[kind]
        for row in rows:
            nk = _node_key(kind, row[fk])
            G.add_node(nk, kind=kind, label=str(row.get(fk, nk)))
    for e in data["edges"]:
        s = _node_key(e["source"]["type"], e["source"]["id"])
        t = _node_key(e["target"]["type"], e["target"]["id"])
        if not G.has_node(s) or not G.has_node(t):
            continue
        G.add_edge(s, t, etype=e["type"], weight=float(e.get("weight", 1.0)))
    return G, data


def cmd_summary(path: Path) -> None:
    G, data = load_networkx(path)
    by_kind: dict[str, int] = {}
    for _, attrs in G.nodes(data=True):
        k = attrs.get("kind", "?")
        by_kind[k] = by_kind.get(k, 0) + 1
    etypes: dict[str, int] = {}
    for _, _, attrs in G.edges(data=True):
        t = attrs.get("etype", "?")
        etypes[t] = etypes.get(t, 0) + 1
    print(f"Graph file: {path}")
    print(f"Nodes: {G.number_of_nodes()}   Edges: {G.number_of_edges()}")
    print("Nodes by type:")
    for k in sorted(by_kind):
        print(f"  {k:10s} {by_kind[k]}")
    print("Edges by type (top 15):")
    for t, c in sorted(etypes.items(), key=lambda x: -x[1])[:15]:
        print(f"  {t:22s} {c}")
    print("(Heterogeneous graph = multiple node types + multiple relation types on one backbone.)")


def _ego_node_set(G, center: str, hops: int, max_nodes: int | None):
    import networkx as nx

    if center not in G:
        raise SystemExit(f"Center node not in graph: {center}")
    lengths = nx.single_source_shortest_path_length(G, center, cutoff=hops)
    nodes = list(lengths.keys())
    if max_nodes is not None and len(nodes) > max_nodes:
        dist_sorted = sorted(nodes, key=lambda n: (lengths[n], n))
        kept = set(dist_sorted[:max_nodes])
        if center not in kept:
            kept.add(center)
        nodes = list(kept)
    return set(nodes)


def cmd_ego(path: Path, mentor_id: str, hops: int, out: Path, max_nodes: int | None) -> None:
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt
    import networkx as nx

    G, _ = load_networkx(path)
    center = _node_key("mentor", mentor_id)
    nodes = _ego_node_set(G, center, hops=hops, max_nodes=max_nodes)
    H = G.subgraph(nodes).copy()

    pos = nx.spring_layout(H, seed=42, k=0.55 / max(1, int(H.number_of_nodes() ** 0.25)))
    plt.figure(figsize=(14, 10), dpi=120)
    for kind, color in KIND_COLORS.items():
        nlist = [n for n in H.nodes if H.nodes[n].get("kind") == kind]
        nx.draw_networkx_nodes(H, pos, nodelist=nlist, node_color=color, node_size=260, alpha=0.92)
    nx.draw_networkx_edges(H, pos, alpha=0.15, width=0.6)
    labels = {n: H.nodes[n].get("label", n) for n in H.nodes()}
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=6)

    handles = [mpatches.Patch(color=c, label=k) for k, c in KIND_COLORS.items()]
    plt.legend(handles=handles, frameon=True)
    plt.axis("off")
    plt.title(f"Ego network: {center}, hops={hops}, |V|={H.number_of_nodes()}, |E|={H.number_of_edges()}")
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    print(f"Wrote {out}")


def cmd_graphml(path: Path, mentor_id: str, hops: int, out: Path, max_nodes: int | None) -> None:
    import networkx as nx

    G, _ = load_networkx(path)
    center = _node_key("mentor", mentor_id)
    nodes = _ego_node_set(G, center, hops=hops, max_nodes=max_nodes)
    H = G.subgraph(nodes).copy()
    out.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(H, out)
    print(f"Wrote GraphML for Gephi/Cytoscape: {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Inspect heterogeneous academic graph JSON.")
    p.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="Path to academic_graph.json")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("summary", help="Print counts by node type and edge type")

    pe = sub.add_parser("ego", help="Plot an ego subgraph around a mentor (PNG)")
    pe.add_argument("--mentor", required=True, help="mentor_id e.g. m_001")
    pe.add_argument("--hops", type=int, default=1)
    pe.add_argument("--max-nodes", type=int, default=120, help="Cap nodes for readability")
    pe.add_argument("--out", type=Path, required=True)

    pg = sub.add_parser("graphml", help="Export ego subgraph as GraphML")
    pg.add_argument("--mentor", required=True)
    pg.add_argument("--hops", type=int, default=1)
    pg.add_argument("--max-nodes", type=int, default=200)
    pg.add_argument("--out", type=Path, required=True)

    args = p.parse_args()
    if args.cmd == "summary":
        cmd_summary(args.graph)
    elif args.cmd == "ego":
        cmd_ego(args.graph, args.mentor, args.hops, args.out, args.max_nodes)
    elif args.cmd == "graphml":
        cmd_graphml(args.graph, args.mentor, args.hops, args.out, args.max_nodes)


if __name__ == "__main__":
    main()
