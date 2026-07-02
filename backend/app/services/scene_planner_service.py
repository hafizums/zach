import math
from typing import List
from app.models.video_project import VideoProject
from app.models.script import Script
from app.schemas.scene_schema import SceneCreate

def generate_mock_scenes(project: VideoProject, script: Script) -> List[SceneCreate]:
    """
    Deterministically generates 8 mock scenes based on the approved script and project.
    """
    total_scenes = 8
    target_duration = project.duration_target
    
    # Simple division of duration
    base_duration = math.floor(target_duration / total_scenes)
    remainder = target_duration % total_scenes
    
    # Very simple mock text chunking (just divide into 8 parts roughly)
    words = script.script_text.split()
    chunk_size = math.ceil(len(words) / total_scenes) if words else 0
    
    scenes_to_create = []
    
    for i in range(total_scenes):
        scene_number = i + 1
        
        # Distribute remainder duration to the first few scenes
        duration = base_duration + (1 if i < remainder else 0)
        
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size
        narration = " ".join(words[start_idx:end_idx]) if words else f"Mock narration for scene {scene_number}"
        
        # Add the hook to the first scene if it exists
        if scene_number == 1 and script.hook:
            narration = f"{script.hook} {narration}"
            
        # Add the payoff to the last scene if it exists
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
        
    return scenes_to_create
