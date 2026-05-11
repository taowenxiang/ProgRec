from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from sturec_agent.llm_client import LLMClient, LLMConfig


class TestLLMClient(unittest.TestCase):
    def test_requires_api_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "API key"):
            LLMConfig(model="gpt-4.1-mini", api_key="")

    @patch("sturec_agent.llm_client.urlopen")
    def test_parse_json_response(self, mock_urlopen) -> None:
        body = json.dumps({"output_text": "{\"goal\": \"nlp\"}"}).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = body
        client = LLMClient(LLMConfig(model="demo", api_key="test-key", endpoint="https://example.com"))
        parsed = client.complete_json("prompt")
        self.assertEqual(parsed["goal"], "nlp")


if __name__ == "__main__":
    unittest.main()
