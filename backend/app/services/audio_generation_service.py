from typing import List
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.schemas.audio_schema import VoiceoverCreate
from app.providers.mock_provider import MockAudioProvider

def generate_mock_voiceover(project: VideoProject, script: Script, scenes: List[Scene]) -> VoiceoverCreate:
    """
    Deterministically generates a mock voiceover using MockAudioProvider.
    Uses concatenated scene narration.
    """
    # Concatenate scene narration
    full_narration = " ".join([scene.narration_text for scene in scenes if scene.narration_text])
    if not full_narration:
        full_narration = script.script_body
        
    provider = MockAudioProvider()
    job = provider.generate_voiceover(full_narration, "mock-narrator", project.language)
    
    file_url = f"/storage/projects/{project.id}/audio/voiceover_mock_{job.job_id}.wav"
    
    # Estimate duration: mock calculation or use project.duration_target
    duration_seconds = project.duration_target if project.duration_target else 30
    
    return VoiceoverCreate(
        project_id=project.id,
        script_id=script.id,
        provider_job_id=job.job_id,
        voice_id="mock-narrator",
        language=project.language,
        narration_text=full_narration,
        file_url=file_url,
        duration_seconds=duration_seconds,
        status="COMPLETED",
        is_active=True
    )
