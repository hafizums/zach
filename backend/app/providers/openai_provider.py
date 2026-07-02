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
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages
        )
        
        return {
            "text": response.choices[0].message.content,
            "provider_job_id": response.id
        }

    def generate_structured_json(self, prompt: str, model_name: str, schema: Dict, system_prompt: Optional[str] = None) -> Dict:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": schema
            }
        )
        
        content = response.choices[0].message.content
        if not content:
            raise ValueError("No content returned from OpenAI")
            
        parsed = json.loads(content)
        parsed["provider_job_id"] = response.id
        return parsed
