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
def test_create_project():
    response = client.post(
        "/api/projects/",
        json={"title": "Test Video", "topic": "Testing"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Video"
    assert data["topic"] == "Testing"
    assert "id" in data

def test_list_projects():
    client.post("/api/projects/", json={"title": "Test 1", "topic": "Topic 1"})
    client.post("/api/projects/", json={"title": "Test 2", "topic": "Topic 2"})
    
    response = client.get("/api/projects/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

def test_get_project():
    create_res = client.post("/api/projects/", json={"title": "Get Me", "topic": "Topic Get"})
    project_id = create_res.json()["id"]

    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["title"] == "Get Me"

def test_get_project_not_found():
    response = client.get("/api/projects/9999")
    assert response.status_code == 404

def test_update_project():
    create_res = client.post("/api/projects/", json={"title": "Old Title", "topic": "Old Topic"})
    project_id = create_res.json()["id"]

    response = client.patch(f"/api/projects/{project_id}", json={"title": "New Title"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["topic"] == "Old Topic"

def test_update_project_not_found():
    response = client.patch("/api/projects/9999", json={"title": "New Title"})
    assert response.status_code == 404

def test_delete_project():
    create_res = client.post("/api/projects/", json={"title": "Delete Me", "topic": "Topic Delete"})
    project_id = create_res.json()["id"]

    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 204

    get_response = client.get(f"/api/projects/{project_id}")
    assert get_response.status_code == 404

def test_delete_project_not_found():
    response = client.delete("/api/projects/9999")
    assert response.status_code == 404
