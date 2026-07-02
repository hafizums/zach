import math
import json
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.video_project import VideoProject
from app.models.script import Script
from app.schemas.scene_schema import SceneCreate
from app.services import provider_registry, provider_run_service, provider_preflight_service
from app.schemas.provider_schema import ProviderRunLogCreate

def generate_mock_scenes(
    db: Session,
    project: VideoProject, 
    script: Script,
    provider_name: str = "mock",
    model_name: str = "mock-llm"
) -> List[SceneCreate]:
    
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "llm")
    provider = provider_registry.get_provider(provider_name, "llm")
    if not provider:
        raise HTTPException(status_code=400, detail="LLM Provider not found")
        
    if provider_name == "openai":
        prompt = f"Create a scene plan for a {project.duration_target} second video about {project.topic}. The script is: {script.script_text}"
        if script.hook: prompt += f" Hook: {script.hook}"
        if script.payoff: prompt += f" Payoff: {script.payoff}"
        
        scene_schema = {
            "type": "object",
            "properties": {
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer"},
                            "duration_seconds": {"type": "integer"},
                            "narration_text": {"type": "string"},
                            "visual_summary": {"type": "string"},
                            "camera_direction": {"type": "string"},
                            "motion_direction": {"type": "string"},
                            "sfx_notes": {"type": "string"}
                        },
                        "required": ["scene_number", "duration_seconds", "narration_text", "visual_summary", "camera_direction", "motion_direction", "sfx_notes"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["scenes"],
            "additionalProperties": False
        }
        
        try:
            result = provider.generate_structured_json(
                prompt=prompt,
                model_name=model_name,
                schema=scene_schema,
                system_prompt="You are a video director. Break the script into 6 to 10 logical scenes."
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Scene generation failed: {str(e)}")
            
        if not isinstance(result, dict) or "scenes" not in result or not isinstance(result["scenes"], list):
            raise HTTPException(status_code=400, detail="Malformed scenes generated")
            
        if len(result["scenes"]) < 6 or len(result["scenes"]) > 10:
            raise HTTPException(status_code=400, detail="Must produce 6 to 10 scenes")
            
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            provider_name=provider_name,
            model_name=model_name,
            modality="llm",
            operation="scene_planning",
            provider_job_id=result.get("provider_job_id"),
            request_json=prompt,
            response_json=result
        ))
        
        scenes_to_create = []
        for s in result["scenes"]:
            scenes_to_create.append(SceneCreate(
                project_id=project.id,
                script_id=script.id,
                scene_number=s["scene_number"],
                duration_seconds=s["duration_seconds"],
                narration_text=s["narration_text"],
                visual_summary=s["visual_summary"],
                camera_direction=s["camera_direction"],
                motion_direction=s["motion_direction"],
                sfx_notes=s["sfx_notes"]
            ))
        return scenes_to_create
        
    # --- Fallback to deterministic mock logic ---
    total_scenes = 8
    target_duration = project.duration_target
    base_duration = math.floor(target_duration / total_scenes)
    remainder = target_duration % total_scenes
    words = script.script_text.split()
    chunk_size = math.ceil(len(words) / total_scenes) if words else 0
    scenes_to_create = []
    
    for i in range(total_scenes):
        scene_number = i + 1
        duration = base_duration + (1 if i < remainder else 0)
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        narration = " ".join(words[start_idx:end_idx]) if words else f"Mock narration for scene {scene_number}"
        if scene_number == 1 and script.hook:
            narration = f"{script.hook} {narration}"
        if scene_number == total_scenes and script.payoff:
            narration = f"{narration} {script.payoff}"
            
        scene = SceneCreate(
            project_id=project.id,
            script_id=script.id,
            scene_number=scene_number,
            duration_seconds=duration,
            narration_text=narration.strip() or f"Fallback narration {scene_number}",
            visual_summary=f"Visual representation of scene {scene_number} showing the topic: {project.topic}",
            camera_direction="Slow zoom in" if i % 2 == 0 else "Pan right",
            motion_direction="Dynamic movement" if i % 3 == 0 else "Subtle ambient motion",
            sfx_notes="Whoosh" if i % 2 == 0 else "Subtle background ambiance"
        )
        scenes_to_create.append(scene)
        
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name="mock",
        model_name="mock-llm",
        modality="llm",
        operation="scene_planning",
        request_json="deterministic mock",
        response_json={"scenes_count": 8}
    ))
        
    return scenes_to_create
