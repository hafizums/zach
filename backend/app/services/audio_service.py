from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.audio import Voiceover
from app.schemas.audio_schema import VoiceoverCreate
from app.models.video_project import VideoProject

def create_voiceover(db: Session, voiceover_in: VoiceoverCreate) -> Voiceover:
    db_voiceover = Voiceover(**voiceover_in.model_dump())
    db.add(db_voiceover)
    db.commit()
    db.refresh(db_voiceover)
    return db_voiceover

def get_active_voiceover(db: Session, project_id: int) -> Optional[Voiceover]:
    return db.query(Voiceover).filter(Voiceover.project_id == project_id, Voiceover.is_active == True).first()

def get_voiceover(db: Session, voiceover_id: int) -> Optional[Voiceover]:
    return db.query(Voiceover).filter(Voiceover.id == voiceover_id).first()

def list_project_voiceovers(db: Session, project_id: int) -> List[Voiceover]:
    return db.query(Voiceover).filter(Voiceover.project_id == project_id).all()

def deactivate_project_voiceovers(db: Session, project_id: int):
    voiceovers = db.query(Voiceover).filter(Voiceover.project_id == project_id, Voiceover.is_active == True).all()
    for v in voiceovers:
        v.is_active = False
    if voiceovers:
        db.commit()

def approve_active_voiceover(db: Session, project_id: int) -> bool:
    voiceover = get_active_voiceover(db, project_id)
    if not voiceover:
        return False
        
    voiceover.status = "APPROVED"
    db.commit()
    return True
