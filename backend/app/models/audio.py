from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class Voiceover(Base):
    __tablename__ = "voiceovers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    
    provider_job_id = Column(String, nullable=True)
    voice_id = Column(String, default="mock-narrator")
    language = Column(String, default="en")
    narration_text = Column(Text, nullable=False)
    file_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    
    status = Column(String, default="COMPLETED")
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project = relationship("VideoProject")
    script = relationship("Script")
    subtitles = relationship("SubtitleSegment", back_populates="voiceover", cascade="all, delete")
