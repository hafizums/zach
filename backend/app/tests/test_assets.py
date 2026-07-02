from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp_assets.sqlite"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def _create_approved_prompts_plan():
    proj_res = client.post("/api/projects/", json={"title": "Asset Test Proj", "topic": "Testing", "duration_target": 40})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    
    return project_id

def test_generate_images_with_approved_prompts():
    project_id = _create_approved_prompts_plan()
    
    res = client.post(f"/api/projects/{project_id}/assets/images/generate")
    assert res.status_code == 200
    assets = res.json()
    assert len(assets) == 8
    
    pair = assets[0]
    assert pair["image"] is not None
    assert pair["image"]["is_active"] is True
    assert "data:image/svg+xml" in pair["image"]["file_url"]
    assert pair["image"]["provider_job_id"] is not None
    
    # Project status should now be IMAGES_GENERATED
    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "IMAGES_GENERATED"

def test_generate_images_without_approved_prompts():
    proj_res = client.post("/api/projects/", json={"title": "No Prompts Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    
    res = client.post(f"/api/projects/{project_id}/assets/images/generate")
    assert res.status_code == 400
    assert "before prompts are approved" in res.json()["detail"]

def test_generate_clips_with_active_images():
    project_id = _create_approved_prompts_plan()
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    
    res = client.post(f"/api/projects/{project_id}/assets/clips/generate")
    assert res.status_code == 200
    assets = res.json()
    assert len(assets) == 8
    
    pair = assets[0]
    assert pair["clip"] is not None
    assert pair["clip"]["is_active"] is True
    assert "vid_mock" in pair["clip"]["file_url"]
    assert pair["clip"]["provider_job_id"] is not None

def test_generate_clips_without_images():
    project_id = _create_approved_prompts_plan()
    
    res = client.post(f"/api/projects/{project_id}/assets/clips/generate")
    assert res.status_code == 400
    assert "has no active image" in res.json()["detail"]

def test_retry_scene_image():
    project_id = _create_approved_prompts_plan()
    gen = client.post(f"/api/projects/{project_id}/assets/images/generate")
    scene_id = gen.json()[0]["scene_id"]
    
    old_img_id = gen.json()[0]["image"]["id"]
    
    res = client.post(f"/api/scenes/{scene_id}/assets/image/retry")
    assert res.status_code == 200
    
    new_img = res.json()["image"]
    assert new_img["id"] != old_img_id
    assert new_img["is_active"] is True
    
    # Verify the old image is no longer returned in list
    list_res = client.get(f"/api/projects/{project_id}/assets")
    pair = next((p for p in list_res.json() if p["scene_id"] == scene_id), None)
    assert pair["image"]["id"] == new_img["id"]

def test_retry_scene_clip():
    project_id = _create_approved_prompts_plan()
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    gen = client.post(f"/api/projects/{project_id}/assets/clips/generate")
    scene_id = gen.json()[0]["scene_id"]
    
    old_clip_id = gen.json()[0]["clip"]["id"]
    
    res = client.post(f"/api/scenes/{scene_id}/assets/clip/retry")
    assert res.status_code == 200
    
    new_clip = res.json()["clip"]
    assert new_clip["id"] != old_clip_id
    assert new_clip["is_active"] is True

def test_approve_assets():
    project_id = _create_approved_prompts_plan()
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    
    res_approve = client.post(f"/api/projects/{project_id}/assets/approve")
    assert res_approve.status_code == 200
    
    res_assets = client.get(f"/api/projects/{project_id}/assets")
    for pair in res_assets.json():
        assert pair["image"]["status"] == "APPROVED"
        assert pair["clip"]["status"] == "APPROVED"
        
    res_proj = client.get(f"/api/projects/{project_id}")
    assert res_proj.json()["status"] == "CLIPS_GENERATED"

def test_generate_images_with_no_approved_script():
    proj_res = client.post("/api/projects/", json={"title": "No Script Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    res = client.post(f"/api/projects/{project_id}/assets/images/generate")
    assert res.status_code == 400
    assert "No approved script found" in res.json()["detail"]

def test_generate_clips_with_no_approved_script():
    proj_res = client.post("/api/projects/", json={"title": "No Script Proj 2", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    res = client.post(f"/api/projects/{project_id}/assets/clips/generate")
    assert res.status_code == 400
    assert "No approved script found" in res.json()["detail"]

def _create_unapproved_prompts_plan():
    proj_res = client.post("/api/projects/", json={"title": "Unapproved Prompts Proj", "topic": "Testing", "duration_target": 40})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    
    client.post(f"/api/projects/{project_id}/prompts/generate")
    # intentionally NOT approving prompts
    
    # We also need to set the project status manually to VIDEO_PROMPTS_READY so the first check passes,
    # and it fails on the prompt iteration check. But wait, if prompts aren't approved, project status is SCENE_PLAN_READY.
    # The first guard for project.status will fail before prompt checks.
    # To test the prompt iteration check, we can just call retry endpoints directly.
    return project_id

def test_generate_images_refuses_draft_prompts():
    project_id = _create_unapproved_prompts_plan()
    
    # Try to retry image for the first scene
    res_prompts = client.get(f"/api/projects/{project_id}/prompts")
    scene_id = res_prompts.json()[0]["scene_id"]
    
    res = client.post(f"/api/scenes/{scene_id}/assets/image/retry")
    assert res.status_code == 400
    assert "must be APPROVED" in res.json()["detail"]

def test_generate_clips_refuses_draft_prompts():
    project_id = _create_unapproved_prompts_plan()
    
    res_prompts = client.get(f"/api/projects/{project_id}/prompts")
    scene_id = res_prompts.json()[0]["scene_id"]
    
    res_clip = client.post(f"/api/scenes/{scene_id}/assets/clip/retry")
    assert res_clip.status_code == 400
    assert "must be APPROVED" in res_clip.json()["detail"]

def test_missing_entities():
    assert client.post("/api/projects/999/assets/images/generate").status_code == 404
    assert client.post("/api/projects/999/assets/clips/generate").status_code == 404
    assert client.post("/api/scenes/999/assets/image/retry").status_code == 404
    assert client.post("/api/scenes/999/assets/clip/retry").status_code == 404
    assert client.get("/api/projects/999/assets").status_code == 404
    assert client.get("/api/scenes/999/assets").status_code == 404
    assert client.post("/api/projects/999/assets/approve").status_code == 404
