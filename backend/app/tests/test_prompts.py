from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp_prompts.sqlite"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


client = TestClient(app)

@pytest.fixture(autouse=True)
def run_around_tests():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    from app.services.model_catalog_service import seed_default_mock_models
    seed_default_mock_models(db)
    db.close()
    yield

    app.dependency_overrides.clear()
def _create_approved_scene_plan():
    proj_res = client.post("/api/projects/", json={"title": "Prompt Test Proj", "topic": "Testing", "duration_target": 40})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    
    return project_id, script_id

def test_generate_prompts_with_approved_scene_plan():
    project_id, _ = _create_approved_scene_plan()
    
    res = client.post(f"/api/projects/{project_id}/prompts/generate")
    assert res.status_code == 200
    prompt_pairs = res.json()
    assert len(prompt_pairs) == 8
    
    pair = prompt_pairs[0]
    assert pair["image_prompt"] is not None
    assert pair["video_prompt"] is not None
    
    # Check image prompt
    img = pair["image_prompt"]
    assert img["status"] == "DRAFT"
    assert "9:16" in img["prompt_text"]
    assert "watermark" in img["negative_prompt"]
    
    # Check video prompt
    vid = pair["video_prompt"]
    assert vid["status"] == "DRAFT"
    assert "animate this reference image" in vid["prompt_text"]
    assert "watermark" in vid["negative_prompt"]

def test_generate_prompts_without_approved_scene_plan():
    proj_res = client.post("/api/projects/", json={"title": "No Scenes Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    # Approve script but no scenes
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    
    res = client.post(f"/api/projects/{project_id}/prompts/generate")
    assert res.status_code == 400
    assert "APPROVED scene plan" in res.json()["detail"]

def test_list_project_prompts():
    project_id, _ = _create_approved_scene_plan()
    client.post(f"/api/projects/{project_id}/prompts/generate")
    
    res = client.get(f"/api/projects/{project_id}/prompts")
    assert res.status_code == 200
    assert len(res.json()) == 8

def test_update_prompts():
    project_id, _ = _create_approved_scene_plan()
    gen_res = client.post(f"/api/projects/{project_id}/prompts/generate")
    pair = gen_res.json()[0]
    
    img_id = pair["image_prompt"]["id"]
    vid_id = pair["video_prompt"]["id"]
    
    res_img = client.patch(f"/api/image-prompts/{img_id}", json={"prompt_text": "Updated img"})
    assert res_img.status_code == 200
    assert res_img.json()["prompt_text"] == "Updated img"
    
    res_vid = client.patch(f"/api/video-prompts/{vid_id}", json={"prompt_text": "Updated vid"})
    assert res_vid.status_code == 200
    assert res_vid.json()["prompt_text"] == "Updated vid"

def test_approve_prompts():
    project_id, _ = _create_approved_scene_plan()
    client.post(f"/api/projects/{project_id}/prompts/generate")
    
    res_approve = client.post(f"/api/projects/{project_id}/prompts/approve")
    assert res_approve.status_code == 200
    
    # Verify prompts are approved
    res_prompts = client.get(f"/api/projects/{project_id}/prompts")
    for pair in res_prompts.json():
        assert pair["image_prompt"]["status"] == "APPROVED"
        assert pair["video_prompt"]["status"] == "APPROVED"
        
    # Verify project status
    res_proj = client.get(f"/api/projects/{project_id}")
    assert res_proj.json()["status"] == "VIDEO_PROMPTS_READY"

def test_generate_prompts_regeneration_replaces_old_prompts():
    project_id, _ = _create_approved_scene_plan()
    
    # First generation
    gen1 = client.post(f"/api/projects/{project_id}/prompts/generate")
    pairs1 = gen1.json()
    assert len(pairs1) == 8
    first_img_ids = {p["image_prompt"]["id"] for p in pairs1}
    first_vid_ids = {p["video_prompt"]["id"] for p in pairs1}
    
    # Second generation
    gen2 = client.post(f"/api/projects/{project_id}/prompts/generate")
    pairs2 = gen2.json()
    assert len(pairs2) == 8
    
    # Ensure project prompt pair count is still 8
    res = client.get(f"/api/projects/{project_id}/prompts")
    assert len(res.json()) == 8

def test_get_scene_prompts_existing():
    project_id, _ = _create_approved_scene_plan()
    gen = client.post(f"/api/projects/{project_id}/prompts/generate")
    pairs = gen.json()
    scene_id = pairs[0]["scene_id"]
    
    res = client.get(f"/api/scenes/{scene_id}/prompts")
    assert res.status_code == 200
    data = res.json()
    assert data["scene_id"] == scene_id
    assert data["image_prompt"] is not None
    assert data["video_prompt"] is not None

def test_get_scene_prompts_missing():
    res = client.get("/api/scenes/999/prompts")
    assert res.status_code == 404

def test_missing_entities():
    assert client.post("/api/projects/999/prompts/generate").status_code == 404
    assert client.get("/api/projects/999/prompts").status_code == 404
    assert client.patch("/api/image-prompts/999", json={}).status_code == 404
    assert client.patch("/api/video-prompts/999", json={}).status_code == 404
    assert client.post("/api/projects/999/prompts/approve").status_code == 404
    assert client.get("/api/scenes/999/prompts").status_code == 404
