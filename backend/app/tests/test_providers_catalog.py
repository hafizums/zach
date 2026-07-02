import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.provider import ProviderModel, ProviderRunLog
from app.schemas.provider_schema import ProviderPreflightRequest
from app.services.provider_run_service import redact_payload

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
        from app.services.model_catalog_service import seed_default_mock_models
        from app.models.provider import ProviderModel
        count = db.query(ProviderModel).count()
        if count == 0:
            seed_default_mock_models(db)
        yield db
    finally:
        db.close()



client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
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
def test_default_mock_models_seeded():
    response = client.get("/api/providers/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 9
    assert any(m["model_name"] == "mock-llm" for m in models)
    assert any(m["model_name"] == "mock-image" for m in models)

def test_list_enabled_provider_models():
    response = client.get("/api/providers/models/enabled")
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 6
    assert all(m["is_enabled"] is True for m in models)

def test_list_models_by_modality():
    response = client.get("/api/providers/models/modality/image")
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 1
    assert models[0]["model_name"] == "mock-image"

def test_create_provider_model():
    payload = {
        "provider_name": "custom",
        "model_name": "custom-v1",
        "display_name": "Custom Gen",
        "modality": "image",
        "cost_hint": "expensive"
    }
    response = client.post("/api/providers/models", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["provider_name"] == "custom"
    assert data["model_name"] == "custom-v1"

def test_update_provider_model():
    response = client.get("/api/providers/models")
    model_id = response.json()[0]["id"]
    
    update_payload = {"display_name": "Updated Mock"}
    patch_response = client.patch(f"/api/providers/models/{model_id}", json=update_payload)
    assert patch_response.status_code == 200
    assert patch_response.json()["display_name"] == "Updated Mock"

def test_disable_enable_provider_model():
    # Find mock-llm
    models = client.get("/api/providers/models").json()
    llm_id = next(m["id"] for m in models if m["model_name"] == "mock-llm")
    
    # Disable
    res_disable = client.post(f"/api/providers/models/{llm_id}/disable")
    assert res_disable.status_code == 200
    assert res_disable.json()["is_enabled"] is False
    
    # Verify not in enabled list
    enabled = client.get("/api/providers/models/enabled").json()
    assert not any(m["id"] == llm_id for m in enabled)
    
    # Enable
    res_enable = client.post(f"/api/providers/models/{llm_id}/enable")
    assert res_enable.status_code == 200
    assert res_enable.json()["is_enabled"] is True

def test_preflight_passes_for_enabled_mock_image():
    payload = {
        "provider_name": "mock",
        "model_name": "mock-image",
        "modality": "image"
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    assert res.json()["ok"] is True

def test_preflight_fails_for_disabled_model():
    models = client.get("/api/providers/models").json()
    img_id = next(m["id"] for m in models if m["model_name"] == "mock-image")
    client.post(f"/api/providers/models/{img_id}/disable")
    
    payload = {
        "provider_name": "mock",
        "model_name": "mock-image",
        "modality": "image"
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "disabled" in data["message"]

def test_preflight_fails_for_unknown_provider():
    payload = {
        "provider_name": "unknown",
        "model_name": "unknown-model",
        "modality": "image"
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    assert res.json()["ok"] is False
    assert "not found in catalog" in res.json()["message"]

def test_redact_payload():
    payload = {
        "safe_key": "safe_value",
        "openai_api_key": "sk-12345",
        "secret_token": "abc",
        "nested": {
            "Authorization": "Bearer 123",
            "password123": "xyz",
            "normal": "value"
        },
        "array_of_credentials": [{"token": "123"}, {"normal": "val"}]
    }
    
    redacted = redact_payload(payload)
    
    assert redacted["safe_key"] == "safe_value"
    assert redacted["openai_api_key"] == "[REDACTED]"
    assert redacted["secret_token"] == "[REDACTED]"
    assert redacted["nested"]["Authorization"] == "[REDACTED]"
    assert redacted["nested"]["password123"] == "[REDACTED]"
    assert redacted["nested"]["normal"] == "value"
    assert redacted["array_of_credentials"][0]["token"] == "[REDACTED]"
    assert redacted["array_of_credentials"][1]["normal"] == "val"
    
def test_redact_payload_json_string():
    raw = '{"api_key": "supersecret", "data": "clean"}'
    redacted = redact_payload(raw)
    import json
    parsed = json.loads(redacted)
    assert parsed["api_key"] == "[REDACTED]"
    assert parsed["data"] == "clean"

# Simple workflow test to trigger logging
def test_script_generation_logs_run():
    # Create project
    proj_res = client.post("/api/projects/", json={
        "title": "Test Proj",
        "topic": "Testing",
        "language": "en"
    })
    proj_id = proj_res.json()["id"]
    
    # Generate Script
    script_res = client.post(f"/api/projects/{proj_id}/scripts/generate")
    assert script_res.status_code == 200
    
    # Check logs
    logs_res = client.get(f"/api/projects/{proj_id}/provider-runs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) == 1
    assert logs[0]["operation"] == "script_generation"
    assert logs[0]["provider_name"] == "mock"
    assert logs[0]["modality"] == "llm"
    assert "Testing" in logs[0]["request_json"]

def test_list_recent_run_logs():
    # Should be at least one from the previous test if it was same DB, but this runs in isolation due to autouse=True
    # Generate Script
    proj_res = client.post("/api/projects/", json={"title": "Test Proj", "topic": "Testing", "language": "en"})
    client.post(f"/api/projects/{proj_res.json()['id']}/scripts/generate")
    
    logs_res = client.get("/api/providers/runs/recent")
    assert logs_res.status_code == 200
    assert len(logs_res.json()) >= 1

def test_preflight_passes_for_enabled_mock_render():
    payload = {
        "provider_name": "mock",
        "model_name": "mock-render",
        "modality": "render"
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    assert res.json()["ok"] is True

def test_preflight_fails_for_render_missing_adapter():
    payload = {
        "provider_name": "custom",
        "model_name": "custom-render",
        "display_name": "Custom Render",
        "modality": "render",
        "cost_hint": "cheap"
    }
    # Create the model in the catalog
    create_res = client.post("/api/providers/models", json=payload)
    assert create_res.status_code == 200
    
    # Enable the model
    model_id = create_res.json()["id"]
    client.post(f"/api/providers/models/{model_id}/enable")
    
    # Preflight should fail because no 'custom' render adapter exists in registry
    preflight_payload = {
        "provider_name": "custom",
        "model_name": "custom-render",
        "modality": "render"
    }
    res = client.post("/api/providers/preflight", json=preflight_payload)
    assert res.status_code == 200
    
    data = res.json()
    assert data["ok"] is False
    assert "registered adapter" in data["message"].lower()
