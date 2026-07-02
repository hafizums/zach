import pytest
import os
from unittest.mock import patch, MagicMock
from app.providers.openai_provider import OpenAILLMProvider

def test_openai_generate_text():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAILLMProvider()
        
        # Mock the client
        provider.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        provider.client.chat.completions.create.return_value = mock_response
        
        result = provider.generate_text("Test prompt", "gpt-4o-mini")
        assert result["text"] == "Test response"
        assert result["provider_job_id"] == mock_response.id
        
        # Verify call
        provider.client.chat.completions.create.assert_called_once()
        args, kwargs = provider.client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"][0]["content"] == "Test prompt"

def test_openai_generate_structured_json():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        provider = OpenAILLMProvider()
        
        provider.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"key": "value"}'
        provider.client.chat.completions.create.return_value = mock_response
        
        schema = {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False
        }
        
        result = provider.generate_structured_json("Test prompt", "gpt-4o-mini", schema, "System prompt")
        assert result["key"] == "value"
        assert result["provider_job_id"] == mock_response.id
        
        args, kwargs = provider.client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["messages"][0]["content"] == "System prompt"
        assert kwargs["messages"][1]["content"] == "Test prompt"
        assert "response_format" in kwargs
        assert kwargs["response_format"]["type"] == "json_schema"

def test_openai_missing_key():
    with patch.dict(os.environ, clear=True):
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            
        provider = OpenAILLMProvider()
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            provider.generate_text("Test", "gpt-4o-mini")
        assert exc.value.status_code == 400
        assert "OPENAI_API_KEY is not configured" in exc.value.detail
