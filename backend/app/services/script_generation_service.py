from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.schemas.script_schema import ScriptCreate
from app.services import script_service, provider_registry, provider_run_service, provider_preflight_service
from app.schemas.provider_schema import ProviderRunLogCreate

from fastapi import HTTPException

def generate_script_for_project(
    db: Session, 
    project: VideoProject,
    provider_name: str = "mock",
    model_name: str = "mock-llm"
) -> ScriptCreate:
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "llm")
    
    provider = provider_registry.get_provider(provider_name, "llm")
    if not provider:
        raise HTTPException(status_code=400, detail="LLM Provider not found")

    prompt = f"Topic: {project.topic}, Language: {project.language}, Duration Target: {project.duration_target}s"
    
    script_schema = {
        "type": "object",
        "properties": {
            "hook": {"type": "string"},
            "script": {"type": "string"},
            "word_count": {"type": "integer"},
            "estimated_duration_seconds": {"type": "integer"},
            "payoff": {"type": "string"}
        },
        "required": ["hook", "script", "word_count", "estimated_duration_seconds", "payoff"],
        "additionalProperties": False
    }

    try:
        if provider_name == "openai":
            result = provider.generate_structured_json(
                prompt=prompt,
                model_name=model_name,
                schema=script_schema,
                system_prompt="You are a scriptwriter. Output only the requested JSON structure."
            )
        else:
            result = provider.generate_text(prompt, model_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Script generation failed: {str(e)}")
    
    # Ensure no partial writes or swallowed errors
    if not isinstance(result, dict) or "script" not in result:
        raise HTTPException(status_code=400, detail="Malformed script generated")

    # Clean the response for logging (e.g. drop secrets if any were in request, though they shouldn't be here)
    provider_job_id = result.get("provider_job_id")
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name=provider_name,
        model_name=model_name,
        modality="llm",
        operation="script_generation",
        provider_job_id=provider_job_id,
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
