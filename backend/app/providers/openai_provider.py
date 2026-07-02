import os
import json
import uuid
from pathlib import Path
from typing import Dict, Optional
from openai import OpenAI
from fastapi import HTTPException
from .base import LLMProvider, AudioProvider, ProviderJob

STORAGE_DIR = Path("storage")


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


class OpenAITTSProvider(AudioProvider):
    """Real voiceover generation via OpenAI TTS (text-to-speech)."""

    def __init__(self):
        self.client = None

    def _get_client(self) -> OpenAI:
        if self.client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")
            self.client = OpenAI(api_key=api_key)
        return self.client

    def generate_voiceover(self, text: str, voice_id: str, language: str) -> ProviderJob:
        """Generate voiceover audio using OpenAI TTS speech API."""
        client = self._get_client()

        model_name = os.getenv("OPENAI_DEFAULT_TTS_MODEL", "gpt-4o-mini-tts")
        voice = voice_id or os.getenv("OPENAI_DEFAULT_TTS_VOICE", "alloy")

        try:
            response = client.audio.speech.create(
                model=model_name,
                voice=voice,
                input=text,
                response_format="mp3",
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"OpenAI TTS generation failed: {str(e)}",
            )

        job_id = f"tts_{uuid.uuid4().hex[:12]}"

        # Build storage path: storage/projects/{project_id}/audio/voiceover_{job_id}.mp3
        # The project_id is not known here, so the caller (audio_generation_service)
        # is responsible for saving the audio bytes and providing the final file_url.
        # We return the raw audio bytes in a safe internal field for the service to persist.
        return ProviderJob(
            job_id=job_id,
            status="COMPLETED",
            result={
                "provider_job_id": job_id,
                "file_url": None,  # filled by audio_generation_service after saving
                "duration_seconds": 0,
                "format": "mp3",
                "status": "COMPLETED",
                "raw_response": {"model": model_name, "voice": voice},
                "_audio_bytes": response.content,  # internal, not serialized to JSON
            },
        )
