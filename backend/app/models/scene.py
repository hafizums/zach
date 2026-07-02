from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.video_project import current_utc_time

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    scene_number = Column(Integer, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    narration_text = Column(Text, nullable=False)
    visual_summary = Column(Text, nullable=False)
    camera_direction = Column(String, nullable=True)
    motion_direction = Column(String, nullable=True)
    sfx_notes = Column(String, nullable=True)
    status = Column(String, default="DRAFT")
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    project = relationship("VideoProject", back_populates="scenes")
    script = relationship("Script", back_populates="scenes")
    image_prompts = relationship("ImagePrompt", back_populates="scene", cascade="all, delete-orphan")
    video_prompts = relationship("VideoPrompt", back_populates="scene", cascade="all, delete-orphan")
    generated_images = relationship("GeneratedImage", back_populates="scene", cascade="all, delete-orphan")
    generated_clips = relationship("GeneratedClip", back_populates="scene", cascade="all, delete-orphan")
