from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime

class ProviderModelBase(BaseModel):
    provider_name: str
    model_name: str
    display_name: str
    modality: str
    is_enabled: Optional[bool] = True
    is_mock: Optional[bool] = True
    supports_aspect_ratio: Optional[str] = None
    supports_duration_seconds: Optional[str] = None
    default_params_json: Optional[str] = None
    cost_hint: Optional[str] = None

class ProviderModelCreate(ProviderModelBase):
    pass

class ProviderModelUpdate(BaseModel):
    display_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    supports_aspect_ratio: Optional[str] = None
    supports_duration_seconds: Optional[str] = None
    default_params_json: Optional[str] = None
    cost_hint: Optional[str] = None

class ProviderModelRead(ProviderModelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProviderRunLogBase(BaseModel):
    project_id: Optional[int] = None
    scene_id: Optional[int] = None
    provider_name: str
    model_name: str
    modality: str
    operation: str
    provider_job_id: Optional[str] = None
    status: Optional[str] = "COMPLETED"
    request_json: Optional[Any] = None
    response_json: Optional[Any] = None
    error_message: Optional[str] = None

class ProviderRunLogCreate(ProviderRunLogBase):
    pass

class ProviderRunLogRead(ProviderRunLogBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProviderPreflightRequest(BaseModel):
    provider_name: str
    model_name: str
    modality: str

class ProviderPreflightResult(BaseModel):
    ok: bool
    provider_name: str
    model_name: str
    modality: str
    message: str
