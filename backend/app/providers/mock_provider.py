from typing import Dict, Optional, Any
from .base import LLMProvider, ImageProvider, VideoProvider, AudioProvider, TranscriptionProvider, ProviderJob

class MockLLMProvider(LLMProvider):
    def generate_text(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        return {"result": "Mock generated text from LLM."}

class MockImageProvider(ImageProvider):
    def generate_image(self, prompt: str, aspect_ratio: str) -> ProviderJob:
        return ProviderJob(job_id="img_mock_123", status="COMPLETED", result={"image_url": "mock_image.jpg"})

class MockVideoProvider(VideoProvider):
    def generate_video(self, image_url: str, prompt: str, duration: int, aspect_ratio: str) -> ProviderJob:
        return ProviderJob(job_id="vid_mock_123", status="COMPLETED", result={"video_url": "mock_video.mp4"})

class MockAudioProvider(AudioProvider):
    def generate_voiceover(self, text: str, voice_id: str, language: str) -> ProviderJob:
        return ProviderJob(job_id="aud_mock_123", status="COMPLETED", result={"audio_url": "mock_audio.wav"})

class MockTranscriptionProvider(TranscriptionProvider):
    def transcribe(self, audio_path: str) -> Dict:
        return {"subtitles": "Mock subtitles text"}
