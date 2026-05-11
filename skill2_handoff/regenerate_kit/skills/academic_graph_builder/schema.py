"""Structured graph payloads for ProgRec Skill 2 (Academic Graph Builder)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

NodeKind = Literal["mentor", "paper", "topic", "project", "student"]

EdgeKind = Literal[
    "collaboration",
    "advising",
    "authored",
    "paper_topic",
    "mentor_topic",
    "project_leads",
    "project_participation",
    "topic_similarity",
    "skill_complementarity",
    "shared_interest",
]


@dataclass(frozen=True)
class NodeRef:
    type: NodeKind
    id: str

    def key(self) -> str:
        return f"{self.type}:{self.id}"


@dataclass
class EdgeRecord:
    type: EdgeKind
    source: NodeRef
    target: NodeRef
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "source": {"type": self.source.type, "id": self.source.id},
            "target": {"type": self.target.type, "id": self.target.id},
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class GraphPayload:
    """Serializable heterogeneous academic graph."""

    version: str
    nodes: dict[str, list[dict[str, Any]]]
    edges: list[EdgeRecord]
    statistics: dict[str, Any] = field(default_factory=dict)
    build_meta: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "nodes": self.nodes,
            "edges": [e.to_json() for e in self.edges],
            "statistics": self.statistics,
            "build_meta": self.build_meta,
        }
