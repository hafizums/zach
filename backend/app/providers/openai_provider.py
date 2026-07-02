import os
import json
from typing import Dict, Optional
from openai import OpenAI
from fastapi import HTTPException
from .base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        if self.client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")
            self.client = OpenAI(api_key=api_key)
        return self.client

    def generate_text(self, prompt: str, model_name: str, system_prompt: Optional[str] = None) -> Dict:
        """Generate free-form text using the OpenAI Responses API."""
        client = self._get_client()

        kwargs = dict(
            model=model_name,
            input=prompt,
        )
        if system_prompt:
            kwargs["instructions"] = system_prompt

        response = client.responses.create(**kwargs)

        text = response.output_text if hasattr(response, "output_text") else response.output[0].content[0].text
        return {
            "text": text,
            "provider_job_id": response.id,
        }

    def generate_structured_json(self, prompt: str, model_name: str, schema: Dict, system_prompt: Optional[str] = None) -> Dict:
        """Generate structured JSON using the OpenAI Responses API with text format."""
        client = self._get_client()

        kwargs = dict(
            model=model_name,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "structured_output",
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        if system_prompt:
            kwargs["instructions"] = system_prompt

        response = client.responses.create(**kwargs)

        text = response.output_text if hasattr(response, "output_text") else response.output[0].content[0].text
        if not text:
            raise ValueError("No content returned from OpenAI")

        parsed = json.loads(text)
        parsed["provider_job_id"] = response.id
        return parsed
