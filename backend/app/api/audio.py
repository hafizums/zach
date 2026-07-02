from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.audio_schema import VoiceoverRead
from app.services import audio_service, audio_generation_service, project_service, script_service, scene_service, asset_service

router = APIRouter()

@router.post("/projects/{project_id}/audio/voiceover/generate", response_model=VoiceoverRead)
def generate_project_voiceover(project_id: int, db: Session = Depends(get_db)):
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
            raise HTTPException(status_code=400, detail=f"Cannot generate voiceover because scene {scene.scene_number} has no active clip.")
            
    audio_service.deactivate_project_voiceovers(db, project_id)
    
    voiceover_in = audio_generation_service.generate_mock_voiceover(db, project, approved_script, scenes)
    voiceover = audio_service.create_voiceover(db, voiceover_in)
    
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
