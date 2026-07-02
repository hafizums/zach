from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

class ProviderJob:
    def __init__(self, job_id: str, status: str, result: Optional[Any] = None):
        self.job_id = job_id
        self.status = status
        self.result = result

class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, model_name: str, system_prompt: Optional[str] = None) -> Dict:
        pass
        
    @abstractmethod
    def generate_structured_json(self, prompt: str, model_name: str, schema: Dict, system_prompt: Optional[str] = None) -> Dict:
        pass

class ImageProvider(ABC):
    @abstractmethod
    def generate_image(self, prompt: str, aspect_ratio: str) -> ProviderJob:
        pass

class VideoProvider(ABC):
    @abstractmethod
    def generate_video(self, image_url: str, prompt: str, duration: int, aspect_ratio: str) -> ProviderJob:
        pass

class AudioProvider(ABC):
    @abstractmethod
    def generate_voiceover(self, text: str, voice_id: str, language: str) -> ProviderJob:
        pass

class TranscriptionProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict:
        pass

    @abstractmethod
    def transcribe_audio(
        self,
        audio_file_path: str,
        model_name: str = "whisper-1",
        language: str | None = None,
        response_format: str = "verbose_json",
        timestamp_granularities: list[str] | None = None,
    ) -> ProviderJob:
        pass
