from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ScriptBase(BaseModel):
    script_text: str
    word_count: Optional[int] = 0
    estimated_duration: Optional[int] = 0
    hook: Optional[str] = None
    payoff: Optional[str] = None

class ScriptCreate(ScriptBase):
    project_id: int
    version: int

class ScriptUpdate(BaseModel):
    script_text: Optional[str] = None
    hook: Optional[str] = None
    payoff: Optional[str] = None
    estimated_duration: Optional[int] = None
    word_count: Optional[int] = None

class ScriptRead(ScriptBase):
    id: int
    project_id: int
    version: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from app.schemas.provider_schema import GenerationRequest

class ScriptGenerateRequest(GenerationRequest):
    # Optional parameters for script generation tuning could go here
    pass
