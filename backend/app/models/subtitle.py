from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class SubtitleSegment(Base):
    __tablename__ = "subtitle_segments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    voiceover_id = Column(Integer, ForeignKey("voiceovers.id"), nullable=False)
    
    index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    style = Column(String, default="bold_white_black_stroke")
    status = Column(String, default="DRAFT")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("VideoProject")
    voiceover = relationship("Voiceover", back_populates="subtitles")
