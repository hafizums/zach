from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.prompt_schema import ImagePromptRead, ImagePromptUpdate, VideoPromptRead, VideoPromptUpdate, ScenePromptPairRead
from app.services import prompt_service, prompt_generation_service, project_service, script_service, scene_service

router = APIRouter()

@router.post("/projects/{project_id}/prompts/generate", response_model=List[ScenePromptPairRead])
def generate_prompts(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Find approved script
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    
    if not approved_script:
        raise HTTPException(status_code=400, detail="Cannot generate prompts without an APPROVED script.")
        
    # Find scenes
    scenes = scene_service.list_script_scenes(db, approved_script.id)
    if not scenes or any(s.status != "APPROVED" for s in scenes):
        raise HTTPException(status_code=400, detail="Cannot generate prompts without an APPROVED scene plan.")
        
    # Delete old prompts cleanly
    prompt_service.delete_project_prompts_for_script(db, approved_script.id)
    
    # Generate new prompts
    image_prompts_in, video_prompts_in = prompt_generation_service.generate_mock_prompt_pairs(project, approved_script, scenes)
    prompt_service.bulk_create_prompt_pairs(db, image_prompts_in, video_prompts_in)
    
    return prompt_service.list_project_prompt_pairs(db, project_id)

@router.get("/projects/{project_id}/prompts", response_model=List[ScenePromptPairRead])
def list_project_prompts(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return prompt_service.list_project_prompt_pairs(db, project_id)

@router.patch("/image-prompts/{prompt_id}", response_model=ImagePromptRead)
def update_image_prompt(prompt_id: int, prompt_in: ImagePromptUpdate, db: Session = Depends(get_db)):
    prompt = prompt_service.get_image_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Image prompt not found")
    return prompt_service.update_image_prompt(db, prompt, prompt_in)

@router.patch("/video-prompts/{prompt_id}", response_model=VideoPromptRead)
def update_video_prompt(prompt_id: int, prompt_in: VideoPromptUpdate, db: Session = Depends(get_db)):
    prompt = prompt_service.get_video_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Video prompt not found")
    return prompt_service.update_video_prompt(db, prompt, prompt_in)

@router.post("/projects/{project_id}/prompts/approve")
def approve_prompts(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    
    if not approved_script:
        raise HTTPException(status_code=400, detail="Cannot approve prompts without an APPROVED script.")
        
    success = prompt_service.approve_project_prompts(db, project_id, approved_script.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve prompts. Ensure prompts exist.")
        
    return {"status": "success", "message": "Prompts approved"}
