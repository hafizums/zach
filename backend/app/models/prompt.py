from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.video_project import current_utc_time

class ImagePrompt(Base):
    __tablename__ = "image_prompts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    
    prompt_text = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    style_lock = Column(Text, nullable=True)
    aspect_ratio = Column(String, default="9:16")
    
    provider = Column(String, default="mock")
    model = Column(String, default="mock-image")
    status = Column(String, default="DRAFT")
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    scene = relationship("Scene", back_populates="image_prompts")


class VideoPrompt(Base):
    __tablename__ = "video_prompts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("video_projects.id"), nullable=False)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=False)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False)
    
    prompt_text = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=False)
    motion_strength = Column(String, default="medium")
    camera_lock = Column(String, default="preserve composition and lighting")
    
    provider = Column(String, default="mock")
    model = Column(String, default="mock-video")
    status = Column(String, default="DRAFT")
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

    scene = relationship("Scene", back_populates="video_prompts")
