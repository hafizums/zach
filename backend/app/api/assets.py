from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.asset_schema import SceneAssetPairRead, GeneratedImageRead, GeneratedClipRead
from app.schemas.provider_schema import ImageGenerationRequest, ImageGenerationEstimateRequest
from app.services import asset_service, asset_generation_service, project_service, script_service, scene_service, prompt_service, model_catalog_service
from app.models.prompt import ImagePrompt, VideoPrompt

router = APIRouter()


def _require_confirmation_if_paid(db: Session, provider_name: str, model_name: str, confirmed: bool) -> None:
    model = model_catalog_service.get_model(db, provider_name, model_name, "image")
    if not model or not model.is_enabled:
        return
    is_paid = model.cost_hint == "paid" or model.is_mock is False
    if is_paid and not confirmed:
        raise HTTPException(status_code=400, detail="Paid provider generation requires explicit confirmation.")


@router.post("/projects/{project_id}/assets/images/estimate")
def estimate_project_images(
    project_id: int,
    request: Optional[ImageGenerationEstimateRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = ImageGenerationEstimateRequest()

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return asset_generation_service.estimate_image_generation(
        db, project, request.provider_name, request.model_name
    )


@router.post("/scenes/{scene_id}/assets/image/estimate")
def estimate_scene_image_retry(
    scene_id: int,
    request: Optional[ImageGenerationEstimateRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = ImageGenerationEstimateRequest()

    return asset_generation_service.estimate_scene_image_retry(
        db, scene_id, request.provider_name, request.model_name
    )

@router.post("/projects/{project_id}/assets/images/generate", response_model=List[SceneAssetPairRead])
def generate_project_images(
    project_id: int,
    request: Optional[ImageGenerationRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = ImageGenerationRequest(provider_name="mock", model_name="mock-image")

    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    if not approved_script:
        raise HTTPException(status_code=400, detail="No approved script found for this project.")

    valid_statuses = ["VIDEO_PROMPTS_READY", "IMAGES_GENERATED", "CLIPS_GENERATED", "VOICEOVER_READY", "SUBTITLES_READY", "FINAL_RENDER_READY"]
    if project.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Cannot generate images before prompts are approved.")

    _require_confirmation_if_paid(db, request.provider_name, request.model_name, request.confirmed)

    scenes = scene_service.list_script_scenes(db, approved_script.id)

    # Validation pass: ensure all prompts are approved before touching any data
    for scene in scenes:
        pair = prompt_service.list_scene_prompt_pair(db, scene.id)
        if not pair or not pair.image_prompt or pair.image_prompt.status != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Image prompt for scene {scene.scene_number} is not APPROVED.")

    # Phase 1: Generate and validate all image results before touching any records.
    # If any scene fails, no GeneratedImage rows are written and no old images are
    # deactivated.
    pending: list[tuple] = []
    for scene in scenes:
        pair = prompt_service.list_scene_prompt_pair(db, scene.id)
        prompt_model = db.query(ImagePrompt).filter(ImagePrompt.id == pair.image_prompt.id).first()
        img_in = asset_generation_service.generate_image(
            db, project, approved_script, scene, prompt_model,
            provider_name=request.provider_name,
            model_name=request.model_name,
        )
        pending.append((scene, img_in))

    # Phase 2: All results are valid — write every record.
    for scene, img_in in pending:
        asset_service.create_generated_image(db, img_in)
        asset_service.deactivate_scene_images(db, scene.id, keep_latest=True)

    if project.status == "VIDEO_PROMPTS_READY":
        project.status = "IMAGES_GENERATED"
        db.add(project)
        db.commit()

    return asset_service.list_project_assets(db, project_id)

@router.post("/projects/{project_id}/assets/clips/generate", response_model=List[SceneAssetPairRead])
def generate_project_clips(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    scripts = script_service.list_project_scripts(db, project_id)
    approved_script = next((s for s in scripts if s.status == "APPROVED"), None)
    if not approved_script:
        raise HTTPException(status_code=400, detail="No approved script found for this project.")
    
    scenes = scene_service.list_script_scenes(db, approved_script.id)
    
    # Validation pass
    for scene in scenes:
        pair = prompt_service.list_scene_prompt_pair(db, scene.id)
        if not pair or not pair.video_prompt or pair.video_prompt.status != "APPROVED":
            raise HTTPException(status_code=400, detail=f"Video prompt for scene {scene.scene_number} is not APPROVED.")
            
        img = asset_service.get_active_image_for_scene(db, scene.id)
        if not img:
            raise HTTPException(status_code=400, detail=f"Cannot generate clip for scene {scene.scene_number} because it has no active image.")
            
    for scene in scenes:
        img = asset_service.get_active_image_for_scene(db, scene.id)
        pair = prompt_service.list_scene_prompt_pair(db, scene.id)
        if pair and pair.video_prompt:
            asset_service.deactivate_scene_clips(db, scene.id)
            prompt_model = db.query(VideoPrompt).filter(VideoPrompt.id == pair.video_prompt.id).first()
            clip_in = asset_generation_service.generate_mock_clip(db, project, approved_script, scene, prompt_model, img)
            asset_service.create_generated_clip(db, clip_in)
            
    return asset_service.list_project_assets(db, project_id)

@router.post("/scenes/{scene_id}/assets/image/retry", response_model=SceneAssetPairRead)
def retry_scene_image(
    scene_id: int,
    request: Optional[ImageGenerationRequest] = None,
    db: Session = Depends(get_db),
):
    if request is None:
        request = ImageGenerationRequest(provider_name="mock", model_name="mock-image")

    _require_confirmation_if_paid(db, request.provider_name, request.model_name, request.confirmed)

    scene = scene_service.get_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")

    project = project_service.get_project(db, scene.project_id)
    script = script_service.get_script(db, scene.script_id)

    pair = prompt_service.list_scene_prompt_pair(db, scene.id)
    if not pair or not pair.image_prompt:
        raise HTTPException(status_code=400, detail="Missing image prompt")
    if pair.image_prompt.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Image prompt must be APPROVED to generate assets.")

    prompt_model = db.query(ImagePrompt).filter(ImagePrompt.id == pair.image_prompt.id).first()
    img_in = asset_generation_service.generate_image(
        db, project, script, scene, prompt_model,
        provider_name=request.provider_name,
        model_name=request.model_name,
        operation="image_retry",
    )
    asset_service.create_generated_image(db, img_in)
    asset_service.deactivate_scene_images(db, scene.id, keep_latest=True)

    return asset_service.list_scene_assets(db, scene.id)

@router.post("/scenes/{scene_id}/assets/clip/retry", response_model=SceneAssetPairRead)
def retry_scene_clip(scene_id: int, db: Session = Depends(get_db)):
    scene = scene_service.get_scene(db, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
        
    project = project_service.get_project(db, scene.project_id)
    script = script_service.get_script(db, scene.script_id)
    
    pair = prompt_service.list_scene_prompt_pair(db, scene.id)
    if not pair or not pair.video_prompt:
        raise HTTPException(status_code=400, detail="Missing video prompt")
    if pair.video_prompt.status != "APPROVED":
        raise HTTPException(status_code=400, detail="Video prompt must be APPROVED to generate assets.")
        
    img = asset_service.get_active_image_for_scene(db, scene.id)
    if not img:
        raise HTTPException(status_code=400, detail="Cannot generate clip without active image")
        
    asset_service.deactivate_scene_clips(db, scene.id)
    prompt_model = db.query(VideoPrompt).filter(VideoPrompt.id == pair.video_prompt.id).first()
    clip_in = asset_generation_service.generate_mock_clip(db, project, script, scene, prompt_model, img)
    asset_service.create_generated_clip(db, clip_in)
    
    return asset_service.list_scene_assets(db, scene.id)

@router.get("/projects/{project_id}/assets", response_model=List[SceneAssetPairRead])
def list_project_assets(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return asset_service.list_project_assets(db, project_id)

@router.get("/scenes/{scene_id}/assets", response_model=SceneAssetPairRead)
def list_scene_assets(scene_id: int, db: Session = Depends(get_db)):
    assets = asset_service.list_scene_assets(db, scene_id)
    if not assets:
        raise HTTPException(status_code=404, detail="Scene not found")
    return assets

@router.post("/projects/{project_id}/assets/approve")
def approve_assets(project_id: int, db: Session = Depends(get_db)):
    project = project_service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    success = asset_service.approve_project_assets(db, project_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve assets. Ensure assets exist.")
        
    return {"status": "success", "message": "Assets approved"}
