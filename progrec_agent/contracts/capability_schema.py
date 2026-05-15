from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityInput:
    name: str
    value_type: str
    required: bool = True


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    kind: str
    owner_skill: str
    when_to_use: str
    requires: list[CapabilityInput]
    returns: str
    can_follow: list[str] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    executor_binding: str = ""

    def to_prompt_block(self) -> str:
        requires = ", ".join(
            f"{item.name}:{item.value_type}{'' if item.required else '?'}" for item in self.requires
        ) or "none"
        followups = ", ".join(self.followups) or "none"
        return "\n".join(
            [
                f"capability: {self.capability_id}",
                f"kind: {self.kind}",
                f"owner_skill: {self.owner_skill}",
                f"requires: {requires}",
                f"returns: {self.returns}",
                f"followups: {followups}",
                f"when_to_use: {self.when_to_use}",
            ]
        )
