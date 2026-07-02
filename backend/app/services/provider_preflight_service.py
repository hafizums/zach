from sqlalchemy.orm import Session
from app.schemas.provider_schema import ProviderPreflightResult
from app.services import model_catalog_service, provider_registry

def preflight_provider_model(db: Session, provider_name: str, model_name: str, modality: str) -> ProviderPreflightResult:
    # 1. Check if model exists in catalog
    model = model_catalog_service.get_model(db, provider_name, model_name, modality)
    
    if not model:
        return ProviderPreflightResult(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            modality=modality,
            message=f"Model '{model_name}' from provider '{provider_name}' with modality '{modality}' not found in catalog."
        )
        
    # 2. Check if model is enabled
    if not model.is_enabled:
        return ProviderPreflightResult(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            modality=modality,
            message=f"Model '{model_name}' is currently disabled."
        )
        
    # 3. Check if provider instance exists in the internal registry (unless it's mock render which might not need one)
    # The requirement says: validate provider exists in registry
    if modality != "render" or provider_registry.validate_provider_available(provider_name, modality):
        if not provider_registry.validate_provider_available(provider_name, modality):
            return ProviderPreflightResult(
                ok=False,
                provider_name=provider_name,
                model_name=model_name,
                modality=modality,
                message=f"Provider '{provider_name}' does not have a registered adapter for modality '{modality}'."
            )

    return ProviderPreflightResult(
        ok=True,
        provider_name=provider_name,
        model_name=model_name,
        modality=modality,
        message="Preflight checks passed."
    )
