from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.schemas.script_schema import ScriptCreate
from app.services import script_service, provider_registry, provider_run_service, provider_preflight_service
from app.schemas.provider_schema import ProviderRunLogCreate

def generate_script_for_project(db: Session, project: VideoProject) -> ScriptCreate:
    provider_preflight_service.require_provider_model(db, "mock", "mock-llm", "llm")
    
    provider = provider_registry.get_provider("mock", "llm")
    prompt = f"Topic: {project.topic}, Language: {project.language}, Duration Target: {project.duration_target}s"
    
    result = provider.generate_text(prompt)
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name="mock",
        model_name="mock-llm",
        modality="llm",
        operation="script_generation",
        request_json=prompt,
        response_json=result
    ))
    
    # Determine new version number
    latest_script = script_service.get_latest_project_script(db, project.id)
    new_version = (latest_script.version + 1) if latest_script else 1

    return ScriptCreate(
        project_id=project.id,
        version=new_version,
        script_text=result.get("script", ""),
        hook=result.get("hook", ""),
        payoff=result.get("payoff", ""),
        word_count=result.get("word_count", 0),
        estimated_duration=result.get("estimated_duration_seconds", 0)
    )
