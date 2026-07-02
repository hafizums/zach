from fastapi import APIRouter
from app.core.config import settings
from app.core.storage import init_storage
from pathlib import Path

router = APIRouter()

@router.get("/health")
def health_check():
    # Check if storage exists (initialize if not)
    storage_exists = init_storage()
    
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "environment": settings.environment,
        "storage_path_exists": storage_exists
    }
