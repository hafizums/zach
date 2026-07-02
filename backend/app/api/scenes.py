from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.scene_schema import SceneRead, SceneUpdate
from app.services import scene_service, scene_planner_service, project_service, script_service

router = APIRouter()

@router.post("/projects/{project_id}/scenes/generate", response_model=List[SceneRead])
def generate_scenes(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Find approved script
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    
    if not approved_script:
        raise HTTPException(status_code=400, detail="Cannot generate scenes without an APPROVED script.")
        
    # Delete old scenes for this script cleanly
    scene_service.delete_project_scenes_for_script(db, approved_script.id)
    
    # Generate new scenes
    scenes_in = scene_planner_service.generate_mock_scenes(project, approved_script)
    scenes = scene_service.bulk_create_scenes(db, scenes_in)
    
    return scenes

@router.get("/projects/{project_id}/scenes", response_model=List[SceneRead])
def list_project_scenes(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return scene_service.list_project_scenes(db, project_id)

@router.get("/scripts/{script_id}/scenes", response_model=List[SceneRead])
def list_script_scenes(script_id: int, db: Session = Depends(get_db)):
    script = script_service.get_script(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return scene_service.list_script_scenes(db, script_id)

@router.get("/scenes/{scene_id}", response_model=SceneRead)
def get_scene(scene_id: int, db: Session = Depends(get_db)):
    scene = scene_service.get_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene

@router.patch("/scenes/{scene_id}", response_model=SceneRead)
def update_scene(scene_id: int, scene_in: SceneUpdate, db: Session = Depends(get_db)):
    scene = scene_service.get_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return scene_service.update_scene(db, scene, scene_in)

@router.post("/projects/{project_id}/scenes/approve")
def approve_scene_plan(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Find approved script
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    
    if not approved_script:
        raise HTTPException(status_code=400, detail="Cannot approve scene plan without an APPROVED script.")
        
    success = scene_service.approve_project_scene_plan(db, project_id, approved_script.id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve scene plan. Ensure scenes exist.")
        
    return {"status": "success", "message": "Scene plan approved"}
