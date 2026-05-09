"""Queryable index over ``GraphPayload`` for downstream skills."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from .schema import EdgeKind, EdgeRecord, GraphPayload, NodeRef


class GraphIndex:
    """Adjacency index + helpers for mentor/project/student queries."""

    def __init__(self, payload: GraphPayload):
        self.payload = payload
        self._out: dict[str, list[tuple[str, EdgeKind, float, dict[str, Any]]]] = {}
        self._undirected: dict[str, set[str]] = {}
        self._rebuild_adjacency()

    def _rebuild_adjacency(self) -> None:
        self._out.clear()
        self._undirected.clear()
        for e in self.payload.edges:
            sk, tk = e.source.key(), e.target.key()
            meta = {"edge_metadata": e.metadata}
            self._add_edge(sk, tk, e.type, e.weight, meta)
            self._add_edge(tk, sk, e.type, e.weight, meta)

    def _add_edge(
        self,
        src: str,
        dst: str,
        kind: EdgeKind,
        weight: float,
        meta: dict[str, Any],
    ) -> None:
        self._out.setdefault(src, []).append((dst, kind, weight, meta))
        self._undirected.setdefault(src, set()).add(dst)
        self._undirected.setdefault(dst, set()).add(src)

    @classmethod
    def from_json_file(cls, path: Path) -> GraphIndex:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
        edges = [
            EdgeRecord(
                type=e["type"],
                source=NodeRef(e["source"]["type"], e["source"]["id"]),
                target=NodeRef(e["target"]["type"], e["target"]["id"]),
                weight=float(e.get("weight", 1.0)),
                metadata=dict(e.get("metadata") or {}),
            )
            for e in raw["edges"]
        ]
        payload = GraphPayload(
            version=raw["version"],
            nodes=raw["nodes"],
            edges=edges,
            statistics=raw.get("statistics") or {},
            build_meta=raw.get("build_meta") or {},
        )
        return cls(payload)

    def ref(self, kind: str, id_: str) -> str:
        return NodeRef(kind, id_).key()

    def neighbors(
        self,
        node_type: str,
        node_id: str,
        *,
        edge_types: set[str] | None = None,
        target_type: str | None = None,
    ) -> list[tuple[NodeRef, EdgeKind, float]]:
        key = self.ref(node_type, node_id)
        out: list[tuple[NodeRef, EdgeKind, float]] = []
        for dst, ek, w, _ in self._out.get(key, []):
            if edge_types is not None and ek not in edge_types:
                continue
            t, nid = dst.split(":", 1)
            if target_type is not None and t != target_type:
                continue
            out.append((NodeRef(t, nid), ek, w))
        return out

    def topics_for_mentor(self, mentor_id: str) -> list[str]:
        return [
            tid
            for ref, et, _ in self.neighbors("mentor", mentor_id, edge_types={"mentor_topic"})
            if ref.type == "topic"
            for tid in [ref.id]
        ]

    def papers_for_mentor(self, mentor_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("mentor", mentor_id, edge_types={"authored"})
            if ref.type == "paper"
        ]

    def projects_for_mentor(self, mentor_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("mentor", mentor_id, edge_types={"project_leads"})
            if ref.type == "project"
        ]

    def students_for_project(self, project_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("project", project_id, edge_types={"project_participation"})
            if ref.type == "student"
        ]

    def mentor_for_project(self, project_id: str) -> str | None:
        for ref, et, _ in self.neighbors("project", project_id, edge_types={"project_leads"}):
            if ref.type == "mentor":
                return ref.id
        return None

    def collaborators(self, mentor_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("mentor", mentor_id, edge_types={"collaboration"})
            if ref.type == "mentor"
        ]

    def advised_students(self, mentor_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("mentor", mentor_id, edge_types={"advising"})
            if ref.type == "student"
        ]

    def mentors_for_topic(self, topic_id: str) -> list[str]:
        return [
            ref.id
            for ref, et, _ in self.neighbors("topic", topic_id, edge_types={"mentor_topic"})
            if ref.type == "mentor"
        ]

    def shortest_path_len(self, a_type: str, a_id: str, b_type: str, b_id: str) -> int | None:
        """Unweighted shortest path length on the collapsed undirected skeleton."""
        start, goal = self.ref(a_type, a_id), self.ref(b_type, b_id)
        if start == goal:
            return 0
        q: deque[str] = deque([start])
        dist: dict[str, int] = {start: 0}
        while q:
            u = q.popleft()
            for v in self._undirected.get(u, ()):
                if v in dist:
                    continue
                dist[v] = dist[u] + 1
                if v == goal:
                    return dist[v]
                q.append(v)
        return None

    def ego_edges(
        self,
        center_type: str,
        center_id: str,
        max_hops: int = 2,
        edge_type_filter: set[str] | None = None,
    ) -> tuple[set[str], list[dict[str, Any]]]:
        """BFS over undirected skeleton; returns node keys and simplified edge list."""
        start = self.ref(center_type, center_id)
        seen: set[str] = {start}
        bounds: dict[str, int] = {start: 0}
        q: deque[str] = deque([start])
        while q:
            u = q.popleft()
            if bounds[u] >= max_hops:
                continue
            for v in self._undirected.get(u, ()):
                if v not in seen:
                    seen.add(v)
                    bounds[v] = bounds[u] + 1
                    q.append(v)

        slim_edges: list[dict[str, Any]] = []
        visited_pairs: set[tuple[str, str]] = set()
        for e in self.payload.edges:
            sk = e.source.key()
            tk = e.target.key()
            if sk not in seen or tk not in seen:
                continue
            if edge_type_filter is not None and e.type not in edge_type_filter:
                continue
            pair = (sk, tk) if sk < tk else (tk, sk)
            if pair in visited_pairs:
                continue
            visited_pairs.add(pair)
            slim_edges.append(e.to_json())
        return seen, slim_edges
