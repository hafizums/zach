from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.render_schema import FinalRenderRead, FinalRenderCreate
from app.services import (
    render_service, 
    render_generation_service,
    project_service,
    audio_service,
    subtitle_service,
    asset_service,
    scene_service
)
from app.pipeline.pipeline_states import PipelineState

router = APIRouter()

@router.post("/projects/{project_id}/renders/generate", response_model=FinalRenderRead)
def generate_render(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    valid_statuses = [
        PipelineState.SUBTITLES_READY.value,
        PipelineState.FINAL_RENDER_READY.value
    ]
    if project.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Cannot generate render before subtitles are approved")

    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover or voiceover.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Approved active voiceover required")

    subtitles = subtitle_service.list_voiceover_subtitle_segments(db, voiceover.id)
    if not subtitles or any(s.status != "APPROVED" for s in subtitles):
        raise HTTPException(status_code=400, detail="Approved subtitles required")

    scenes = scene_service.list_project_scenes(db, project_id)
    clips_by_scene = {}
    for scene in scenes:
        clip = asset_service.get_active_clip_for_scene(db, scene.id)
        if not clip or clip.status != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Approved active clip required for scene {scene.id}")
        clips_by_scene[scene.id] = clip

    render_in = render_generation_service.generate_mock_render(
        db=db,
        project=project,
        voiceover=voiceover,
        subtitles=subtitles,
        scenes=scenes,
        clips_by_scene=clips_by_scene
    )

    render_service.deactivate_project_renders(db, project_id)
    render = render_service.create_final_render(db, render_in)
    
    return render

@router.get("/projects/{project_id}/renders/active", response_model=FinalRenderRead)
def get_active_render(project_id: int, db: Session = Depends(get_db)):
    render = render_service.get_active_render(db, project_id)
    if not render:
        raise HTTPException(status_code=404, detail="Active render not found")
    return render

@router.get("/projects/{project_id}/renders", response_model=List[FinalRenderRead])
def list_project_renders(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return render_service.list_project_renders(db, project_id)

@router.post("/projects/{project_id}/renders/approve")
def approve_render(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    success = render_service.approve_active_render(db, project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Active render not found")
        
    project.status = PipelineState.FINAL_RENDER_READY.value
    db.commit()
    
    return {"message": "Render approved successfully"}
