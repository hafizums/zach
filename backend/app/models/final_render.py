from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.video_project import current_utc_time

class FinalRender(Base):
    __tablename__ = "final_renders"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    voiceover_id = Column(Integer, ForeignKey("voiceovers.id"), nullable=False)
    output_url = Column(String, nullable=False)
    manifest_json = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    aspect_ratio = Column(String, default="9:16")
    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)
    status = Column(String, default="COMPLETED")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    project = relationship("VideoProject")
    voiceover = relationship("Voiceover")
