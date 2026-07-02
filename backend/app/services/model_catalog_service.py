from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.provider import ProviderModel
from app.schemas.provider_schema import ProviderModelCreate, ProviderModelUpdate

def seed_default_mock_models(db: Session) -> None:
    defaults = [
        {"provider_name": "mock", "model_name": "mock-llm", "display_name": "Mock LLM", "modality": "llm", "cost_hint": "mock-free"},
        {"provider_name": "mock", "model_name": "mock-image", "display_name": "Mock Image Generator", "modality": "image", "cost_hint": "mock-free", "supports_aspect_ratio": "9:16,16:9,1:1"},
        {"provider_name": "mock", "model_name": "mock-video", "display_name": "Mock Video Generator", "modality": "video", "cost_hint": "mock-free", "supports_duration_seconds": "3,5,8"},
        {"provider_name": "mock", "model_name": "mock-audio", "display_name": "Mock TTS", "modality": "audio", "cost_hint": "mock-free"},
        {"provider_name": "mock", "model_name": "mock-transcription", "display_name": "Mock Transcription", "modality": "transcription", "cost_hint": "mock-free"},
        {"provider_name": "mock", "model_name": "mock-render", "display_name": "Mock Renderer", "modality": "render", "cost_hint": "mock-free"}
    ]
    
    for default in defaults:
        existing = db.query(ProviderModel).filter(
            ProviderModel.provider_name == default["provider_name"],
            ProviderModel.model_name == default["model_name"]
        ).first()
        
        if not existing:
            new_model = ProviderModel(**default)
            db.add(new_model)
    
    db.commit()

def list_models(db: Session, skip: int = 0, limit: int = 100) -> List[ProviderModel]:
    return db.query(ProviderModel).offset(skip).limit(limit).all()

def list_enabled_models(db: Session) -> List[ProviderModel]:
    return db.query(ProviderModel).filter(ProviderModel.is_enabled == True).all()

def list_models_by_modality(db: Session, modality: str) -> List[ProviderModel]:
    return db.query(ProviderModel).filter(ProviderModel.modality == modality).all()

def get_model_by_id(db: Session, model_id: int) -> Optional[ProviderModel]:
    return db.query(ProviderModel).filter(ProviderModel.id == model_id).first()

def get_model(db: Session, provider_name: str, model_name: str, modality: str) -> Optional[ProviderModel]:
    return db.query(ProviderModel).filter(
        ProviderModel.provider_name == provider_name,
        ProviderModel.model_name == model_name,
        ProviderModel.modality == modality
    ).first()

def create_model(db: Session, model_in: ProviderModelCreate) -> ProviderModel:
    db_model = ProviderModel(**model_in.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def update_model(db: Session, model_id: int, model_in: ProviderModelUpdate) -> Optional[ProviderModel]:
    db_model = get_model_by_id(db, model_id)
    if not db_model:
        return None
    
    update_data = model_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_model, key, value)
        
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def disable_model(db: Session, model_id: int) -> Optional[ProviderModel]:
    return update_model(db, model_id, ProviderModelUpdate(is_enabled=False))

def enable_model(db: Session, model_id: int) -> Optional[ProviderModel]:
    return update_model(db, model_id, ProviderModelUpdate(is_enabled=True))
