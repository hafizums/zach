from typing import List
from app.models.video_project import VideoProject
from app.models.scene import Scene
from app.models.audio import Voiceover
from app.schemas.subtitle_schema import SubtitleSegmentCreate

def generate_mock_subtitles(project: VideoProject, voiceover: Voiceover, scenes: List[Scene]) -> List[SubtitleSegmentCreate]:
    """
    Generates deterministic subtitle segments from scenes.
    For this MVP, we create one segment per scene using estimated timing.
    """
    segments = []
    
    if not scenes:
        return segments
        
    # We estimate segment timing based on equal division of total duration for MVP
    # Or, if scene prompts have durations, we could use them. But scenes don't directly have duration.
    # Let's just divide the voiceover duration equally across scenes.
    duration_per_scene = voiceover.duration_seconds / len(scenes)
    
    current_time = 0.0
    
    for i, scene in enumerate(scenes):
        start_time = current_time
        end_time = current_time + duration_per_scene
        
        # Avoid slight floating point overruns
        if i == len(scenes) - 1:
            end_time = float(voiceover.duration_seconds)
            
        segment = SubtitleSegmentCreate(
            project_id=project.id,
            voiceover_id=voiceover.id,
            index=i,
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            text=scene.narration_text if scene.narration_text else f"Mock subtitle {i+1}",
            style="bold_white_black_stroke",
            status="DRAFT"
        )
        segments.append(segment)
        
        current_time += duration_per_scene
        
    return segments
