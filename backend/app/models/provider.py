from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base
from app.models.video_project import current_utc_time

class ProviderModel(Base):
    __tablename__ = "provider_models"

    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    modality = Column(String, nullable=False)
    
    is_enabled = Column(Boolean, default=True)
    is_mock = Column(Boolean, default=True)
    supports_aspect_ratio = Column(String, nullable=True)
    supports_duration_seconds = Column(String, nullable=True)
    default_params_json = Column(Text, nullable=True)
    cost_hint = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
    updated_at = Column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)

class ProviderRunLog(Base):
    __tablename__ = "provider_run_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, nullable=True)
    scene_id = Column(Integer, nullable=True)
    provider_name = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    modality = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    
    provider_job_id = Column(String, nullable=True)
    status = Column(String, default="COMPLETED")
    
    request_json = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=current_utc_time)
