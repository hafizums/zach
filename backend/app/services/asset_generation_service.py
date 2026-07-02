from typing import List, Tuple
import uuid
import base64
from sqlalchemy.orm import Session
from app.models.video_project import VideoProject
from app.models.script import Script
from app.models.scene import Scene
from app.models.prompt import ImagePrompt, VideoPrompt
from app.models.generated_asset import GeneratedImage
from app.schemas.asset_schema import GeneratedImageCreate, GeneratedClipCreate
from app.schemas.provider_schema import ProviderRunLogCreate
import json
from fastapi import HTTPException
from app.services import provider_registry, provider_run_service, provider_preflight_service

def generate_mock_image(db: Session, project: VideoProject, script: Script, scene: Scene, prompt: ImagePrompt) -> GeneratedImageCreate:
    """
    Deterministically generates a mock image using registered image provider.
    """
    provider_preflight_service.require_provider_model(db, "mock", "mock-image", "image")
    
    provider = provider_registry.get_provider("mock", "image")
    job = provider.generate_image(prompt.prompt_text, "9:16")
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        scene_id=scene.id,
        provider_name="mock",
        model_name="mock-image",
        modality="image",
        operation="image_generation",
        provider_job_id=job.job_id,
        request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": "9:16"},
        response_json={"job_id": job.job_id}
    ))
    
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
        provider_name="mock",
        model_name="mock-image",
        provider_job_id=job.job_id,
        file_url=file_url,
        thumbnail_url=file_url,
        width=1080,
        height=1920,
        status="COMPLETED",
        is_active=True
    )

def generate_mock_clip(db: Session, project: VideoProject, script: Script, scene: Scene, prompt: VideoPrompt, source_image: GeneratedImage) -> GeneratedClipCreate:
    """
    Deterministically generates a mock clip using registered video provider.
    """
    provider_preflight_service.require_provider_model(db, "mock", "mock-video", "video")
    
    provider = provider_registry.get_provider("mock", "video")
    job = provider.generate_video(source_image.file_url, prompt.prompt_text, prompt.duration_seconds, "9:16")
    
    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        scene_id=scene.id,
        provider_name="mock",
        model_name="mock-video",
        modality="video",
        operation="clip_generation",
        provider_job_id=job.job_id,
        request_json={"source_image": source_image.file_url, "prompt_text": prompt.prompt_text, "duration": prompt.duration_seconds, "aspect_ratio": "9:16"},
        response_json={"job_id": job.job_id}
    ))
    
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


def generate_image(
    db: Session,
    project: VideoProject,
    script: Script,
    scene: Scene,
    prompt: ImagePrompt,
    provider_name: str = "mock",
    model_name: str = "mock-image",
    operation: str = "image_generation",
) -> GeneratedImageCreate:
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "image")

    if provider_name == "mock":
        return generate_mock_image(db, project, script, scene, prompt)

    if provider_name == "wavespeed":
        return _generate_wavespeed_image(db, project, script, scene, prompt, model_name, operation)

    raise HTTPException(status_code=400, detail=f"Unsupported image provider: {provider_name}")


def _is_paid_provider(db: Session, provider_name: str, model_name: str) -> bool:
    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "image")
    if not model:
        return False
    return model.cost_hint == "paid" or model.is_mock is False


def estimate_image_generation(
    db: Session,
    project: VideoProject,
    provider_name: str,
    model_name: str,
) -> dict:
    from app.services import script_service, scene_service, prompt_service
    from app.schemas.provider_schema import ImageGenerationEstimateResponse

    preflight = provider_preflight_service.preflight_provider_model(
        db, provider_name, model_name, "image"
    )

    if not preflight.ok:
        return {
            "ok": False,
            "provider_name": provider_name,
            "model_name": model_name,
            "modality": "image",
            "scene_count": 0,
            "approved_prompt_count": 0,
            "estimated_jobs": 0,
            "cost_hint": "",
            "requires_confirmation": False,
            "message": preflight.message,
        }

    scripts = script_service.list_project_scripts(db, project.id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    if not approved_script:
        return {
            "ok": False,
            "provider_name": provider_name,
            "model_name": model_name,
            "modality": "image",
            "scene_count": 0,
            "approved_prompt_count": 0,
            "estimated_jobs": 0,
            "cost_hint": "",
            "requires_confirmation": False,
            "message": "No approved script found.",
        }

    scenes = scene_service.list_script_scenes(db, approved_script.id)
    approved_count = 0
    for scene in scenes:
        pair = prompt_service.list_scene_prompt_pair(db, scene.id)
        if pair and pair.image_prompt and pair.image_prompt.status == "APPROVED":
            approved_count += 1

    is_paid = _is_paid_provider(db, provider_name, model_name)
    cost_hint = "paid" if is_paid else "mock-free"

    return {
        "ok": True,
        "provider_name": provider_name,
        "model_name": model_name,
        "modality": "image",
        "scene_count": len(scenes),
        "approved_prompt_count": approved_count,
        "estimated_jobs": approved_count,
        "cost_hint": cost_hint,
        "requires_confirmation": is_paid,
        "message": f"Ready to generate {approved_count} images with {model_name}.",
    }


def estimate_scene_image_retry(
    db: Session,
    scene_id: int,
    provider_name: str,
    model_name: str,
) -> dict:
    from app.services import scene_service as svc, prompt_service as ps

    preflight = provider_preflight_service.preflight_provider_model(
        db, provider_name, model_name, "image"
    )

    if not preflight.ok:
        return {
            "ok": False,
            "scene_id": scene_id,
            "scene_number": 0,
            "estimated_jobs": 0,
            "cost_hint": "",
            "requires_confirmation": False,
            "message": preflight.message,
        }

    scene = svc.get_scene(db, scene_id)
    if not scene:
        return {
            "ok": False,
            "scene_id": scene_id,
            "scene_number": 0,
            "estimated_jobs": 0,
            "cost_hint": "",
            "requires_confirmation": False,
            "message": "Scene not found.",
        }

    is_paid = _is_paid_provider(db, provider_name, model_name)
    cost_hint = "paid" if is_paid else "mock-free"

    return {
        "ok": True,
        "scene_id": scene.id,
        "scene_number": scene.scene_number,
        "estimated_jobs": 1,
        "cost_hint": cost_hint,
        "requires_confirmation": is_paid,
        "message": f"Ready to retry image for scene {scene.scene_number} with {model_name}.",
    }


def _generate_wavespeed_image(
    db: Session,
    project: VideoProject,
    script: Script,
    scene: Scene,
    prompt: ImagePrompt,
    model_name: str,
    operation: str = "image_generation",
) -> GeneratedImageCreate:
    from app.services import model_catalog_service

    provider = provider_registry.get_provider("wavespeed", "image")
    if not provider:
        raise HTTPException(status_code=400, detail="WaveSpeed image provider adapter not found")

    model = model_catalog_service.get_model(db, "wavespeed", model_name, "image")
    default_params = {}
    if model and model.default_params_json:
        try:
            default_params = json.loads(model.default_params_json)
        except json.JSONDecodeError:
            pass

    try:
        job = provider.generate_image(
            prompt=prompt.prompt_text,
            aspect_ratio=prompt.aspect_ratio or "9:16",
            model_name=model_name,
            negative_prompt=prompt.negative_prompt,
            default_params=default_params,
        )
    except HTTPException as e:
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            scene_id=scene.id,
            provider_name="wavespeed",
            model_name=model_name,
            modality="image",
            operation=operation,
            provider_job_id=None,
            request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": prompt.aspect_ratio, "negative_prompt": prompt.negative_prompt},
            response_json=None,
            status="FAILED",
            error_message=str(e.detail),
        ))
        raise
    except Exception as e:
        error_msg = f"WaveSpeed generation failed: {str(e)}"
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            scene_id=scene.id,
            provider_name="wavespeed",
            model_name=model_name,
            modality="image",
            operation=operation,
            provider_job_id=None,
            request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": prompt.aspect_ratio, "negative_prompt": prompt.negative_prompt},
            response_json=None,
            status="FAILED",
            error_message=error_msg,
        ))
        raise HTTPException(status_code=400, detail=error_msg)

    result = job.result
    if not isinstance(result, dict):
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            scene_id=scene.id,
            provider_name="wavespeed",
            model_name=model_name,
            modality="image",
            operation=operation,
            provider_job_id=job.job_id,
            request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": prompt.aspect_ratio, "negative_prompt": prompt.negative_prompt},
            response_json={"raw_result": str(result)},
            status="FAILED",
            error_message="WaveSpeed returned malformed response",
        ))
        raise HTTPException(status_code=400, detail="WaveSpeed returned malformed response")

    file_url = result.get("file_url")
    if not file_url:
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            scene_id=scene.id,
            provider_name="wavespeed",
            model_name=model_name,
            modality="image",
            operation=operation,
            provider_job_id=job.job_id,
            request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": prompt.aspect_ratio, "negative_prompt": prompt.negative_prompt},
            response_json=result,
            status="FAILED",
            error_message="WaveSpeed response missing file_url",
        ))
        raise HTTPException(status_code=400, detail="WaveSpeed response missing file_url")

    provider_job_id = result.get("provider_job_id", job.job_id)

    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        scene_id=scene.id,
        provider_name="wavespeed",
        model_name=model_name,
        modality="image",
        operation=operation,
        provider_job_id=provider_job_id,
        request_json={"prompt_text": prompt.prompt_text, "aspect_ratio": prompt.aspect_ratio, "negative_prompt": prompt.negative_prompt},
        response_json=result,
        status="COMPLETED",
    ))

    return GeneratedImageCreate(
        project_id=project.id,
        script_id=script.id,
        scene_id=scene.id,
        image_prompt_id=prompt.id,
        provider_name="wavespeed",
        model_name=model_name,
        provider_job_id=provider_job_id,
        file_url=file_url,
        thumbnail_url=result.get("thumbnail_url", file_url),
        width=result.get("width", 1080),
        height=result.get("height", 1920),
        status="COMPLETED",
        is_active=True,
    )
