from typing import Dict, Optional, Any
from .base import LLMProvider, ImageProvider, VideoProvider, AudioProvider, TranscriptionProvider, ProviderJob

class MockLLMProvider(LLMProvider):
    def generate_text(self, prompt: str, schema: Optional[Dict] = None) -> Dict:
        return {
            "hook": "This is a mock hook that grabs your attention.",
            "script": "Here is the mock educational script body that explains the topic clearly and concisely without being too long. It is just the right length for a short video.",
            "word_count": 35,
            "estimated_duration_seconds": 30,
            "payoff": "And that is the mock payoff.",
            "keywords": ["mock", "educational"]
        }

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
