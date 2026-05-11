from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_key: str
    endpoint: str = "https://api.openai.com/v1/responses"
    temperature: float = 0.1

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("API key is required")


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_json(self, prompt: str) -> dict[str, object]:
        payload = {
            "model": self.config.model,
            "input": prompt,
            "temperature": self.config.temperature,
        }
        request = Request(
            self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        with urlopen(request) as response:
            raw = json.loads(response.read().decode("utf-8"))
        output_text = raw.get("output_text", "{}")
        if not isinstance(output_text, str):
            raise ValueError("LLM response output_text must be a JSON string")
        return json.loads(output_text)
