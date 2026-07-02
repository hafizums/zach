from typing import List, Tuple
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.schemas.prompt_schema import ImagePromptCreate, VideoPromptCreate

def generate_mock_prompt_pairs(project: VideoProject, script: Script, scenes: List[Scene]) -> Tuple[List[ImagePromptCreate], List[VideoPromptCreate]]:
    """
    Deterministically generates image and video prompts for a list of approved scenes.
    """
    image_prompts = []
    video_prompts = []
    
    # Base styling
    base_image_prompt = "vertical 9:16, semi-realistic 3D educational explainer, dark neutral background, clean science-documentary look, no text, no logo, no watermark"
    base_image_negative = "text, subtitles, watermark, logo, extra limbs, distorted anatomy, gore, clutter"
    
    for scene in scenes:
        # Construct Image Prompt
        img_prompt_text = f"{base_image_prompt}, {scene.visual_summary}, camera: {scene.camera_direction or 'static'}"
        
        img_prompt = ImagePromptCreate(
            project_id=project.id,
            script_id=script.id,
            scene_id=scene.id,
            prompt_text=img_prompt_text,
            negative_prompt=base_image_negative,
            style_lock="3d_explainer_v1",
            aspect_ratio="9:16",
            provider="mock",
            model="mock-image"
        )
        image_prompts.append(img_prompt)
        
        # Construct Video Prompt
        vid_prompt_text = f"animate this reference image, duration: {scene.duration_seconds}s, motion: {scene.motion_direction or 'subtle'}, camera: {scene.camera_direction or 'static'}, preserve subject, lighting, composition, and background, no jump cuts, no morphing, no text"
        
        vid_prompt = VideoPromptCreate(
            project_id=project.id,
            script_id=script.id,
            scene_id=scene.id,
            prompt_text=vid_prompt_text,
            negative_prompt=base_image_negative,
            duration_seconds=scene.duration_seconds,
            motion_strength="medium",
            camera_lock="preserve composition and lighting",
            provider="mock",
            model="mock-video"
        )
        video_prompts.append(vid_prompt)
        
    return image_prompts, video_prompts
