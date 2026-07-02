from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.video_project import current_utc_time

class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    image_prompt_id = Column(Integer, ForeignKey("image_prompts.id"), nullable=False)

    provider_name = Column(String, nullable=True)
    model_name = Column(String, nullable=True)
    provider_job_id = Column(String, nullable=True)
    file_url = Column(String, nullable=False)
    thumbnail_url = Column(String, nullable=True)

    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)

    status = Column(String, default="COMPLETED")
    quality_score = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    scene = relationship("Scene", back_populates="generated_images")


class GeneratedClip(Base):
    __tablename__ = "generated_clips"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    video_prompt_id = Column(Integer, ForeignKey("video_prompts.id"), nullable=False)
    source_image_id = Column(Integer, ForeignKey("generated_images.id"), nullable=False)
    
    provider_job_id = Column(String, nullable=True)
    file_url = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    
    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)
    fps = Column(Integer, default=30)
    
    status = Column(String, default="COMPLETED")
    quality_score = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    scene = relationship("Scene", back_populates="generated_clips")
