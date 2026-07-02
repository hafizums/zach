import json
import time
from typing import List
from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.models.audio import Voiceover
from app.models.subtitle import SubtitleSegment
from app.models.generated_asset import GeneratedClip
from app.models.scene import Scene
from app.schemas.render_schema import FinalRenderCreate
from app.schemas.provider_schema import ProviderRunLogCreate
from app.services import provider_registry, provider_run_service

def generate_mock_render(
    db: Session,
    project: VideoProject,
    voiceover: Voiceover,
    subtitles: List[SubtitleSegment],
    scenes: List[Scene],
    clips_by_scene: dict[int, GeneratedClip]
) -> FinalRenderCreate:
    """
    Builds a deterministic manifest and returns a FinalRenderCreate schema.
    No FFmpeg execution happens here.
    """
    
    clip_manifests = []
    for scene in scenes:
        clip = clips_by_scene.get(scene.id)
        if clip:
            clip_manifests.append({
                "scene_id": scene.id,
                "scene_number": scene.scene_number,
                "clip_id": clip.id,
                "file_url": clip.file_url,
                "duration_seconds": clip.duration_seconds
            })
            
    voiceover_manifest = {
        "voiceover_id": voiceover.id,
        "file_url": voiceover.file_url,
        "duration_seconds": voiceover.duration_seconds,
        "provider_job_id": voiceover.provider_job_id
    }
    
    subtitle_manifests = [
        {
            "index": sub.index,
            "start_time": sub.start_time,
            "end_time": sub.end_time,
            "text": sub.text,
            "style": sub.style
        }
        for sub in subtitles
    ]
    
    timestamp = int(time.time())
    output_url = f"/storage/projects/{project.id}/renders/final_render_mock_{timestamp}.mp4"
    
    manifest_dict = {
        "project_id": project.id,
        "aspect_ratio": project.aspect_ratio,
        "width": 1080 if project.aspect_ratio == "9:16" else 1920,
        "height": 1920 if project.aspect_ratio == "9:16" else 1080,
        "duration_seconds": voiceover.duration_seconds,
        "output_url": output_url,
        "clips": clip_manifests,
        "voiceover": voiceover_manifest,
        "subtitles": subtitle_manifests
    }
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name="mock",
        model_name="mock-render",
        modality="render",
        operation="final_render",
        request_json={"manifest": manifest_dict},
        response_json={"output_url": output_url}
    ))
    
    return FinalRenderCreate(
        project_id=project.id,
        voiceover_id=voiceover.id,
        output_url=output_url,
        manifest_json=json.dumps(manifest_dict),
        duration_seconds=voiceover.duration_seconds,
        aspect_ratio=project.aspect_ratio,
        width=manifest_dict["width"],
        height=manifest_dict["height"]
    )
