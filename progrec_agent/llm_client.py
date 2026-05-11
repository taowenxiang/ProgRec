from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def resolve_responses_endpoint(base_url_or_endpoint: str) -> str:
    value = (base_url_or_endpoint or "").strip().rstrip("/")
    if not value:
        return "https://api.openai.com/v1/responses"
    if value.endswith("/responses"):
        return value
    if value.endswith("/v1"):
        return f"{value}/responses"
    return f"{value}/v1/responses"


def resolve_chat_completions_endpoint(base_url_or_endpoint: str) -> str:
    value = (base_url_or_endpoint or "").strip().rstrip("/")
    if not value:
        return "https://api.openai.com/v1/chat/completions"
    if value.endswith("/chat/completions"):
        return value
    if value.endswith("/responses"):
        return value.removesuffix("/responses") + "/chat/completions"
    if value.endswith("/v1"):
        return f"{value}/chat/completions"
    return f"{value}/v1/chat/completions"


@dataclass(frozen=True)
class LLMConfig:
    model: str
    api_key: str
    endpoint: str = "https://api.openai.com/v1/responses"
    temperature: float = 0.1

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("API key is required")
        object.__setattr__(self, "endpoint", resolve_responses_endpoint(self.endpoint))


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

    @staticmethod
    def _extract_chat_completion_text(raw: dict[str, object]) -> str:
        for item in list(raw.get("choices") or []):
            if not isinstance(item, dict):
                continue
            message = item.get("message")
            if not isinstance(message, dict):
                continue
            text = message.get("content")
            if isinstance(text, str) and text.strip():
                return text
        raise ValueError("Chat Completions response did not contain assistant content")

    @staticmethod
    def _should_fallback_to_chat_completions(exc: HTTPError, body: dict[str, object]) -> bool:
        error = body.get("error")
        if not isinstance(error, dict):
            return False
        code = str(error.get("code") or "").strip().lower()
        message = str(error.get("message") or "").strip().lower()
        return code == "convert_request_failed" or "not implemented" in message

    def _post_json(self, endpoint: str, payload: dict[str, object]) -> dict[str, object]:
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
            method="POST",
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def complete_json(self, prompt: str) -> dict[str, object]:
        responses_payload = {
            "model": self.config.model,
            "input": prompt,
            "temperature": self.config.temperature,
        }
        try:
            raw = self._post_json(self.config.endpoint, responses_payload)
            output_text = self._extract_output_text(raw)
            return json.loads(output_text)
        except HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                body = {}
            if not self._should_fallback_to_chat_completions(exc, body):
                raise
        chat_payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
        }
        chat_endpoint = resolve_chat_completions_endpoint(self.config.endpoint)
        raw = self._post_json(chat_endpoint, chat_payload)
        output_text = self._extract_chat_completion_text(raw)
        return json.loads(output_text)
