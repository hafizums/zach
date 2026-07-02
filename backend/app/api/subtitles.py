from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.subtitle_schema import SubtitleSegmentRead, SubtitleSegmentUpdate
from app.services import subtitle_service, subtitle_generation_service, project_service, audio_service, scene_service, script_service

router = APIRouter()

@router.post("/projects/{project_id}/subtitles/generate", response_model=List[SubtitleSegmentRead])
def generate_project_subtitles(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    voiceover = audio_service.get_active_voiceover(db, project_id)
    if not voiceover:
        raise HTTPException(status_code=400, detail="Cannot generate subtitles before voiceover exists.")
        
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    scenes = scene_service.list_script_scenes(db, approved_script.id) if approved_script else []
    
    subtitle_service.delete_project_subtitles_for_voiceover(db, project_id, voiceover.id)
    
    segments_in = subtitle_generation_service.generate_mock_subtitles(project, voiceover, scenes)
    segments = subtitle_service.bulk_create_subtitle_segments(db, segments_in)
    
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
