from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.provider_schema import (
    ProviderModelRead,
    ProviderModelCreate,
    ProviderModelUpdate,
    ProviderPreflightRequest,
    ProviderPreflightResult,
    ProviderRunLogRead
)
from app.services import model_catalog_service, provider_preflight_service, provider_run_service

router = APIRouter()

@router.get("/providers/models", response_model=List[ProviderModelRead])
def list_provider_models(db: Session = Depends(get_db)):
    return model_catalog_service.list_models(db)

@router.get("/providers/models/enabled", response_model=List[ProviderModelRead])
def list_enabled_provider_models(db: Session = Depends(get_db)):
    return model_catalog_service.list_enabled_models(db)

@router.get("/providers/models/modality/{modality}", response_model=List[ProviderModelRead])
def list_models_by_modality(modality: str, db: Session = Depends(get_db)):
    return model_catalog_service.list_models_by_modality(db, modality)

@router.post("/providers/models", response_model=ProviderModelRead)
def create_provider_model(model_in: ProviderModelCreate, db: Session = Depends(get_db)):
    # Check if duplicate exists
    existing = model_catalog_service.get_model(db, model_in.provider_name, model_in.model_name, model_in.modality)
    if existing:
        raise HTTPException(status_code=400, detail="Model already exists in catalog.")
    return model_catalog_service.create_model(db, model_in)

@router.patch("/providers/models/{model_id}", response_model=ProviderModelRead)
def update_provider_model(model_id: int, model_in: ProviderModelUpdate, db: Session = Depends(get_db)):
    updated = model_catalog_service.update_model(db, model_id, model_in)
    if not updated:
        raise HTTPException(status_code=404, detail="Model not found.")
    return updated

@router.post("/providers/models/{model_id}/enable", response_model=ProviderModelRead)
def enable_provider_model(model_id: int, db: Session = Depends(get_db)):
    updated = model_catalog_service.enable_model(db, model_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Model not found.")
    return updated

@router.post("/providers/models/{model_id}/disable", response_model=ProviderModelRead)
def disable_provider_model(model_id: int, db: Session = Depends(get_db)):
    updated = model_catalog_service.disable_model(db, model_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Model not found.")
    return updated

@router.post("/providers/preflight", response_model=ProviderPreflightResult)
def preflight_provider(request: ProviderPreflightRequest, db: Session = Depends(get_db)):
    return provider_preflight_service.preflight_provider_model(
        db, 
        request.provider_name, 
        request.model_name, 
        request.modality
    )

@router.get("/providers/runs/recent", response_model=List[ProviderRunLogRead])
def get_recent_provider_runs(limit: int = 50, db: Session = Depends(get_db)):
    return provider_run_service.list_recent_run_logs(db, limit)

@router.get("/projects/{project_id}/provider-runs", response_model=List[ProviderRunLogRead])
def get_project_provider_runs(project_id: int, db: Session = Depends(get_db)):
    return provider_run_service.list_project_run_logs(db, project_id)

@router.get("/scenes/{scene_id}/provider-runs", response_model=List[ProviderRunLogRead])
def get_scene_provider_runs(scene_id: int, db: Session = Depends(get_db)):
    return provider_run_service.list_scene_run_logs(db, scene_id)
