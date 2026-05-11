from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class MentorCandidate:
    mentor_id: str
    topic_score: float
    graph_score: float = 0.0
    community_id: str = "community_unknown"
    final_score: float = 0.0
    mentor_name: str = ""
    activity_score: float = 0.0
    centrality_score: float = 0.0
    network_proximity: float = 0.0
    personalized_proximity: float = 0.0
    graph_confidence: float = 0.0
    mentor_authority: float = 0.0
    meta_path_breakdown: dict[str, float] = field(default_factory=dict)
    top_evidence_paths: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    reason_text: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
