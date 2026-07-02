from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp_scenes.sqlite"
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

def _create_project_and_approved_script():
    proj_res = client.post("/api/projects/", json={"title": "Scene Test Proj", "topic": "Testing", "duration_target": 40})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    
    client.post(f"/api/scripts/{script_id}/approve")
    
    return project_id, script_id

def test_generate_scenes_with_approved_script():
    project_id, script_id = _create_project_and_approved_script()
    
    res = client.post(f"/api/projects/{project_id}/scenes/generate")
    assert res.status_code == 200
    scenes = res.json()
    assert len(scenes) == 8
    
    # Check scene properties
    assert scenes[0]["scene_number"] == 1
    assert scenes[0]["status"] == "DRAFT"
    assert "duration_seconds" in scenes[0]
    assert scenes[0]["duration_seconds"] > 0
    assert "narration_text" in scenes[0]
    assert "visual_summary" in scenes[0]

def test_generate_scenes_without_approved_script():
    proj_res = client.post("/api/projects/", json={"title": "No Script Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    res = client.post(f"/api/projects/{project_id}/scenes/generate")
    assert res.status_code == 400
    assert "APPROVED script" in res.json()["detail"]

def test_list_scenes():
    project_id, script_id = _create_project_and_approved_script()
    client.post(f"/api/projects/{project_id}/scenes/generate")
    
    res_proj = client.get(f"/api/projects/{project_id}/scenes")
    assert res_proj.status_code == 200
    assert len(res_proj.json()) == 8
    
    res_script = client.get(f"/api/scripts/{script_id}/scenes")
    assert res_script.status_code == 200
    assert len(res_script.json()) == 8

def test_update_scene():
    project_id, script_id = _create_project_and_approved_script()
    gen_res = client.post(f"/api/projects/{project_id}/scenes/generate")
    scene_id = gen_res.json()[0]["id"]
    
    res_patch = client.patch(f"/api/scenes/{scene_id}", json={"visual_summary": "Updated visual"})
    assert res_patch.status_code == 200
    assert res_patch.json()["visual_summary"] == "Updated visual"

def test_approve_scene_plan():
    project_id, script_id = _create_project_and_approved_script()
    client.post(f"/api/projects/{project_id}/scenes/generate")
    
    res_approve = client.post(f"/api/projects/{project_id}/scenes/approve")
    assert res_approve.status_code == 200
    
    # Verify scenes are approved
    res_scenes = client.get(f"/api/projects/{project_id}/scenes")
    for scene in res_scenes.json():
        assert scene["status"] == "APPROVED"
        
    # Verify project status
    res_proj = client.get(f"/api/projects/{project_id}")
    assert res_proj.json()["status"] == "SCENE_PLAN_READY"

def test_missing_entities():
    assert client.post("/api/projects/999/scenes/generate").status_code == 404
    assert client.get("/api/projects/999/scenes").status_code == 404
    assert client.get("/api/scripts/999/scenes").status_code == 404
    assert client.get("/api/scenes/999").status_code == 404
    assert client.patch("/api/scenes/999", json={}).status_code == 404
    assert client.post("/api/projects/999/scenes/approve").status_code == 404
