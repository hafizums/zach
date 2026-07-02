import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # We must explicitly seed the memory DB since the lifespan event applies to the real DB
    db = TestingSessionLocal()
    from app.services.model_catalog_service import seed_default_mock_models
    seed_default_mock_models(db)
    db.close()
    
    yield

    app.dependency_overrides.clear()
def disable_model_helper(model_name: str):
    models = client.get("/api/providers/models").json()
    model_id = next(m["id"] for m in models if m["model_name"] == model_name)
    client.post(f"/api/providers/models/{model_id}/disable")

def test_disable_mock_llm_blocks_script_generation():
    disable_model_helper("mock-llm")
    
    # Create project
    proj_res = client.post("/api/projects/", json={
        "title": "Blocker Test Proj",
        "topic": "Testing blockers",
        "language": "en"
    })
    proj_id = proj_res.json()["id"]
    
    # Generate script should fail with 400
    res = client.post(f"/api/projects/{proj_id}/scripts/generate")
    assert res.status_code == 400
    assert "mock-llm" in res.json()["detail"]

def test_disable_mock_image_blocks_image_generation():
    # Setup up to prompts
    proj_res = client.post("/api/projects/", json={"title": "Test", "topic": "Test", "language": "en"})
    proj_id = proj_res.json()["id"]
    client.post(f"/api/projects/{proj_id}/scripts/generate")
    script_id = client.get(f"/api/projects/{proj_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    client.post(f"/api/projects/{proj_id}/scenes/generate")
    client.post(f"/api/projects/{proj_id}/scenes/approve")
    client.post(f"/api/projects/{proj_id}/prompts/generate")
    client.post(f"/api/projects/{proj_id}/prompts/approve")
    
    # Disable mock-image
    disable_model_helper("mock-image")
    
    # Generate assets should fail
    res = client.post(f"/api/projects/{proj_id}/assets/images/generate")
    assert res.status_code == 400
    assert "mock-image" in res.json()["detail"]

def test_disable_mock_video_blocks_clip_generation():
    # Setup up to prompts
    proj_res = client.post("/api/projects/", json={"title": "Test", "topic": "Test", "language": "en"})
    proj_id = proj_res.json()["id"]
    client.post(f"/api/projects/{proj_id}/scripts/generate")
    script_id = client.get(f"/api/projects/{proj_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    client.post(f"/api/projects/{proj_id}/scenes/generate")
    client.post(f"/api/projects/{proj_id}/scenes/approve")
    client.post(f"/api/projects/{proj_id}/prompts/generate")
    client.post(f"/api/projects/{proj_id}/prompts/approve")
    
    # Generate images first (needs mock-image enabled)
    client.post(f"/api/projects/{proj_id}/assets/images/generate")
    
    # Disable mock-video
    disable_model_helper("mock-video")
    
    # Generate clips should fail
    res = client.post(f"/api/projects/{proj_id}/assets/clips/generate")
    assert res.status_code == 400
    assert "mock-video" in res.json()["detail"]

def test_disable_mock_audio_blocks_voiceover_generation():
    # Setup up to asset approval
    proj_res = client.post("/api/projects/", json={"title": "Test", "topic": "Test", "language": "en"})
    proj_id = proj_res.json()["id"]
    client.post(f"/api/projects/{proj_id}/scripts/generate")
    script_id = client.get(f"/api/projects/{proj_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    client.post(f"/api/projects/{proj_id}/scenes/generate")
    client.post(f"/api/projects/{proj_id}/scenes/approve")
    client.post(f"/api/projects/{proj_id}/prompts/generate")
    client.post(f"/api/projects/{proj_id}/prompts/approve")
    client.post(f"/api/projects/{proj_id}/assets/images/generate")
    client.post(f"/api/projects/{proj_id}/assets/clips/generate")
    client.post(f"/api/projects/{proj_id}/assets/approve")
    
    # Disable mock-audio
    disable_model_helper("mock-audio")
    
    # Generate audio should fail
    res = client.post(f"/api/projects/{proj_id}/audio/voiceover/generate")
    assert res.status_code == 400
    assert "mock-audio" in res.json()["detail"]

def test_disable_mock_render_blocks_final_render():
    # Setup up to subtitles approval
    proj_res = client.post("/api/projects/", json={"title": "Test", "topic": "Test", "language": "en"})
    proj_id = proj_res.json()["id"]
    client.post(f"/api/projects/{proj_id}/scripts/generate")
    script_id = client.get(f"/api/projects/{proj_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    client.post(f"/api/projects/{proj_id}/scenes/generate")
    client.post(f"/api/projects/{proj_id}/scenes/approve")
    client.post(f"/api/projects/{proj_id}/prompts/generate")
    client.post(f"/api/projects/{proj_id}/prompts/approve")
    client.post(f"/api/projects/{proj_id}/assets/images/generate")
    client.post(f"/api/projects/{proj_id}/assets/clips/generate")
    client.post(f"/api/projects/{proj_id}/assets/approve")
    
    audio_res = client.post(f"/api/projects/{proj_id}/audio/voiceover/generate")
    voiceover_id = audio_res.json()["id"]
    client.post(f"/api/projects/{proj_id}/subtitles/generate")
    client.post(f"/api/projects/{proj_id}/subtitles/approve")
    
    # Disable mock-render
    disable_model_helper("mock-render")
    
    # Generate render should fail
    res = client.post(f"/api/projects/{proj_id}/renders/generate")
    assert res.status_code == 400
    assert "mock-render" in res.json()["detail"]

def test_preflight_modality_mismatch():
    payload = {
        "provider_name": "mock",
        "model_name": "mock-image",
        "modality": "video"
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "not found in catalog" in data["message"]
