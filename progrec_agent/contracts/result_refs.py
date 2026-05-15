from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResultReference:
    result_ref: str
    result_type: str
    owner_skill: str
    session_id: str
    input_refs: list[str]
    summary: dict[str, object]
    followups: list[str]
    payload: dict[str, object] = field(default_factory=dict)


class ResultRegistry:
    def __init__(self) -> None:
        self._refs: dict[str, ResultReference] = {}
        self._latest_by_type: dict[str, str] = {}

    def store(self, result: ResultReference) -> None:
        self._refs[result.result_ref] = result
        self._latest_by_type[result.result_type] = result.result_ref

    def get(self, result_ref: str) -> ResultReference:
        return self._refs[result_ref]

    def latest_ref(self, result_type: str) -> str | None:
        return self._latest_by_type.get(result_type)
