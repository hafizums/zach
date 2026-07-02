from typing import List, Tuple
import uuid
import base64
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.models.prompt import ImagePrompt, VideoPrompt
from app.models.generated_asset import GeneratedImage
from app.schemas.asset_schema import GeneratedImageCreate, GeneratedClipCreate
from app.providers.mock_provider import MockImageProvider, MockVideoProvider

def generate_mock_image(project: VideoProject, script: Script, scene: Scene, prompt: ImagePrompt) -> GeneratedImageCreate:
    """
    Deterministically generates a mock image using MockImageProvider.
    """
    provider = MockImageProvider()
    job = provider.generate_image(prompt.prompt_text, "9:16")
    
    # Create a simple SVG with text for the placeholder
    text_content = f"Scene {scene.scene_number}"
    svg_data = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <rect width="1080" height="1920" fill="#2d3748"/>
  <text x="540" y="960" font-family="sans-serif" font-size="80" fill="#cbd5e0" text-anchor="middle" dominant-baseline="middle">{text_content}</text>
  <text x="540" y="1060" font-family="sans-serif" font-size="40" fill="#a0aec0" text-anchor="middle" dominant-baseline="middle">{prompt.prompt_text[:40]}...</text>
</svg>"""
    
    encoded_svg = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
    file_url = f"data:image/svg+xml;base64,{encoded_svg}"
    
    return GeneratedImageCreate(
        project_id=project.id,
        script_id=script.id,
        scene_id=scene.id,
        image_prompt_id=prompt.id,
        provider_job_id=job.job_id,
        file_url=file_url,
        thumbnail_url=file_url,
        width=1080,
        height=1920,
        status="COMPLETED",
        is_active=True
    )

def generate_mock_clip(project: VideoProject, script: Script, scene: Scene, prompt: VideoPrompt, source_image: GeneratedImage) -> GeneratedClipCreate:
    """
    Deterministically generates a mock clip using MockVideoProvider.
    """
    provider = MockVideoProvider()
    job = provider.generate_video(source_image.file_url, prompt.prompt_text, prompt.duration_seconds, "9:16")
    
    file_url = f"/storage/projects/{project.id}/clips/scene_{scene.scene_number}_clip_{job.job_id}.mp4"
    
    return GeneratedClipCreate(
        project_id=project.id,
        script_id=script.id,
        scene_id=scene.id,
        video_prompt_id=prompt.id,
        source_image_id=source_image.id,
        provider_job_id=job.job_id,
        file_url=file_url,
        duration_seconds=prompt.duration_seconds,
        width=1080,
        height=1920,
        fps=30,
        status="COMPLETED",
        is_active=True
    )
