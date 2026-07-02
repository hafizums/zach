from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.schemas.script_schema import ScriptCreate
from app.services import script_service
from app.providers.mock_provider import MockLLMProvider

def generate_script_for_project(db: Session, project: VideoProject) -> ScriptCreate:
    provider = MockLLMProvider()
    prompt = f"Topic: {project.topic}, Language: {project.language}, Duration Target: {project.duration_target}s"
    
    result = provider.generate_text(prompt)
    
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
