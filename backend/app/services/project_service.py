from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.video_project import VideoProject
from app.schemas.project_schema import ProjectCreate, ProjectUpdate

def create_project(db: Session, project_in: ProjectCreate) -> VideoProject:
    db_project = VideoProject(**project_in.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def list_projects(db: Session, skip: int = 0, limit: int = 100) -> List[VideoProject]:
    return db.query(VideoProject).offset(skip).limit(limit).all()

def get_project(db: Session, project_id: int) -> Optional[VideoProject]:
    return db.query(VideoProject).filter(VideoProject.id == project_id).first()

def update_project(db: Session, db_project: VideoProject, project_in: ProjectUpdate) -> VideoProject:
    update_data = project_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int) -> bool:
    db_project = get_project(db, project_id)
    if not db_project:
        return False
    db.delete(db_project)
    db.commit()
    return True
