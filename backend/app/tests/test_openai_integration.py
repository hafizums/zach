"""
test_openai_integration.py — 15 tests for Phase 10 gate review

All tests use mock/stub; no real OpenAI API calls are made.
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

# ---------------------------------------------------------------------------
# Isolated in-memory DB for this file
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    app.dependency_overrides[get_db] = _override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    from app.services.model_catalog_service import seed_default_mock_models
    seed_default_mock_models(db)
    db.close()
    yield
    app.dependency_overrides.clear()


def _override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_project():
    r = client.post("/api/projects/", json={"title": "OAI Test", "topic": "Science", "duration_target": 60})
    assert r.status_code == 200
    return r.json()["id"]


def _get_openai_llm_model_id():
    models = client.get("/api/providers/models").json()
    m = next((m for m in models if m["provider_name"] == "openai" and m["modality"] == "llm"), None)
    assert m is not None, "OpenAI LLM model not in catalog"
    return m["id"]


def _enable_openai_llm():
    mid = _get_openai_llm_model_id()
    client.post(f"/api/providers/models/{mid}/enable")


def _disable_openai_llm():
    mid = _get_openai_llm_model_id()
    client.post(f"/api/providers/models/{mid}/disable")


def _mock_openai_responses_create(text: str) -> MagicMock:
    """Return a mock that behaves like an OpenAI Responses API response object."""
    resp = MagicMock()
    resp.id = "resp_test_mocked"
    resp.output_text = text
    return resp


def _create_approved_script(project_id: int) -> int:
    r = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    assert r.status_code == 200
    sid = r.json()["id"]
    client.post(f"/api/scripts/{sid}/approve")
    return sid


def _create_approved_scenes(project_id: int):
    client.post(f"/api/projects/{project_id}/scenes/generate", json={})
    client.post(f"/api/projects/{project_id}/scenes/approve")


def _create_approved_prompts(project_id: int):
    client.post(f"/api/projects/{project_id}/prompts/generate", json={})
    client.post(f"/api/projects/{project_id}/prompts/approve")


def _create_approved_assets(project_id: int):
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    client.post(f"/api/projects/{project_id}/assets/approve")


# ---------------------------------------------------------------------------
# Test 1 — OpenAI model is seeded disabled by default
# ---------------------------------------------------------------------------

def test_openai_model_seeded_disabled():
    models = client.get("/api/providers/models").json()
    openai_m = next((m for m in models if m["provider_name"] == "openai" and m["modality"] == "llm"), None)
    assert openai_m is not None
    assert openai_m["is_enabled"] is False


# ---------------------------------------------------------------------------
# Test 2 — Preflight fails when OpenAI model is disabled
# ---------------------------------------------------------------------------

def test_openai_preflight_fails_when_disabled():
    # Ensure disabled (it already is by default, but be explicit)
    _disable_openai_llm()

    res = client.post("/api/providers/preflight", json={
        "provider_name": "openai",
        "model_name": "gpt-4o-mini",
        "modality": "llm",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "disabled" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 3 — Preflight fails when enabled but OPENAI_API_KEY is missing
# ---------------------------------------------------------------------------

def test_openai_preflight_fails_when_key_missing():
    _enable_openai_llm()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENAI_API_KEY", None)
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini",
            "modality": "llm",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "OPENAI_API_KEY" in data["message"]


# ---------------------------------------------------------------------------
# Test 4 — Preflight passes when enabled and key is present (mocked env)
# ---------------------------------------------------------------------------

def test_openai_preflight_passes_when_enabled_and_key_present():
    _enable_openai_llm()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini",
            "modality": "llm",
        })
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ---------------------------------------------------------------------------
# Test 5 — Script generation defaults to mock when no provider is specified
# ---------------------------------------------------------------------------

def test_script_generation_defaults_to_mock():
    pid = _create_project()
    r = client.post(f"/api/projects/{pid}/scripts/generate", json={})
    assert r.status_code == 200
    script = r.json()
    assert "mock" in script["hook"].lower()

    logs = client.get(f"/api/projects/{pid}/provider-runs").json()
    assert any(lg["provider_name"] == "mock" for lg in logs)


# ---------------------------------------------------------------------------
# Test 6 — Script generation with OpenAI disabled returns 400
# ---------------------------------------------------------------------------

def test_script_generation_openai_disabled_returns_400():
    _disable_openai_llm()  # already disabled, but explicit
    pid = _create_project()
    r = client.post(f"/api/projects/{pid}/scripts/generate", json={
        "provider_name": "openai",
        "model_name": "gpt-4o-mini",
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Test 7 — Script generation with OpenAI selected and mocked provider creates script
# ---------------------------------------------------------------------------

def test_script_generation_openai_mocked_creates_script():
    _enable_openai_llm()
    pid = _create_project()

    mock_resp_json = json.dumps({
        "hook": "Did you know black holes sing?",
        "script": "Black holes produce gravitational waves that propagate across spacetime.",
        "word_count": 12,
        "estimated_duration_seconds": 60,
        "payoff": "The universe is a symphony.",
    })

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=json.loads(mock_resp_json),
        ):
            r = client.post(f"/api/projects/{pid}/scripts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 200
    script = r.json()
    assert "black holes" in script["hook"].lower() or "black holes" in script["script"].lower()


# ---------------------------------------------------------------------------
# Test 8 — Scene generation with OpenAI mocked creates scenes
# ---------------------------------------------------------------------------

def test_scene_generation_openai_mocked_creates_scenes():
    _enable_openai_llm()
    pid = _create_project()
    _create_approved_script(pid)

    mock_scenes_data = {
        "scenes": [
            {
                "scene_number": i,
                "duration_seconds": 8,
                "narration_text": f"Narration for scene {i}",
                "visual_summary": f"Visual summary scene {i}",
                "camera_direction": "slow zoom",
                "motion_direction": "subtle",
                "sfx_notes": "none",
            }
            for i in range(1, 8)
        ]
    }

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=mock_scenes_data,
        ):
            r = client.post(f"/api/projects/{pid}/scenes/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 200
    scenes = r.json()
    assert len(scenes) == 7
    assert scenes[0]["scene_number"] == 1


# ---------------------------------------------------------------------------
# Test 9 — Prompt generation with OpenAI mocked creates prompt pairs
# ---------------------------------------------------------------------------

def test_prompt_generation_openai_mocked_creates_pairs():
    _enable_openai_llm()
    pid = _create_project()
    _create_approved_script(pid)
    _create_approved_scenes(pid)

    # Build mocked prompt pairs
    scenes_r = client.get(f"/api/projects/{pid}/scenes").json()
    mock_prompts = {
        "prompts": [
            {
                "scene_number": s["scene_number"],
                "image_prompt_text": f"Image for scene {s['scene_number']}",
                "image_negative_prompt": "text, watermark",
                "image_style_lock": "3d_explainer",
                "video_prompt_text": f"Video for scene {s['scene_number']}",
                "video_negative_prompt": "blurry, noise",
                "video_motion_strength": "medium",
                "video_camera_lock": "static",
            }
            for s in scenes_r
        ]
    }

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=mock_prompts,
        ):
            r = client.post(f"/api/projects/{pid}/prompts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 200
    pairs = r.json()
    assert len(pairs) == len(scenes_r)
    assert pairs[0]["image_prompt"] is not None
    assert pairs[0]["video_prompt"] is not None


# ---------------------------------------------------------------------------
# Test 10 — Malformed OpenAI script output returns 400
# ---------------------------------------------------------------------------

def test_malformed_openai_script_output_returns_400():
    _enable_openai_llm()
    pid = _create_project()

    # Return a dict without "script" key
    bad_result = {"hook": "hi", "word_count": 5}

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=bad_result,
        ):
            r = client.post(f"/api/projects/{pid}/scripts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 400
    assert "Malformed script" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Test 11 — Malformed OpenAI scene output returns 400 and existing scenes remain
# ---------------------------------------------------------------------------

def test_malformed_openai_scene_output_returns_400_keeps_existing():
    _enable_openai_llm()
    pid = _create_project()
    _create_approved_script(pid)

    # First generate with mock (valid)
    gen_r = client.post(f"/api/projects/{pid}/scenes/generate", json={})
    assert gen_r.status_code == 200
    original_count = len(gen_r.json())

    # Now try with OpenAI returning malformed output
    bad_result = {"not_scenes": []}  # missing "scenes" key

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=bad_result,
        ):
            r = client.post(f"/api/projects/{pid}/scenes/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 400

    # Old scenes must still exist
    remaining = client.get(f"/api/projects/{pid}/scenes").json()
    assert len(remaining) == original_count


# ---------------------------------------------------------------------------
# Test 12 — Malformed OpenAI prompt output returns 400 and existing prompts remain
# ---------------------------------------------------------------------------

def test_malformed_openai_prompt_output_returns_400_keeps_existing():
    _enable_openai_llm()
    pid = _create_project()
    _create_approved_script(pid)
    _create_approved_scenes(pid)

    # Generate valid prompts first (mock)
    pr = client.post(f"/api/projects/{pid}/prompts/generate", json={})
    assert pr.status_code == 200
    original_count = len(pr.json())

    # Now try OpenAI returning malformed output
    bad_result = {"wrong_key": []}

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=bad_result,
        ):
            r = client.post(f"/api/projects/{pid}/prompts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    assert r.status_code == 400

    # Old prompts must still exist
    remaining = client.get(f"/api/projects/{pid}/prompts").json()
    assert len(remaining) == original_count


# ---------------------------------------------------------------------------
# Test 13 — Provider run logs exist for OpenAI script/scene/prompt generation
# ---------------------------------------------------------------------------

def test_provider_run_logs_recorded_for_openai_calls():
    _enable_openai_llm()
    pid = _create_project()

    valid_script = {
        "hook": "Hook",
        "script": "Script text here.",
        "word_count": 3,
        "estimated_duration_seconds": 60,
        "payoff": "Payoff",
    }

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=valid_script,
        ):
            r = client.post(f"/api/projects/{pid}/scripts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })
    assert r.status_code == 200

    logs = client.get(f"/api/projects/{pid}/provider-runs").json()
    openai_logs = [lg for lg in logs if lg["provider_name"] == "openai"]
    assert len(openai_logs) >= 1
    assert openai_logs[0]["operation"] == "script_generation"
    assert openai_logs[0]["modality"] == "llm"


# ---------------------------------------------------------------------------
# Test 14 — Run logs do not contain OPENAI_API_KEY
# ---------------------------------------------------------------------------

def test_provider_run_logs_do_not_contain_api_key():
    _enable_openai_llm()
    pid = _create_project()

    valid_script = {
        "hook": "Hook",
        "script": "Script text.",
        "word_count": 2,
        "estimated_duration_seconds": 60,
        "payoff": "Payoff",
    }

    fake_key = "sk-very-secret-key-1234567890"

    from app.providers import openai_provider as _oai_mod
    with patch.dict(os.environ, {"OPENAI_API_KEY": fake_key}):
        with patch.object(
            _oai_mod.OpenAILLMProvider,
            "generate_structured_json",
            return_value=valid_script,
        ):
            client.post(f"/api/projects/{pid}/scripts/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini",
            })

    logs = client.get(f"/api/projects/{pid}/provider-runs").json()
    for lg in logs:
        req_str = json.dumps(lg.get("request_json", ""))
        resp_str = json.dumps(lg.get("response_json", ""))
        assert fake_key not in req_str
        assert fake_key not in resp_str


# ---------------------------------------------------------------------------
# Test 15 — Full mock pipeline still reaches FINAL_RENDER_READY
# ---------------------------------------------------------------------------

def test_full_mock_pipeline_reaches_final_render_ready():
    pid = _create_project()

    # Script
    sr = client.post(f"/api/projects/{pid}/scripts/generate", json={})
    assert sr.status_code == 200
    client.post(f"/api/scripts/{sr.json()['id']}/approve")

    # Scenes
    client.post(f"/api/projects/{pid}/scenes/generate", json={})
    client.post(f"/api/projects/{pid}/scenes/approve")

    # Prompts
    client.post(f"/api/projects/{pid}/prompts/generate", json={})
    client.post(f"/api/projects/{pid}/prompts/approve")

    # Assets
    client.post(f"/api/projects/{pid}/assets/images/generate")
    client.post(f"/api/projects/{pid}/assets/clips/generate")
    client.post(f"/api/projects/{pid}/assets/approve")

    # Audio + Subtitles
    client.post(f"/api/projects/{pid}/audio/voiceover/generate")
    client.post(f"/api/projects/{pid}/subtitles/generate")
    client.post(f"/api/projects/{pid}/subtitles/approve")

    # Render
    rr = client.post(f"/api/projects/{pid}/renders/generate")
    assert rr.status_code == 200

    approve_r = client.post(f"/api/projects/{pid}/renders/approve")
    assert approve_r.status_code == 200

    proj = client.get(f"/api/projects/{pid}").json()
    assert proj["status"] == "FINAL_RENDER_READY"
