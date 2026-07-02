from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp_renders.sqlite"
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

def _create_approved_subtitles_plan():
    proj_res = client.post("/api/projects/", json={"title": "Render Test Proj", "topic": "Testing", "duration_target": 30})
    project_id = proj_res.json()["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    client.post(f"/api/projects/{project_id}/assets/approve")
    
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    client.post(f"/api/projects/{project_id}/subtitles/approve")
    
    return project_id

def test_generate_mock_render_after_subtitles_approved():
    project_id = _create_approved_subtitles_plan()
    
    res = client.post(f"/api/projects/{project_id}/renders/generate")
    assert res.status_code == 200
    render = res.json()
    assert render["output_url"] is not None
    assert render["status"] == "COMPLETED"
    assert render["is_active"] is True
    
    # Project status remains SUBTITLES_READY until render approval
    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "SUBTITLES_READY"

def test_render_generation_before_subtitles_ready_returns_400():
    proj_res = client.post("/api/projects/", json={"title": "Draft Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    res = client.post(f"/api/projects/{project_id}/renders/generate")
    assert res.status_code == 400
    assert "before subtitles are approved" in res.json()["detail"]

def test_generated_manifest_includes_all_components():
    project_id = _create_approved_subtitles_plan()
    res = client.post(f"/api/projects/{project_id}/renders/generate")
    render = res.json()
    
    import json
    manifest = json.loads(render["manifest_json"])
    assert "clips" in manifest
    assert "voiceover" in manifest
    assert "subtitles" in manifest
    assert "output_url" in manifest
    assert "duration_seconds" in manifest
    assert manifest["aspect_ratio"] == "9:16"
    
    # Check populated
    assert len(manifest["clips"]) > 0
    assert manifest["voiceover"]["file_url"] is not None
    assert len(manifest["subtitles"]) > 0

def test_generating_render_deactivates_old():
    project_id = _create_approved_subtitles_plan()
    
    res1 = client.post(f"/api/projects/{project_id}/renders/generate")
    r1_id = res1.json()["id"]
    
    res2 = client.post(f"/api/projects/{project_id}/renders/generate")
    r2_id = res2.json()["id"]
    
    all_renders = client.get(f"/api/projects/{project_id}/renders").json()
    r1 = next(r for r in all_renders if r["id"] == r1_id)
    r2 = next(r for r in all_renders if r["id"] == r2_id)
    
    assert r1["is_active"] is False
    assert r2["is_active"] is True

def test_get_active_render():
    project_id = _create_approved_subtitles_plan()
    gen_res = client.post(f"/api/projects/{project_id}/renders/generate")
    r_id = gen_res.json()["id"]
    
    res = client.get(f"/api/projects/{project_id}/renders/active")
    assert res.status_code == 200
    assert res.json()["id"] == r_id

def test_list_project_renders():
    project_id = _create_approved_subtitles_plan()
    client.post(f"/api/projects/{project_id}/renders/generate")
    client.post(f"/api/projects/{project_id}/renders/generate")
    
    res = client.get(f"/api/projects/{project_id}/renders")
    assert res.status_code == 200
    assert len(res.json()) == 2

def test_approve_render_updates_statuses():
    project_id = _create_approved_subtitles_plan()
    client.post(f"/api/projects/{project_id}/renders/generate")
    
    res = client.post(f"/api/projects/{project_id}/renders/approve")
    assert res.status_code == 200
    
    render = client.get(f"/api/projects/{project_id}/renders/active").json()
    assert render["status"] == "APPROVED"
    
    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "FINAL_RENDER_READY"

def test_missing_entities():
    assert client.post("/api/projects/999/renders/generate").status_code == 404
    assert client.get("/api/projects/999/renders/active").status_code == 404
    assert client.get("/api/projects/999/renders").status_code == 404
    assert client.post("/api/projects/999/renders/approve").status_code == 404
    
    # Project exists, but no active render to approve
    proj_res = client.post("/api/projects/", json={"title": "Draft Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    assert client.get(f"/api/projects/{project_id}/renders/active").status_code == 404
    assert client.post(f"/api/projects/{project_id}/renders/approve").status_code == 404
