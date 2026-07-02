from app.providers.mock_provider import (
    MockLLMProvider,
    MockImageProvider,
    MockVideoProvider,
    MockAudioProvider,
    MockTranscriptionProvider
)

def test_mock_llm_provider():
    provider = MockLLMProvider()
    result = provider.generate_text("Test prompt")
    assert "result" in result

def test_mock_image_provider():
    provider = MockImageProvider()
    job = provider.generate_image("Test prompt", "16:9")
    assert job.status == "COMPLETED"
    assert job.result["image_url"] == "mock_image.jpg"

def test_mock_video_provider():
    provider = MockVideoProvider()
    job = provider.generate_video("mock_image.jpg", "Test prompt", 5, "16:9")
    assert job.status == "COMPLETED"
    assert job.result["video_url"] == "mock_video.mp4"

def test_mock_audio_provider():
    provider = MockAudioProvider()
    job = provider.generate_voiceover("Test text", "voice_1", "en")
    assert job.status == "COMPLETED"
    assert job.result["audio_url"] == "mock_audio.wav"

def test_mock_transcription_provider():
    provider = MockTranscriptionProvider()
    result = provider.transcribe("mock_audio.wav")
    assert "subtitles" in result
