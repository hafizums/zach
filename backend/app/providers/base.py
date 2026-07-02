from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

class ProviderJob:
    def __init__(self, job_id: str, status: str, result: Optional[Any] = None):
        self.job_id = job_id
        self.status = status
        self.result = result

class LLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
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
