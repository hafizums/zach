import json
from typing import List, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.schemas.prompt_schema import ImagePromptCreate, VideoPromptCreate
from app.services import provider_registry, provider_run_service, provider_preflight_service
from app.schemas.provider_schema import ProviderRunLogCreate

def generate_mock_prompt_pairs(
    db: Session,
    project: VideoProject, 
    script: Script, 
    scenes: List[Scene],
    provider_name: str = "mock",
    model_name: str = "mock-llm"
) -> Tuple[List[ImagePromptCreate], List[VideoPromptCreate]]:
    
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "llm")
    provider = provider_registry.get_provider(provider_name, "llm")
    if not provider:
        raise HTTPException(status_code=400, detail="LLM Provider not found")
        
    image_prompts = []
    video_prompts = []
    base_image_prompt = "vertical 9:16, semi-realistic 3D educational explainer, dark neutral background, clean science-documentary look, no text, no logo, no watermark"
    base_image_negative = "text, subtitles, watermark, logo, extra limbs, distorted anatomy, gore, clutter"
    
    if provider_name == "openai":
        # Build prompt to generate pairs for all scenes at once
        prompt = (
            f"Create image and video prompt pairs for each of the {len(scenes)} scenes below.\n"
            "Each pair must include: image_prompt_text, image_negative_prompt, image_style_lock, "
            "video_prompt_text, video_negative_prompt, video_motion_strength, video_camera_lock.\n"
        )
        for s in scenes:
            prompt += (
                f"Scene {s.scene_number}: {s.visual_summary} "
                f"(camera: {s.camera_direction or 'static'}, motion: {s.motion_direction or 'subtle'})\n"
            )

        schema = {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_number": {"type": "integer"},
                            "image_prompt_text": {"type": "string"},
                            "image_negative_prompt": {"type": "string"},
                            "image_style_lock": {"type": "string"},
                            "video_prompt_text": {"type": "string"},
                            "video_negative_prompt": {"type": "string"},
                            "video_motion_strength": {"type": "string"},
                            "video_camera_lock": {"type": "string"},
                        },
                        "required": [
                            "scene_number",
                            "image_prompt_text",
                            "image_negative_prompt",
                            "image_style_lock",
                            "video_prompt_text",
                            "video_negative_prompt",
                            "video_motion_strength",
                            "video_camera_lock",
                        ],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["prompts"],
            "additionalProperties": False,
        }

        REQUIRED_ITEM_FIELDS = {
            "scene_number", "image_prompt_text", "image_negative_prompt", "image_style_lock",
            "video_prompt_text", "video_negative_prompt", "video_motion_strength", "video_camera_lock",
        }

        try:
            result = provider.generate_structured_json(
                prompt=prompt,
                model_name=model_name,
                schema=schema,
                system_prompt="You are an AI generation expert. Create detailed, cinematic image and video prompts for a 3D educational short-form video.",
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Prompt generation failed: {str(e)}")

        if not isinstance(result, dict) or "prompts" not in result or not isinstance(result["prompts"], list):
            raise HTTPException(status_code=400, detail="Malformed prompts generated")

        if len(result["prompts"]) != len(scenes):
            raise HTTPException(
                status_code=400,
                detail=f"Generated prompts count ({len(result['prompts'])}) does not match scenes count ({len(scenes)})",
            )

        # Validate every item has all required fields before touching the DB
        generated_prompts_map: Dict = {}
        for item in result["prompts"]:
            missing = REQUIRED_ITEM_FIELDS - set(item.keys())
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Prompt item for scene {item.get('scene_number', '?')} missing fields: {missing}",
                )
            generated_prompts_map[item["scene_number"]] = item

        for scene in scenes:
            gen_data = generated_prompts_map.get(scene.scene_number)
            if not gen_data:
                raise HTTPException(status_code=400, detail=f"Missing prompts for scene {scene.scene_number}")

            img_prompt = ImagePromptCreate(
                project_id=project.id,
                script_id=script.id,
                scene_id=scene.id,
                prompt_text=gen_data["image_prompt_text"],
                negative_prompt=gen_data["image_negative_prompt"],
                style_lock=gen_data["image_style_lock"],
                aspect_ratio="9:16",
                provider="mock",
                model="mock-image",
            )
            image_prompts.append(img_prompt)

            vid_prompt = VideoPromptCreate(
                project_id=project.id,
                script_id=script.id,
                scene_id=scene.id,
                prompt_text=gen_data["video_prompt_text"],
                negative_prompt=gen_data["video_negative_prompt"],
                duration_seconds=scene.duration_seconds,
                motion_strength=gen_data["video_motion_strength"],
                camera_lock=gen_data["video_camera_lock"],
                provider="mock",
                model="mock-video",
            )
            video_prompts.append(vid_prompt)

        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            provider_name=provider_name,
            model_name=model_name,
            modality="llm",
            operation="prompt_generation",
            provider_job_id=result.get("provider_job_id"),
            request_json=prompt,
            response_json=result,
        ))

        return image_prompts, video_prompts

    # --- Fallback to deterministic mock logic ---
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
        
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name="mock",
        model_name="mock-llm",
        modality="llm",
        operation="prompt_generation",
        request_json="deterministic mock",
        response_json={"prompts_count": len(scenes)}
    ))
        
    return image_prompts, video_prompts
