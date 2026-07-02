from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.script_schema import ScriptRead, ScriptUpdate, ScriptGenerateRequest
from app.services import script_service, script_generation_service
from app.services import project_service

router = APIRouter()

@router.post("/projects/{project_id}/scripts/generate", response_model=ScriptRead)
def generate_script(project_id: int, request: ScriptGenerateRequest = None, db: Session = Depends(get_db)):
    if request is None:
        request = ScriptGenerateRequest()
        
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    script_in = script_generation_service.generate_script_for_project(
        db, 
        project, 
        provider_name=request.provider_name, 
        model_name=request.model_name
    )
    script = script_service.create_script(db, script_in)
    return script

@router.get("/projects/{project_id}/scripts", response_model=List[ScriptRead])
def list_project_scripts(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return script_service.list_project_scripts(db, project_id)

@router.get("/projects/{project_id}/scripts/latest", response_model=ScriptRead)
def get_latest_project_script(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    script = script_service.get_latest_project_script(db, project_id)
    if not script:
        raise HTTPException(status_code=404, detail="No scripts found for project")
    return script

@router.get("/scripts/{script_id}", response_model=ScriptRead)
def get_script(script_id: int, db: Session = Depends(get_db)):
    script = script_service.get_script(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script

@router.patch("/scripts/{script_id}", response_model=ScriptRead)
def update_script(script_id: int, script_in: ScriptUpdate, db: Session = Depends(get_db)):
    script = script_service.get_script(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script_service.update_script(db, script, script_in)

@router.post("/scripts/{script_id}/approve", response_model=ScriptRead)
def approve_script(script_id: int, db: Session = Depends(get_db)):
    script = script_service.approve_script(db, script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script
