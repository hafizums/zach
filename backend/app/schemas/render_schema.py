from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FinalRenderBase(BaseModel):
    project_id: int
    voiceover_id: int
    output_url: str
    manifest_json: str
    duration_seconds: int
    aspect_ratio: Optional[str] = "9:16"
    width: Optional[int] = 1080
    height: Optional[int] = 1920

class FinalRenderCreate(FinalRenderBase):
    pass

class FinalRenderRead(FinalRenderBase):
    id: int
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RenderManifestRead(BaseModel):
    project_id: int
    aspect_ratio: str
    width: int
    height: int
    duration_seconds: int
    output_url: str
    clips: List[Dict[str, Any]]
    voiceover: Dict[str, Any]
    subtitles: List[Dict[str, Any]]
