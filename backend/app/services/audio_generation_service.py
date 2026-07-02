from typing import List
from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.schemas.audio_schema import VoiceoverCreate
from app.schemas.provider_schema import ProviderRunLogCreate
from app.services import provider_registry, provider_run_service, provider_preflight_service

def generate_mock_voiceover(db: Session, project: VideoProject, script: Script, scenes: List[Scene]) -> VoiceoverCreate:
    """
    Deterministically generates a mock voiceover using registered audio provider.
    Uses concatenated scene narration.
    """
    provider_preflight_service.require_provider_model(db, "mock", "mock-audio", "audio")
    # Concatenate scene narration
    full_narration = " ".join([scene.narration_text for scene in scenes if scene.narration_text])
    if not full_narration:
        full_narration = script.script_body
        
    provider = provider_registry.get_provider("mock", "audio")
    job = provider.generate_voiceover(full_narration, "mock-narrator", project.language)
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name="mock",
        model_name="mock-audio",
        modality="audio",
        operation="voiceover_generation",
        provider_job_id=job.job_id,
        request_json={"narration": full_narration, "voice": "mock-narrator", "language": project.language},
        response_json={"job_id": job.job_id}
    ))
    
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
