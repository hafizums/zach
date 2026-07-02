from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.scene import Scene
from app.models.video_project import VideoProject
from app.schemas.scene_schema import SceneCreate, SceneUpdate
from app.pipeline.pipeline_states import PipelineState

def create_scene(db: Session, scene_in: SceneCreate) -> Scene:
    db_scene = Scene(**scene_in.model_dump())
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def bulk_create_scenes(db: Session, scenes_in: List[SceneCreate]) -> List[Scene]:
    db_scenes = [Scene(**s.model_dump()) for s in scenes_in]
    db.add_all(db_scenes)
    db.commit()
    for s in db_scenes:
        db.refresh(s)
    return db_scenes

def list_project_scenes(db: Session, project_id: int) -> List[Scene]:
    return db.query(Scene).filter(Scene.project_id == project_id).order_by(Scene.scene_number.asc()).all()

def list_script_scenes(db: Session, script_id: int) -> List[Scene]:
    return db.query(Scene).filter(Scene.script_id == script_id).order_by(Scene.scene_number.asc()).all()

def get_scene(db: Session, scene_id: int) -> Optional[Scene]:
    return db.query(Scene).filter(Scene.id == scene_id).first()

def update_scene(db: Session, db_scene: Scene, scene_in: SceneUpdate) -> Scene:
    update_data = scene_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_scene, key, value)
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene

def delete_project_scenes_for_script(db: Session, script_id: int) -> bool:
    db.query(Scene).filter(Scene.script_id == script_id).delete()
    db.commit()
    return True

def approve_project_scene_plan(db: Session, project_id: int, script_id: int) -> bool:
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        return False
        
    scenes = list_script_scenes(db, script_id)
    if not scenes:
        return False

    for scene in scenes:
        scene.status = "APPROVED"
        db.add(scene)
        
    project.status = PipelineState.SCENE_PLAN_READY.value
    db.add(project)
    
    db.commit()
    return True
