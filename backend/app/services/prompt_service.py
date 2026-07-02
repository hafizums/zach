from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.models.prompt import ImagePrompt, VideoPrompt
from app.models.scene import Scene
from app.models.video_project import VideoProject
from app.schemas.prompt_schema import ImagePromptCreate, ImagePromptUpdate, VideoPromptCreate, VideoPromptUpdate, ScenePromptPairRead
from app.pipeline.pipeline_states import PipelineState

def create_image_prompt(db: Session, prompt_in: ImagePromptCreate) -> ImagePrompt:
    db_prompt = ImagePrompt(**prompt_in.model_dump())
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def create_video_prompt(db: Session, prompt_in: VideoPromptCreate) -> VideoPrompt:
    db_prompt = VideoPrompt(**prompt_in.model_dump())
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def bulk_create_prompt_pairs(db: Session, image_prompts_in: List[ImagePromptCreate], video_prompts_in: List[VideoPromptCreate]) -> None:
    db_img_prompts = [ImagePrompt(**p.model_dump()) for p in image_prompts_in]
    db_vid_prompts = [VideoPrompt(**p.model_dump()) for p in video_prompts_in]
    
    db.add_all(db_img_prompts)
    db.add_all(db_vid_prompts)
    db.commit()

def list_project_prompt_pairs(db: Session, project_id: int) -> List[ScenePromptPairRead]:
    scenes = db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.scene_number.asc()).all()
    img_prompts = db.query(ImagePrompt).filter(ImagePrompt.project_id == project_id).all()
    vid_prompts = db.query(VideoPrompt).filter(VideoPrompt.project_id == project_id).all()

    img_map = {p.scene_id: p for p in img_prompts}
    vid_map = {p.scene_id: p for p in vid_prompts}

    pairs = []
    for scene in scenes:
        pairs.append(
            ScenePromptPairRead(
                scene_id=scene.id,
                scene_number=scene.scene_number,
                image_prompt=img_map.get(scene.id),
                video_prompt=vid_map.get(scene.id)
            )
        )
    return pairs

def get_image_prompt(db: Session, prompt_id: int) -> Optional[ImagePrompt]:
    return db.query(ImagePrompt).filter(ImagePrompt.id == prompt_id).first()

def get_video_prompt(db: Session, prompt_id: int) -> Optional[VideoPrompt]:
    return db.query(VideoPrompt).filter(VideoPrompt.id == prompt_id).first()

def update_image_prompt(db: Session, db_prompt: ImagePrompt, prompt_in: ImagePromptUpdate) -> ImagePrompt:
    update_data = prompt_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_prompt, key, value)
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def update_video_prompt(db: Session, db_prompt: VideoPrompt, prompt_in: VideoPromptUpdate) -> VideoPrompt:
    update_data = prompt_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_prompt, key, value)
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def delete_project_prompts_for_script(db: Session, script_id: int) -> None:
    db.query(ImagePrompt).filter(ImagePrompt.script_id == script_id).delete()
    db.query(VideoPrompt).filter(VideoPrompt.script_id == script_id).delete()
    db.commit()

def approve_project_prompts(db: Session, project_id: int, script_id: int) -> bool:
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        return False
        
    img_prompts = db.query(ImagePrompt).filter(ImagePrompt.script_id == script_id).all()
    vid_prompts = db.query(VideoPrompt).filter(VideoPrompt.script_id == script_id).all()
    
    if not img_prompts and not vid_prompts:
        return False

    for p in img_prompts:
        p.status = "APPROVED"
        db.add(p)
        
    for p in vid_prompts:
        p.status = "APPROVED"
        db.add(p)
        
    # Skip IMAGE_PROMPTS_READY and go straight to VIDEO_PROMPTS_READY as required by MVP
    project.status = PipelineState.VIDEO_PROMPTS_READY.value
    db.add(project)
    
    db.commit()
    return True
