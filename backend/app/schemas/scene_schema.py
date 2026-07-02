from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class SceneBase(BaseModel):
    scene_number: int
    duration_seconds: int
    narration_text: str
    visual_summary: str
    camera_direction: Optional[str] = None
    motion_direction: Optional[str] = None
    sfx_notes: Optional[str] = None

class SceneCreate(SceneBase):
    project_id: int
    script_id: int

class SceneUpdate(BaseModel):
    duration_seconds: Optional[int] = None
    narration_text: Optional[str] = None
    visual_summary: Optional[str] = None
    camera_direction: Optional[str] = None
    motion_direction: Optional[str] = None
    sfx_notes: Optional[str] = None

class SceneRead(SceneBase):
    id: int
    project_id: int
    script_id: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

from app.schemas.provider_schema import GenerationRequest

class SceneGenerateRequest(GenerationRequest):
    pass
