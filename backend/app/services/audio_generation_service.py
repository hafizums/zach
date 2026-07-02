import os
import uuid
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.schemas.audio_schema import VoiceoverCreate
from app.schemas.provider_schema import (
    ProviderRunLogCreate,
    VoiceoverGenerationEstimateResponse,
)
from app.services import provider_registry, provider_run_service, provider_preflight_service

STORAGE_DIR = Path("storage")


def _save_audio_bytes(audio_bytes: bytes, project_id: int, job_id: str) -> str:
    """Save raw audio bytes to local storage and return the file URL path."""
    rel_dir = Path(f"projects/{project_id}/audio")
    abs_dir = STORAGE_DIR / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    filename = f"voiceover_{job_id}.mp3"
    filepath = abs_dir / filename
    filepath.write_bytes(audio_bytes)
    return f"/storage/{rel_dir.as_posix()}/{filename}"


def _require_confirmation_if_paid(db: Session, provider_name: str, model_name: str, confirmed: bool) -> None:
    """Check that paid provider usage is explicitly confirmed."""
    model = provider_preflight_service.preflight_provider_model(db, provider_name, model_name, "audio")
    if not model.ok:
        return  # preflight will be called again later and will fail properly
    # Look up the actual model record to check cost_hint
    from app.services import model_catalog_service
    m = model_catalog_service.get_model(db, provider_name, model_name, "audio")
    if not m or not m.is_enabled:
        return
    is_paid = m.cost_hint == "paid" or m.is_mock is False
    if is_paid and not confirmed:
        raise HTTPException(status_code=400, detail="Paid provider generation requires explicit confirmation.")


def estimate_voiceover_generation(
    db: Session,
    project: VideoProject,
    provider_name: str = "mock",
    model_name: str = "mock-audio",
    voice_id: Optional[str] = None,
) -> VoiceoverGenerationEstimateResponse:
    """Estimate voiceover generation without calling the provider."""
    from app.services import script_service

    scripts = script_service.list_project_scripts(db, project.id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    if not approved_script:
        return VoiceoverGenerationEstimateResponse(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            message="No approved script found. Generate and approve a script first.",
        )

    if not approved_script.script_text:
        return VoiceoverGenerationEstimateResponse(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            script_id=approved_script.id,
            message="Approved script has no body text.",
        )

    # Preflight the provider/model
    preflight = provider_preflight_service.preflight_provider_model(
        db, provider_name, model_name, "audio"
    )
    if not preflight.ok:
        return VoiceoverGenerationEstimateResponse(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            script_id=approved_script.id,
            message=preflight.message,
        )

    # Check cost hint
    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "audio")
    cost_hint = model.cost_hint if model else "mock-free"
    requires_confirmation = (cost_hint == "paid" or (model and model.is_mock is False))

    character_count = len(approved_script.script_text)

    return VoiceoverGenerationEstimateResponse(
        ok=True,
        provider_name=provider_name,
        model_name=model_name,
        script_id=approved_script.id,
        character_count=character_count,
        estimated_jobs=1,
        cost_hint=cost_hint or "unknown",
        requires_confirmation=requires_confirmation,
        message=f"Ready to generate voiceover with {provider_name} {model_name}."
        if preflight.ok
        else preflight.message,
    )


def generate_voiceover(
    db: Session,
    project: VideoProject,
    script: Script,
    provider_name: str = "mock",
    model_name: str = "mock-audio",
    voice_id: Optional[str] = None,
    operation: str = "voiceover_generation",
) -> VoiceoverCreate:
    """
    Dispatcher: generate voiceover via mock or real provider.

    For mock: keeps current deterministic behaviour.
    For OpenAI TTS: preflight → call adapter → save audio → return VoiceoverCreate.
    """
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "audio")

    # Build full narration text from script
    full_narration = script.script_text or ""

    if provider_name == "mock":
        provider = provider_registry.get_provider("mock", "audio")
        job = provider.generate_voiceover(full_narration, voice_id or "mock-narrator", project.language)

        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            provider_name="mock",
            model_name="mock-audio",
            modality="audio",
            operation=operation,
            provider_job_id=job.job_id,
            request_json={"narration": full_narration, "voice": voice_id or "mock-narrator", "language": project.language},
            response_json={"job_id": job.job_id},
        ))

        file_url = f"/storage/projects/{project.id}/audio/voiceover_mock_{job.job_id}.wav"
        duration_seconds = project.duration_target if project.duration_target else 30

        return VoiceoverCreate(
            project_id=project.id,
            script_id=script.id,
            provider_name="mock",
            model_name="mock-audio",
            provider_job_id=job.job_id,
            voice_id=voice_id or "mock-narrator",
            language=project.language,
            narration_text=full_narration,
            file_url=file_url,
            duration_seconds=duration_seconds,
            status="COMPLETED",
            is_active=True,
        )

    # --- OpenAI TTS (or future non-mock providers) ---
    provider = provider_registry.get_provider(provider_name, "audio")
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"No audio provider adapter registered for '{provider_name}'.",
        )

    # Determine voice: request → model defaults → provider default
    from app.services import model_catalog_service
    import json

    model = model_catalog_service.get_model(db, provider_name, model_name, "audio")
    effective_voice = voice_id
    if not effective_voice and model and model.default_params_json:
        try:
            defaults = json.loads(model.default_params_json)
            effective_voice = defaults.get("voice")
        except (json.JSONDecodeError, TypeError):
            pass
    if not effective_voice:
        effective_voice = "alloy"

    try:
        job = provider.generate_voiceover(full_narration, effective_voice, project.language)
    except Exception as e:
        # Log failed provider run without leaking secrets
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            provider_name=provider_name,
            model_name=model_name,
            modality="audio",
            operation=operation,
            provider_job_id=None,
            status="FAILED",
            error_message=str(e)[:500],
        ))
        raise HTTPException(
            status_code=400,
            detail=f"Voiceover generation failed: {str(e)}",
        )

    result = job.result or {}

    # Save audio bytes to local storage
    audio_bytes = result.get("_audio_bytes")
    if audio_bytes:
        file_url = _save_audio_bytes(audio_bytes, project.id, job.job_id)
    else:
        file_url = result.get("file_url")
        if not file_url:
            raise HTTPException(
                status_code=400,
                detail="OpenAI TTS completed but returned no audio data.",
            )

    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name=provider_name,
        model_name=model_name,
        modality="audio",
        operation=operation,
        provider_job_id=job.job_id,
        request_json={"narration_length": len(full_narration), "voice": effective_voice, "language": project.language},
        response_json={
            "provider_job_id": job.job_id,
            "format": result.get("format", "mp3"),
            "duration_seconds": result.get("duration_seconds", 0),
        },
    ))

    return VoiceoverCreate(
        project_id=project.id,
        script_id=script.id,
        provider_name=provider_name,
        model_name=model_name,
        provider_job_id=job.job_id,
        voice_id=effective_voice,
        language=project.language,
        narration_text=full_narration,
        file_url=file_url,
        duration_seconds=result.get("duration_seconds", 0),
        status="COMPLETED",
        is_active=True,
    )


# Keep backward-compatible mock function
def generate_mock_voiceover(db: Session, project: VideoProject, script: Script, scenes: List[Scene]) -> VoiceoverCreate:
    """
    Deterministically generates a mock voiceover using registered audio provider.
    Uses concatenated scene narration.
    """
    provider_preflight_service.require_provider_model(db, "mock", "mock-audio", "audio")
    # Concatenate scene narration
    full_narration = " ".join([scene.narration_text for scene in scenes if scene.narration_text])
    if not full_narration:
        full_narration = script.script_text

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
        provider_name="mock",
        model_name="mock-audio",
        provider_job_id=job.job_id,
        voice_id="mock-narrator",
        language=project.language,
        narration_text=full_narration,
        file_url=file_url,
        duration_seconds=duration_seconds,
        status="COMPLETED",
        is_active=True,
    )
