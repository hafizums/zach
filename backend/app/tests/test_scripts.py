from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.main import app
from app.core.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.sqlite"
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

def _create_project():
    res = client.post("/api/projects/", json={"title": "Test Proj", "topic": "Testing"})
    return res.json()

def test_generate_first_script():
    project = _create_project()
    project_id = project["id"]
    
    res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    assert res.status_code == 200
    script = res.json()
    assert script["version"] == 1
    assert script["project_id"] == project_id
    assert script["status"] == "DRAFT"
    assert "mock" in script["hook"].lower()

def test_regenerate_script():
    project = _create_project()
    project_id = project["id"]
    
    res1 = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    res2 = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    
    assert res1.json()["version"] == 1
    assert res2.json()["version"] == 2

def test_list_scripts_and_latest():
    project = _create_project()
    project_id = project["id"]
    
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    
    res_list = client.get(f"/api/projects/{project_id}/scripts")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 2
    
    res_latest = client.get(f"/api/projects/{project_id}/scripts/latest")
    assert res_latest.status_code == 200
    assert res_latest.json()["version"] == 2

def test_update_script():
    project = _create_project()
    project_id = project["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    
    res_update = client.patch(f"/api/scripts/{script_id}", json={"script_text": "Updated body"})
    assert res_update.status_code == 200
    assert res_update.json()["script_text"] == "Updated body"

def test_approve_script():
    project = _create_project()
    project_id = project["id"]
    
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    
    res_approve = client.post(f"/api/scripts/{script_id}/approve")
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "APPROVED"
    
    res_proj = client.get(f"/api/projects/{project_id}")
    assert res_proj.json()["status"] == "SCRIPT_READY"

def test_missing_entities():
    assert client.post("/api/projects/999/scripts/generate", json={}).status_code == 404
    assert client.get("/api/scripts/999").status_code == 404
    assert client.get("/api/projects/999/scripts/latest").status_code == 404
    assert client.patch("/api/scripts/999", json={}).status_code == 404
    assert client.post("/api/scripts/999/approve").status_code == 404
