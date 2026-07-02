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

class GenerationRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-llm"


class ImageGenerationRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-image"
    confirmed: bool = False


class ImageGenerationEstimateRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-image"


class ImageGenerationEstimateResponse(BaseModel):
    ok: bool
    provider_name: str
    model_name: str
    modality: str = "image"
    scene_count: int = 0
    approved_prompt_count: int = 0
    estimated_jobs: int = 0
    cost_hint: str = "mock-free"
    requires_confirmation: bool = False
    message: str = ""


class VideoGenerationRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-video"
    confirmed: bool = False


class VideoGenerationEstimateRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-video"


class VideoGenerationEstimateResponse(BaseModel):
    ok: bool
    provider_name: str
    model_name: str
    modality: str = "video"
    scene_count: int = 0
    approved_video_prompt_count: int = 0
    active_image_count: int = 0
    estimated_jobs: int = 0
    cost_hint: str = "mock-free"
    requires_confirmation: bool = False
    message: str = ""


class VoiceoverGenerationRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-audio"
    voice_id: Optional[str] = None
    confirmed: bool = False


class VoiceoverGenerationEstimateRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-audio"
    voice_id: Optional[str] = None


class VoiceoverGenerationEstimateResponse(BaseModel):
    ok: bool
    provider_name: str
    model_name: str
    modality: str = "audio"
    script_id: Optional[int] = None
    character_count: int = 0
    estimated_jobs: int = 0
    cost_hint: str = "mock-free"
    requires_confirmation: bool = False
    message: str = ""


class SubtitleGenerationRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-transcription"
    confirmed: bool = False


class SubtitleGenerationEstimateRequest(BaseModel):
    provider_name: str = "mock"
    model_name: str = "mock-transcription"


class SubtitleGenerationEstimateResponse(BaseModel):
    ok: bool
    provider_name: str
    model_name: str
    modality: str = "transcription"
    voiceover_id: Optional[int] = None
    audio_file_url: Optional[str] = None
    estimated_jobs: int = 0
    cost_hint: str = "mock-free"
    requires_confirmation: bool = False
    message: str = ""
