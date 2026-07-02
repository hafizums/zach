from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ImagePromptBase(BaseModel):
    prompt_text: str
    negative_prompt: Optional[str] = None
    style_lock: Optional[str] = None
    aspect_ratio: Optional[str] = "9:16"
    provider: Optional[str] = "mock"
    model: Optional[str] = "mock-image"

class ImagePromptCreate(ImagePromptBase):
    project_id: int
    script_id: int
    scene_id: int

class ImagePromptUpdate(BaseModel):
    prompt_text: Optional[str] = None
    negative_prompt: Optional[str] = None
    style_lock: Optional[str] = None
    aspect_ratio: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class ImagePromptRead(ImagePromptBase):
    id: int
    project_id: int
    script_id: int
    scene_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class VideoPromptBase(BaseModel):
    prompt_text: str
    negative_prompt: Optional[str] = None
    duration_seconds: int
    motion_strength: Optional[str] = "medium"
    camera_lock: Optional[str] = "preserve composition and lighting"
    provider: Optional[str] = "mock"
    model: Optional[str] = "mock-video"

class VideoPromptCreate(VideoPromptBase):
    project_id: int
    script_id: int
    scene_id: int

class VideoPromptUpdate(BaseModel):
    prompt_text: Optional[str] = None
    negative_prompt: Optional[str] = None
    duration_seconds: Optional[int] = None
    motion_strength: Optional[str] = None
    camera_lock: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

class VideoPromptRead(VideoPromptBase):
    id: int
    project_id: int
    script_id: int
    scene_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ScenePromptPairRead(BaseModel):
    scene_id: int
    scene_number: int
    image_prompt: Optional[ImagePromptRead] = None
    video_prompt: Optional[VideoPromptRead] = None

from app.schemas.provider_schema import GenerationRequest

class PromptGenerateRequest(GenerationRequest):
    pass
