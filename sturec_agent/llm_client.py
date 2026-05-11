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

    @staticmethod
    def _extract_output_text(raw: dict[str, object]) -> str:
        output_text = raw.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        for item in list(raw.get("output") or []):
            if not isinstance(item, dict):
                continue
            for content in list(item.get("content") or []):
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
        raise ValueError("LLM response did not contain output text")

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
        output_text = self._extract_output_text(raw)
        return json.loads(output_text)
