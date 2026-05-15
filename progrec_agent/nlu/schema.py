from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

IntentName = Literal[
    "recommendation_request",
    "inspect_recommendation",
    "explain_recommendation",
    "validate_resources",
]
Provenance = Literal["explicit", "inferred", "unknown"]


@dataclass
class SlotValue:
    value: Any
    provenance: Provenance


@dataclass
class IntentFrame:
    intent: IntentName
    target_types: list[str] = field(default_factory=list)
    entities: dict[str, SlotValue] = field(default_factory=dict)
    constraints: dict[str, SlotValue] = field(default_factory=dict)
    preferences: dict[str, SlotValue] = field(default_factory=dict)
    references: dict[str, SlotValue] = field(default_factory=dict)
    confidence: float = 0.0
    uncertain_fields: list[str] = field(default_factory=list)
    possible_conflicts: list[str] = field(default_factory=list)
