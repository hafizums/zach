from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.subtitle import SubtitleSegment
from app.schemas.subtitle_schema import SubtitleSegmentCreate, SubtitleSegmentUpdate

def create_subtitle_segment(db: Session, segment_in: SubtitleSegmentCreate) -> SubtitleSegment:
    db_segment = SubtitleSegment(**segment_in.model_dump())
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment

def bulk_create_subtitle_segments(db: Session, segments_in: List[SubtitleSegmentCreate]) -> List[SubtitleSegment]:
    db_segments = [SubtitleSegment(**s.model_dump()) for s in segments_in]
    db.add_all(db_segments)
    db.commit()
    for s in db_segments:
        db.refresh(s)
    return db_segments

def list_project_subtitle_segments(db: Session, project_id: int) -> List[SubtitleSegment]:
    return db.query(SubtitleSegment).filter(SubtitleSegment.project_id == project_id).order_by(SubtitleSegment.index).all()

def list_voiceover_subtitle_segments(db: Session, voiceover_id: int) -> List[SubtitleSegment]:
    return db.query(SubtitleSegment).filter(SubtitleSegment.voiceover_id == voiceover_id).order_by(SubtitleSegment.index).all()

def get_subtitle_segment(db: Session, segment_id: int) -> Optional[SubtitleSegment]:
    return db.query(SubtitleSegment).filter(SubtitleSegment.id == segment_id).first()

def update_subtitle_segment(db: Session, segment_id: int, segment_in: SubtitleSegmentUpdate) -> Optional[SubtitleSegment]:
    db_segment = get_subtitle_segment(db, segment_id)
    if not db_segment:
        return None
        
    update_data = segment_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_segment, key, value)
        
    db.commit()
    db.refresh(db_segment)
    return db_segment

def delete_project_subtitles_for_voiceover(db: Session, project_id: int, voiceover_id: int):
    segments = db.query(SubtitleSegment).filter(SubtitleSegment.project_id == project_id, SubtitleSegment.voiceover_id == voiceover_id).all()
    for s in segments:
        db.delete(s)
    if segments:
        db.commit()

def approve_project_subtitles(db: Session, project_id: int, voiceover_id: int) -> bool:
    segments = list_voiceover_subtitle_segments(db, voiceover_id)
    if not segments:
        return False
        
    for s in segments:
        s.status = "APPROVED"
        
    db.commit()
    return True
