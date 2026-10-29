
"""Mocked OpenAI integration tests — no paid API calls."""

import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from app.api.v1.endpoints.ai import generate_grounded_answer


class FakeResponse:
    def __init__(self, payload):
        self.body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self.body

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_openai_returns_grounded_answer():
    response = {
        "choices": [
            {
                "message": {
                    "content": (
                        "Employees receive 20 days of annual leave "
                        "[Leave policy 1 (version 1)]."
                    )
                }
            }
        ]
    }

    with patch("app.api.v1.endpoints.ai.settings") as settings:
        settings.openai_api_key = "mock-test-key"
        settings.llm_model = "gpt-4o-mini"

        with patch("app.api.v1.endpoints.ai.urlopen") as mock_urlopen:
            mock_urlopen.return_value = FakeResponse(response)

            answer = generate_grounded_answer(
                "How many annual leave days do I get?",
                "[Leave policy 1 (version 1)] Annual entitlement: 20 days.",
            )

            assert answer is not None
            assert "20 days" in answer

            request = mock_urlopen.call_args.args[0]
            body = json.loads(request.data)

            assert body["model"] == "gpt-4o-mini"
            assert "Annual entitlement: 20 days" in body["messages"][1]["content"]


def test_missing_api_key_uses_fallback():
    with patch("app.api.v1.endpoints.ai.settings") as settings:
        settings.openai_api_key = None

        assert generate_grounded_answer(
            "What is the leave policy?",
            "Annual entitlement: 20 days.",
        ) is None



def test_invalid_api_key_is_handled():
    with patch("app.api.v1.endpoints.ai.settings") as settings:
        settings.openai_api_key = "invalid-mock-key"
        settings.llm_model = "gpt-4o-mini"

        with patch(
            "app.api.v1.endpoints.ai.urlopen",
            side_effect=HTTPError(
                "https://api.openai.com/v1/chat/completions",
                401,
                "Unauthorized",
                {},
                None,
            ),
        ):
            assert generate_grounded_answer(
                "What is the leave policy?",
                "Annual entitlement: 20 days.",
            ) is None



def test_rate_limit_is_handled():
    with patch("app.api.v1.endpoints.ai.settings") as settings:
        settings.openai_api_key = "mock-test-key"
        settings.llm_model = "gpt-4o-mini"

        with patch(
            "app.api.v1.endpoints.ai.urlopen",
            side_effect=HTTPError(
                "https://api.openai.com/v1/chat/completions",
                429,
                "Too Many Requests",
                {},
                None,
            ),
        ):
            assert generate_grounded_answer(
                "What is the expense policy?",
                "Expense limit: 500.",
            ) is None


def test_network_failure_is_handled():
    with patch("app.api.v1.endpoints.ai.settings") as settings:
        settings.openai_api_key = "mock-test-key"
        settings.llm_model = "gpt-4o-mini"

        with patch(
            "app.api.v1.endpoints.ai.urlopen",
            side_effect=URLError("Network unavailable"),
        ):
            assert generate_grounded_answer(
                "What is the expense policy?",
                "Expense limit: 500.",
            ) is None
