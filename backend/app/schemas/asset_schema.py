from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class GeneratedImageBase(BaseModel):
    file_url: str
    thumbnail_url: Optional[str] = None
    width: int = 1080
    height: int = 1920
    status: str = "COMPLETED"
    is_active: bool = True

class GeneratedImageCreate(GeneratedImageBase):
    project_id: int
    script_id: int
    scene_id: int
    image_prompt_id: int

class GeneratedImageRead(GeneratedImageBase):
    id: int
    project_id: int
    script_id: int
    scene_id: int
    image_prompt_id: int
    provider_job_id: Optional[str] = None
    quality_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class GeneratedClipBase(BaseModel):
    file_url: str
    duration_seconds: int
    width: int = 1080
    height: int = 1920
    fps: int = 30
    status: str = "COMPLETED"
    is_active: bool = True

class GeneratedClipCreate(GeneratedClipBase):
    project_id: int
    script_id: int
    scene_id: int
    video_prompt_id: int
    source_image_id: int

class GeneratedClipRead(GeneratedClipBase):
    id: int
    project_id: int
    script_id: int
    scene_id: int
    video_prompt_id: int
    source_image_id: int
    provider_job_id: Optional[str] = None
    quality_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SceneAssetPairRead(BaseModel):
    scene_id: int
    scene_number: int
    image: Optional[GeneratedImageRead] = None
    clip: Optional[GeneratedClipRead] = None
