from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.pipeline.pipeline_states import PipelineState

class ProjectBase(BaseModel):
    title: str
    topic: str
    language: Optional[str] = "en"
    duration_target: Optional[int] = 30
    aspect_ratio: Optional[str] = "9:16"
    visual_style: Optional[str] = "semi_realistic_3d_explainer"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None
    duration_target: Optional[int] = None
    aspect_ratio: Optional[str] = None
    visual_style: Optional[str] = None
    status: Optional[str] = None

class ProjectRead(ProjectBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
