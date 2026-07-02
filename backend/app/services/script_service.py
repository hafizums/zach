from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.script import Script
from app.models.video_project import VideoProject
from app.schemas.script_schema import ScriptCreate, ScriptUpdate
from app.pipeline.pipeline_states import PipelineState

def create_script(db: Session, script_in: ScriptCreate) -> Script:
    db_script = Script(**script_in.model_dump())
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

def list_project_scripts(db: Session, project_id: int) -> List[Script]:
    return db.query(Script).filter(Script.project_id == project_id).order_by(Script.version.desc()).all()

def get_script(db: Session, script_id: int) -> Optional[Script]:
    return db.query(Script).filter(Script.id == script_id).first()

def get_latest_project_script(db: Session, project_id: int) -> Optional[Script]:
    return db.query(Script).filter(Script.project_id == project_id).order_by(Script.version.desc()).first()

def update_script(db: Session, db_script: Script, script_in: ScriptUpdate) -> Script:
    update_data = script_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_script, key, value)
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

def approve_script(db: Session, script_id: int) -> Optional[Script]:
    db_script = get_script(db, script_id)
    if not db_script:
        return None

    # Find the project
    project = db.query(VideoProject).filter(VideoProject.id == db_script.project_id).first()
    if not project:
        return None

    # Reset any other APPROVED scripts for this project to DRAFT
    approved_scripts = db.query(Script).filter(
        Script.project_id == project.id,
        Script.status == "APPROVED",
        Script.id != db_script.id
    ).all()
    for s in approved_scripts:
        s.status = "DRAFT"
        db.add(s)

    # Approve this script
    db_script.status = "APPROVED"
    db.add(db_script)

    # Update project status
    project.status = PipelineState.SCRIPT_READY.value
    db.add(project)

    db.commit()
    db.refresh(db_script)
    return db_script
