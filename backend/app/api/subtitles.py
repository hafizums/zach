from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.subtitle_schema import SubtitleSegmentRead, SubtitleSegmentUpdate
from app.schemas.provider_schema import (
    SubtitleGenerationRequest,
    SubtitleGenerationEstimateRequest,
    SubtitleGenerationEstimateResponse,
)
from app.services import subtitle_service, subtitle_generation_service, project_service, audio_service, scene_service, script_service

router = APIRouter()


def _require_confirmation_if_paid(db: Session, provider_name: str, model_name: str, confirmed: bool) -> None:
    """Check that paid provider usage is explicitly confirmed for transcription."""
    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "transcription")
    if not model or not model.is_enabled:
        return
    is_paid = model.cost_hint == "paid" or model.is_mock is False
    if is_paid and not confirmed:
        raise HTTPException(status_code=400, detail="Paid provider generation requires explicit confirmation.")


@router.post("/projects/{project_id}/subtitles/estimate", response_model=SubtitleGenerationEstimateResponse)
def estimate_project_subtitles(
    project_id: int,
    request: Optional[SubtitleGenerationEstimateRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = SubtitleGenerationEstimateRequest()

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_statuses = ["VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"]
    if project.status not in valid_statuses:
        return SubtitleGenerationEstimateResponse(
            ok=False,
            provider_name=request.provider_name,
            model_name=request.model_name,
            message=f"Project status '{project.status}' does not allow subtitle generation. Generate voiceover first.",
        )

    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover:
        return SubtitleGenerationEstimateResponse(
            ok=False,
            provider_name=request.provider_name,
            model_name=request.model_name,
            message="No active voiceover found. Generate voiceover first.",
        )

    if not voiceover.file_url:
        return SubtitleGenerationEstimateResponse(
            ok=False,
            provider_name=request.provider_name,
            model_name=request.model_name,
            voiceover_id=voiceover.id,
            message="Active voiceover has no audio file URL.",
        )

    return subtitle_generation_service.estimate_subtitle_generation(
        db, project, voiceover, request.provider_name, request.model_name
    )


@router.post("/projects/{project_id}/subtitles/generate", response_model=List[SubtitleSegmentRead])
def generate_project_subtitles(
    project_id: int,
    request: Optional[SubtitleGenerationRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = SubtitleGenerationRequest()

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover:
        raise HTTPException(status_code=400, detail="Cannot generate subtitles before voiceover exists.")

    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    scenes = scene_service.list_script_scenes(db, approved_script.id) if approved_script else []

    # Check confirmation for paid providers
    _require_confirmation_if_paid(db, request.provider_name, request.model_name, request.confirmed)

    # SAFE ORDER: Generate and validate segments first.
    # Only after successful generation, delete old subtitles and create new ones.
    segments_in = subtitle_generation_service.generate_subtitles(
        db, project, voiceover, scenes,
        provider_name=request.provider_name,
        model_name=request.model_name,
    )

    # Atomically replace old subtitles with new — old subtitles survive if anything fails
    try:
        segments = subtitle_service.replace_subtitle_segments_for_voiceover(
            db, project_id, voiceover.id, segments_in
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to save subtitles: {str(e)}",
        )

    return segments


@router.get("/projects/{project_id}/subtitles", response_model=List[SubtitleSegmentRead])
def list_project_subtitles(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return subtitle_service.list_project_subtitle_segments(db, project_id)


@router.get("/voiceovers/{voiceover_id}/subtitles", response_model=List[SubtitleSegmentRead])
def list_voiceover_subtitles(voiceover_id: int, db: Session = Depends(get_db)):
    voiceover = audio_service.get_voiceover(db, voiceover_id)
    if not voiceover:
        raise HTTPException(status_code=404, detail="Voiceover not found")
    return subtitle_service.list_voiceover_subtitle_segments(db, voiceover_id)


@router.patch("/subtitles/{segment_id}", response_model=SubtitleSegmentRead)
def update_subtitle_segment(segment_id: int, segment_in: SubtitleSegmentUpdate, db: Session = Depends(get_db)):
    segment = subtitle_service.update_subtitle_segment(db, segment_id, segment_in)
    if not segment:
        raise HTTPException(status_code=404, detail="Subtitle segment not found")
    return segment


@router.post("/projects/{project_id}/subtitles/approve")
def approve_subtitles(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover:
        raise HTTPException(status_code=400, detail="No active voiceover found to approve.")

    audio_success = audio_service.approve_active_voiceover(db, project_id)
    sub_success = subtitle_service.approve_project_subtitles(db, project_id, voiceover.id)

    if not audio_success or not sub_success:
        raise HTTPException(status_code=400, detail="Failed to approve audio/subtitles. Ensure they exist.")

    project.status = "SUBTITLES_READY"
    db.add(project)
    db.commit()

    return {"status": "success", "message": "Audio and subtitles approved"}
