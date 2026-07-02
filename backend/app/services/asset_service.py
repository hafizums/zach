from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.generated_asset import GeneratedImage, GeneratedClip
from app.models.scene import Scene
from app.models.video_project import VideoProject
from app.schemas.asset_schema import GeneratedImageCreate, GeneratedClipCreate, SceneAssetPairRead
from app.pipeline.pipeline_states import PipelineState

def deactivate_scene_images(db: Session, scene_id: int) -> None:
    images = db.query(GeneratedImage).filter(GeneratedImage.scene_id == scene_id, GeneratedImage.is_active == True).all()
    for img in images:
        img.is_active = False
        db.add(img)
    db.commit()

def deactivate_scene_clips(db: Session, scene_id: int) -> None:
    clips = db.query(GeneratedClip).filter(GeneratedClip.scene_id == scene_id, GeneratedClip.is_active == True).all()
    for clip in clips:
        clip.is_active = False
        db.add(clip)
    db.commit()

def create_generated_image(db: Session, image_in: GeneratedImageCreate) -> GeneratedImage:
    db_img = GeneratedImage(**image_in.model_dump())
    db.add(db_img)
    db.commit()
    db.refresh(db_img)
    return db_img

def create_generated_clip(db: Session, clip_in: GeneratedClipCreate) -> GeneratedClip:
    db_clip = GeneratedClip(**clip_in.model_dump())
    db.add(db_clip)
    db.commit()
    db.refresh(db_clip)
    return db_clip

def get_active_image_for_scene(db: Session, scene_id: int) -> Optional[GeneratedImage]:
    return db.query(GeneratedImage).filter(GeneratedImage.scene_id == scene_id, GeneratedImage.is_active == True).first()

def get_active_clip_for_scene(db: Session, scene_id: int) -> Optional[GeneratedClip]:
    return db.query(GeneratedClip).filter(GeneratedClip.scene_id == scene_id, GeneratedClip.is_active == True).first()

def list_project_assets(db: Session, project_id: int) -> List[SceneAssetPairRead]:
    scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.scene_number.asc()).all()
    
    images = db.query(GeneratedImage).filter(GeneratedImage.project_id == project_id, GeneratedImage.is_active == True).all()
    clips = db.query(GeneratedClip).filter(GeneratedClip.project_id == project_id, GeneratedClip.is_active == True).all()
    
    img_map = {img.scene_id: img for img in images}
    clip_map = {clip.scene_id: clip for clip in clips}
    
    pairs = []
    for scene in scenes:
        pairs.append(SceneAssetPairRead(
            scene_id=scene.id,
            scene_number=scene.scene_number,
            image=img_map.get(scene.id),
            clip=clip_map.get(scene.id)
        ))
    return pairs

def list_scene_assets(db: Session, scene_id: int) -> Optional[SceneAssetPairRead]:
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return None
        
    img = get_active_image_for_scene(db, scene_id)
    clip = get_active_clip_for_scene(db, scene_id)
    
    return SceneAssetPairRead(
        scene_id=scene.id,
        scene_number=scene.scene_number,
        image=img,
        clip=clip
    )

def approve_project_assets(db: Session, project_id: int) -> bool:
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        return False
        
    images = db.query(GeneratedImage).filter(GeneratedImage.project_id == project_id, GeneratedImage.is_active == True).all()
    clips = db.query(GeneratedClip).filter(GeneratedClip.project_id == project_id, GeneratedClip.is_active == True).all()
    
    if not images and not clips:
        return False
        
    for img in images:
        img.status = "APPROVED"
        db.add(img)
        
    for clip in clips:
        clip.status = "APPROVED"
        db.add(clip)
        
    project.status = PipelineState.CLIPS_GENERATED.value
    db.add(project)
    
    db.commit()
    return True
