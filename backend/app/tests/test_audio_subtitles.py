from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp_audio.sqlite"
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

def _create_approved_assets_plan():
    proj_res = client.post("/api/projects/", json={"title": "Audio Test Proj", "topic": "Testing", "duration_target": 30})
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
    
    return project_id

def test_generate_voiceover_after_assets_approved():
    project_id = _create_approved_assets_plan()
    
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    assert res.status_code == 200
    vo = res.json()
    assert vo["provider_job_id"] is not None
    assert vo["duration_seconds"] == 30
    assert vo["is_active"] is True
    
    # Project status should now be VOICEOVER_READY
    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "VOICEOVER_READY"

def test_generate_voiceover_before_assets_approved_returns_400():
    proj_res = client.post("/api/projects/", json={"title": "Draft Proj", "topic": "Testing"})
    project_id = proj_res.json()["id"]
    
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    assert res.status_code == 400
    assert "before assets are approved" in res.json()["detail"]

def test_generating_voiceover_deactivates_old():
    project_id = _create_approved_assets_plan()
    
    res1 = client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    vo1_id = res1.json()["id"]
    
    res2 = client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    vo2_id = res2.json()["id"]
    
    assert vo1_id != vo2_id
    
    all_vo = client.get(f"/api/projects/{project_id}/audio/voiceovers").json()
    vo1 = next(v for v in all_vo if v["id"] == vo1_id)
    vo2 = next(v for v in all_vo if v["id"] == vo2_id)
    
    assert vo1["is_active"] is False
    assert vo2["is_active"] is True

def test_generate_subtitle_segments_from_active_voiceover():
    project_id = _create_approved_assets_plan()
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    
    res = client.post(f"/api/projects/{project_id}/subtitles/generate")
    assert res.status_code == 200
    subtitles = res.json()
    
    # 8 scenes by default in the mock logic -> 8 subtitle segments
    assert len(subtitles) > 0
    assert subtitles[0]["status"] == "DRAFT"
    
def test_subtitle_generation_before_voiceover_returns_400():
    project_id = _create_approved_assets_plan()
    
    res = client.post(f"/api/projects/{project_id}/subtitles/generate")
    assert res.status_code == 400
    assert "before voiceover exists" in res.json()["detail"]

def test_list_project_subtitles():
    project_id = _create_approved_assets_plan()
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    
    res = client.get(f"/api/projects/{project_id}/subtitles")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_update_subtitle_segment():
    project_id = _create_approved_assets_plan()
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    gen_res = client.post(f"/api/projects/{project_id}/subtitles/generate")
    sub_id = gen_res.json()[0]["id"]
    
    update_res = client.patch(f"/api/subtitles/{sub_id}", json={"text": "Updated Subtitle!"})
    assert update_res.status_code == 200
    assert update_res.json()["text"] == "Updated Subtitle!"

def test_approve_subtitles():
    project_id = _create_approved_assets_plan()
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    
    res_approve = client.post(f"/api/projects/{project_id}/subtitles/approve")
    assert res_approve.status_code == 200
    
    proj_res = client.get(f"/api/projects/{project_id}")
    assert proj_res.json()["status"] == "SUBTITLES_READY"
    
    vo = client.get(f"/api/projects/{project_id}/audio/voiceover").json()
    assert vo["status"] == "APPROVED"
    
    subs = client.get(f"/api/projects/{project_id}/subtitles").json()
    assert all(s["status"] == "APPROVED" for s in subs)

def test_missing_entities():
    assert client.post("/api/projects/999/audio/voiceover/generate").status_code == 404
    assert client.get("/api/projects/999/audio/voiceover").status_code == 404
    assert client.get("/api/projects/999/audio/voiceovers").status_code == 404
    assert client.post("/api/projects/999/subtitles/generate").status_code == 404
    assert client.get("/api/projects/999/subtitles").status_code == 404
    assert client.get("/api/voiceovers/999/subtitles").status_code == 200 # Returns empty list
    assert client.patch("/api/subtitles/999", json={"text": "hi"}).status_code == 404
    assert client.post("/api/projects/999/subtitles/approve").status_code == 404
