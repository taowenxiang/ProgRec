from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from progrec_agent.llm_client import (
    LLMClient,
    LLMConfig,
    resolve_chat_completions_endpoint,
    resolve_responses_endpoint,
)


class TestLLMClient(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API key"):
            LLMConfig(model="gpt-4.1-mini", api_key="")

    def test_resolve_responses_endpoint_from_root_base_url(self) -> None:
        self.assertEqual(
            resolve_responses_endpoint("https://example.com"),
            "https://example.com/v1/responses",
        )

    def test_resolve_responses_endpoint_from_v1_base_url(self) -> None:
        self.assertEqual(
            resolve_responses_endpoint("https://example.com/v1"),
            "https://example.com/v1/responses",
        )

    def test_resolve_responses_endpoint_keeps_full_endpoint(self) -> None:
        self.assertEqual(
            resolve_responses_endpoint("https://example.com/v1/responses"),
            "https://example.com/v1/responses",
        )

    def test_resolve_chat_completions_endpoint_from_responses_endpoint(self) -> None:
        self.assertEqual(
            resolve_chat_completions_endpoint("https://example.com/v1/responses"),
            "https://example.com/v1/chat/completions",
        )

    @patch("progrec_agent.llm_client.urlopen")
    def test_parse_json_response(self, mock_urlopen) -> None:
        body = json.dumps({"output_text": "{\"goal\": \"nlp\"}"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = body
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))
        parsed = client.complete_json("prompt")
        self.assertEqual(parsed["goal"], "nlp")

    @patch("progrec_agent.llm_client.urlopen")
    def test_post_json_uses_request_timeout(self, mock_urlopen) -> None:
        body = json.dumps({"output_text": "{\"goal\": \"nlp\"}"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = body
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))

        client.complete_json("prompt")

        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 20.0)

    @patch("progrec_agent.llm_client.urlopen")
    def test_parse_json_response_from_output_array(self, mock_urlopen) -> None:
        body = json.dumps(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "{\"goal\": \"trustworthy ai\"}",
                            }
                        ],
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = body
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))
        parsed = client.complete_json("prompt")
        self.assertEqual(parsed["goal"], "trustworthy ai")

    @patch("progrec_agent.llm_client.urlopen")
    def test_falls_back_to_chat_completions_on_convert_request_failed(self, mock_urlopen) -> None:
        error_body = io.BytesIO(
            json.dumps(
                {
                    "error": {
                        "message": "not implemented",
                        "type": "rix_api_error",
                        "code": "convert_request_failed",
                    }
                }
            ).encode("utf-8")
        )
        responses_error = HTTPError(
            url="https://example.com/v1/responses",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=error_body,
        )
        chat_body = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "{\"goal\": \"fallback works\"}",
                        }
                    }
                ]
            }
        ).encode("utf-8")

        mock_urlopen.side_effect = [
            responses_error,
            unittest.mock.Mock(__enter__=unittest.mock.Mock(return_value=unittest.mock.Mock(read=unittest.mock.Mock(return_value=chat_body))), __exit__=unittest.mock.Mock(return_value=False)),
        ]
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))
        parsed = client.complete_json("prompt")
        self.assertEqual(parsed["goal"], "fallback works")


if __name__ == "__main__":
    unittest.main()
