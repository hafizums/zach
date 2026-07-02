from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.final_render import FinalRender
from app.schemas.render_schema import FinalRenderCreate

def create_final_render(db: Session, render_in: FinalRenderCreate) -> FinalRender:
    db_render = FinalRender(**render_in.model_dump())
    db.add(db_render)
    db.commit()
    db.refresh(db_render)
    return db_render

def get_active_render(db: Session, project_id: int) -> Optional[FinalRender]:
    return db.query(FinalRender).filter(
        FinalRender.project_id == project_id, 
        FinalRender.is_active == True
    ).first()

def list_project_renders(db: Session, project_id: int) -> List[FinalRender]:
    return db.query(FinalRender).filter(FinalRender.project_id == project_id).all()

def deactivate_project_renders(db: Session, project_id: int):
    renders = db.query(FinalRender).filter(
        FinalRender.project_id == project_id, 
        FinalRender.is_active == True
    ).all()
    for r in renders:
        r.is_active = False
    if renders:
        db.commit()

def approve_active_render(db: Session, project_id: int) -> bool:
    render = get_active_render(db, project_id)
    if not render:
        return False
        
    render.status = "APPROVED"
    db.commit()
    return True
