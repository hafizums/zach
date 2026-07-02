from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from .audio_schema import VoiceoverRead

class SubtitleSegmentBase(BaseModel):
    index: int
    start_time: float
    end_time: float
    text: str
    style: str = "bold_white_black_stroke"
    status: str = "DRAFT"

class SubtitleSegmentCreate(SubtitleSegmentBase):
    project_id: int
    voiceover_id: int

class SubtitleSegmentUpdate(BaseModel):
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    text: Optional[str] = None
    style: Optional[str] = None

class SubtitleSegmentRead(SubtitleSegmentBase):
    id: int
    project_id: int
    voiceover_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AudioSubtitleBundleRead(BaseModel):
    voiceover: VoiceoverRead
    subtitles: List[SubtitleSegmentRead]
