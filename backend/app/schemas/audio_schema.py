from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class VoiceoverBase(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-audio"
    voice_id: str = "mock-narrator"
    language: str = "en"
    narration_text: str
    file_url: str
    duration_seconds: int
    status: str = "COMPLETED"
    is_active: bool = True
    provider_job_id: Optional[str] = None

class VoiceoverCreate(VoiceoverBase):
    project_id: int
    script_id: int

class VoiceoverRead(VoiceoverBase):
    id: int
    project_id: int
    script_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
