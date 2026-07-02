import pytest
import os
from unittest.mock import patch, MagicMock
from app.providers.openai_provider import OpenAILLMProvider


def _make_response(text: str) -> MagicMock:
    """Build a minimal mock that looks like an OpenAI Responses API response."""
    resp = MagicMock()
    resp.id = "resp_unit_test"
    resp.output_text = text
    return resp


# ---------------------------------------------------------------------------
# generate_text — uses client.responses.create
# ---------------------------------------------------------------------------

def test_openai_generate_text_uses_responses_api():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAILLMProvider()
        provider.client = MagicMock()
        provider.client.responses.create.return_value = _make_response("Hello world")

        result = provider.generate_text("Test prompt", "gpt-4o-mini")

        # Responses API must be used, NOT chat completions
        provider.client.responses.create.assert_called_once()
        assert not provider.client.chat.completions.create.called

        call_kwargs = provider.client.responses.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["input"] == "Test prompt"

        assert result["text"] == "Hello world"
        assert result["provider_job_id"] == "resp_unit_test"


def test_openai_generate_text_with_system_prompt():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAILLMProvider()
        provider.client = MagicMock()
        provider.client.responses.create.return_value = _make_response("Answer")

        provider.generate_text("Q", "gpt-4o-mini", system_prompt="Be helpful")

        call_kwargs = provider.client.responses.create.call_args[1]
        assert call_kwargs["instructions"] == "Be helpful"


# ---------------------------------------------------------------------------
# generate_structured_json — uses client.responses.create with text format
# ---------------------------------------------------------------------------

def test_openai_generate_structured_json_uses_responses_api():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAILLMProvider()
        provider.client = MagicMock()
        provider.client.responses.create.return_value = _make_response('{"key": "value"}')

        schema = {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        }

        result = provider.generate_structured_json("Test prompt", "gpt-4o-mini", schema, "System prompt")

        # Responses API must be used
        provider.client.responses.create.assert_called_once()
        assert not provider.client.chat.completions.create.called

        call_kwargs = provider.client.responses.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["input"] == "Test prompt"
        assert call_kwargs["instructions"] == "System prompt"
        # text format must carry json_schema
        assert call_kwargs["text"]["format"]["type"] == "json_schema"

        assert result["key"] == "value"
        assert result["provider_job_id"] == "resp_unit_test"


# ---------------------------------------------------------------------------
# Missing key — raises HTTPException via _get_client
# ---------------------------------------------------------------------------

def test_openai_missing_key_raises_http_exception():
    with patch.dict(os.environ, {}, clear=True):
        # Ensure OPENAI_API_KEY is absent
        os.environ.pop("OPENAI_API_KEY", None)

        provider = OpenAILLMProvider()
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            provider.generate_text("Test", "gpt-4o-mini")

        assert exc.value.status_code == 400
        assert "OPENAI_API_KEY is not configured" in exc.value.detail
