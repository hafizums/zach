from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.pipeline.pipeline_states import PipelineState

def current_utc_time():
    return datetime.now(timezone.utc)

class VideoProject(Base):
    __tablename__ = "video_projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    language = Column(String, default="en")
    duration_target = Column(Integer, default=30)
    aspect_ratio = Column(String, default="9:16")
    visual_style = Column(String, default="semi_realistic_3d_explainer")
    status = Column(String, default=PipelineState.DRAFT_CREATED.value)
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    scripts = relationship("Script", back_populates="project", cascade="all, delete-orphan")
