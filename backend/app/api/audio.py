from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.audio_schema import VoiceoverRead
from app.schemas.provider_schema import (
    VoiceoverGenerationRequest,
    VoiceoverGenerationEstimateRequest,
    VoiceoverGenerationEstimateResponse,
)
from app.services import audio_service, audio_generation_service, project_service, script_service, scene_service, asset_service

router = APIRouter()


def _require_confirmation_if_paid(db: Session, provider_name: str, model_name: str, confirmed: bool) -> None:
    """Check that paid provider usage is explicitly confirmed for audio."""
    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "audio")
    if not model or not model.is_enabled:
        return
    is_paid = model.cost_hint == "paid" or model.is_mock is False
    if is_paid and not confirmed:
        raise HTTPException(status_code=400, detail="Paid provider generation requires explicit confirmation.")


@router.post("/projects/{project_id}/audio/voiceover/estimate", response_model=VoiceoverGenerationEstimateResponse)
def estimate_project_voiceover(
    project_id: int,
    request: Optional[VoiceoverGenerationEstimateRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = VoiceoverGenerationEstimateRequest()

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_statuses = ["CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"]
    if project.status not in valid_statuses:
        return VoiceoverGenerationEstimateResponse(
            ok=False,
            provider_name=request.provider_name,
            model_name=request.model_name,
            message=f"Project status '{project.status}' does not allow voiceover generation. Assets must be approved first.",
        )

    return audio_generation_service.estimate_voiceover_generation(
        db, project, request.provider_name, request.model_name, request.voice_id
    )


@router.post("/projects/{project_id}/audio/voiceover/generate", response_model=VoiceoverRead)
def generate_project_voiceover(
    project_id: int,
    request: Optional[VoiceoverGenerationRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = VoiceoverGenerationRequest()

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_statuses = ["CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"]
    if project.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Cannot generate voiceover before assets are approved.")

    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    if not approved_script:
        raise HTTPException(status_code=400, detail="No approved script found.")

    scenes = scene_service.list_script_scenes(db, approved_script.id)

    # Validation pass: must have active clips
    for scene in scenes:
        clip = asset_service.get_active_clip_for_scene(db, scene.id)
        if not clip:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot generate voiceover because scene {scene.scene_number} has no active clip.",
            )

    # Check confirmation for paid providers
    _require_confirmation_if_paid(db, request.provider_name, request.model_name, request.confirmed)

    # Generate the voiceover (safe: old voiceover stays active until new one succeeds)
    voiceover_in = audio_generation_service.generate_voiceover(
        db,
        project,
        approved_script,
        provider_name=request.provider_name,
        model_name=request.model_name,
        voice_id=request.voice_id,
    )

    # Create new voiceover and deactivate old ones atomically —
    # if create fails, old active voiceover remains intact.
    try:
        voiceover = audio_service.create_voiceover_and_deactivate_old(db, voiceover_in)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save voiceover: {str(e)}",
        )

    if project.status == "CLIPS_GENERATED":
        project.status = "VOICEOVER_READY"
        db.add(project)
        db.commit()

    return voiceover


@router.get("/projects/{project_id}/audio/voiceover", response_model=VoiceoverRead)
def get_project_active_voiceover(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover:
        raise HTTPException(status_code=404, detail="No active voiceover found")

    return voiceover


@router.get("/projects/{project_id}/audio/voiceovers", response_model=List[VoiceoverRead])
def list_project_voiceovers(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return audio_service.list_project_voiceovers(db, project_id)
