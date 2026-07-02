"""
Phase 14 tests — Real Voiceover Provider via OpenAI TTS

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
# Isolated in-memory DB
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

def _create_project(title="P14 Test", topic="Science", duration_target=30):
    r = client.post("/api/projects/", json={"title": title, "topic": topic, "duration_target": duration_target})
    assert r.status_code == 200
    return r.json()["id"]


def _create_approved_assets_plan(project_id=None):
    if project_id is None:
        project_id = _create_project()
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = client.get(f"/api/projects/{project_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    client.post(f"/api/projects/{project_id}/assets/approve")
    return project_id


def _get_openai_tts_model():
    models = client.get("/api/providers/models").json()
    m = next((m for m in models if m["provider_name"] == "openai" and m["modality"] == "audio"), None)
    assert m is not None, "OpenAI TTS model not in catalog"
    return m


def _enable_openai_tts():
    m = _get_openai_tts_model()
    client.post(f"/api/providers/models/{m['id']}/enable")


def _disable_openai_tts():
    m = _get_openai_tts_model()
    client.post(f"/api/providers/models/{m['id']}/disable")


# ---------------------------------------------------------------------------
# Test 1 — OpenAI TTS model seeded disabled by default
# ---------------------------------------------------------------------------

def test_openai_tts_model_seeded_disabled():
    m = _get_openai_tts_model()
    assert m["is_enabled"] is False
    assert m["modality"] == "audio"
    assert m["cost_hint"] == "paid"


# ---------------------------------------------------------------------------
# Test 2 — OpenAI TTS model does not appear in enabled audio models by default
# ---------------------------------------------------------------------------

def test_openai_tts_not_in_enabled_models_by_default():
    enabled = client.get("/api/providers/models/enabled").json()
    audio_models = [m for m in enabled if m["modality"] == "audio"]
    openai_audio = [m for m in audio_models if m["provider_name"] == "openai"]
    assert len(openai_audio) == 0
    # Mock audio should be the only enabled audio model
    assert any(m["model_name"] == "mock-audio" for m in audio_models)


# ---------------------------------------------------------------------------
# Test 3 — OpenAI audio preflight fails when disabled
# ---------------------------------------------------------------------------

def test_openai_audio_preflight_fails_when_disabled():
    _disable_openai_tts()
    res = client.post("/api/providers/preflight", json={
        "provider_name": "openai",
        "model_name": "gpt-4o-mini-tts",
        "modality": "audio",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "disabled" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 4 — OpenAI audio preflight fails when enabled but key missing
# ---------------------------------------------------------------------------

def test_openai_audio_preflight_fails_when_key_missing():
    _enable_openai_tts()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENAI_API_KEY", None)
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini-tts",
            "modality": "audio",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "OPENAI_API_KEY" in data["message"]


# ---------------------------------------------------------------------------
# Test 5 — OpenAI audio preflight passes when enabled and key mocked
# ---------------------------------------------------------------------------

def test_openai_audio_preflight_passes_when_enabled_and_key_present():
    _enable_openai_tts()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini-tts",
            "modality": "audio",
        })
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ---------------------------------------------------------------------------
# Test 6 — Voiceover estimate defaults to mock and requires no confirmation
# ---------------------------------------------------------------------------

def test_voiceover_estimate_defaults_to_mock_no_confirmation():
    project_id = _create_approved_assets_plan()
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider_name"] == "mock"
    assert data["model_name"] == "mock-audio"
    assert data["requires_confirmation"] is False
    assert data["estimated_jobs"] == 1


# ---------------------------------------------------------------------------
# Test 7 — Voiceover estimate for OpenAI disabled returns ok=false
# ---------------------------------------------------------------------------

def test_voiceover_estimate_openai_disabled_returns_not_ok():
    _disable_openai_tts()
    project_id = _create_approved_assets_plan()
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={
        "provider_name": "openai",
        "model_name": "gpt-4o-mini-tts",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False


# ---------------------------------------------------------------------------
# Test 8 — Voiceover estimate for OpenAI enabled without key returns ok=false
# ---------------------------------------------------------------------------

def test_voiceover_estimate_openai_no_key_returns_not_ok():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENAI_API_KEY", None)
        res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini-tts",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "OPENAI_API_KEY" in data["message"]


# ---------------------------------------------------------------------------
# Test 9 — Voiceover estimate for OpenAI enabled with key returns ok=true
# ---------------------------------------------------------------------------

def test_voiceover_estimate_openai_with_key_returns_ok():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={
            "provider_name": "openai",
            "model_name": "gpt-4o-mini-tts",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["requires_confirmation"] is True
    assert data["cost_hint"] == "paid"


# ---------------------------------------------------------------------------
# Test 10 — Voiceover estimate returns correct script_id, character_count, estimated_jobs=1
# ---------------------------------------------------------------------------

def test_voiceover_estimate_returns_correct_fields():
    project_id = _create_approved_assets_plan()
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={
        "provider_name": "mock",
        "model_name": "mock-audio",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["script_id"] is not None
    assert data["character_count"] > 0
    assert data["estimated_jobs"] == 1
    assert data["modality"] == "audio"


# ---------------------------------------------------------------------------
# Test 11 — Voiceover estimate returns ok=false when approved script is missing
# ---------------------------------------------------------------------------

def test_voiceover_estimate_missing_script_returns_not_ok():
    project_id = _create_project()
    # No script generated
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    # The project status check fires before the script check
    assert "status" in data["message"].lower() or "script" in data["message"].lower() or "allow" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 12 — Voiceover estimate returns ok=false before CLIPS_GENERATED
# ---------------------------------------------------------------------------

def test_voiceover_estimate_before_clips_generated_returns_not_ok():
    project_id = _create_project()
    # Generate script but don't go through the full pipeline
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = client.get(f"/api/projects/{project_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")
    # Project status is SCRIPT_READY, not CLIPS_GENERATED
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "status" in data["message"].lower() or "allow" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 13 — Mock voiceover generation does not require confirmation
# ---------------------------------------------------------------------------

def test_mock_voiceover_generation_no_confirmation_required():
    project_id = _create_approved_assets_plan()
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "mock",
        "model_name": "mock-audio",
        "confirmed": False,
    })
    assert res.status_code == 200
    vo = res.json()
    assert vo["provider_job_id"] is not None
    assert vo["is_active"] is True
    assert vo["provider_name"] == "mock"


# ---------------------------------------------------------------------------
# Test 14 — OpenAI voiceover generation without confirmation returns 400
# ---------------------------------------------------------------------------

def test_openai_voiceover_without_confirmation_returns_400():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "openai",
        "model_name": "gpt-4o-mini-tts",
        "confirmed": False,
    })
    assert res.status_code == 400
    assert "confirmation" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 15 — OpenAI voiceover with confirmation calls mocked provider and creates voiceover
# ---------------------------------------------------------------------------

def test_openai_voiceover_with_confirmation_creates_voiceover():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()

    # Build a mock audio bytes response
    mock_audio_bytes = b"fake-mp3-audio-data"

    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tts_test_abc123",
        status="COMPLETED",
        result={
            "provider_job_id": "tts_test_abc123",
            "file_url": None,
            "duration_seconds": 0,
            "format": "mp3",
            "status": "COMPLETED",
            "raw_response": {"model": "gpt-4o-mini-tts", "voice": "alloy"},
            "_audio_bytes": mock_audio_bytes,
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAITTSProvider,
            "generate_voiceover",
            return_value=mock_job,
        ):
            res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "voice_id": "alloy",
                "confirmed": True,
            })

    assert res.status_code == 200
    vo = res.json()
    assert vo["provider_name"] == "openai"
    assert vo["model_name"] == "gpt-4o-mini-tts"
    assert vo["voice_id"] == "alloy"
    assert vo["provider_job_id"] == "tts_test_abc123"
    assert vo["status"] == "COMPLETED"
    assert vo["is_active"] is True
    assert "voiceover_tts_test_abc123.mp3" in vo["file_url"]


# ---------------------------------------------------------------------------
# Test 16 — Generated voiceover stores provider name, model name, voice ID, etc.
# ---------------------------------------------------------------------------

def test_generated_voiceover_stores_provider_fields():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()

    mock_audio_bytes = b"fake-mp3-data"
    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tts_fields_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tts_fields_test",
            "file_url": None,
            "duration_seconds": 0,
            "format": "mp3",
            "status": "COMPLETED",
            "raw_response": {},
            "_audio_bytes": mock_audio_bytes,
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(_oai_mod.OpenAITTSProvider, "generate_voiceover", return_value=mock_job):
            res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "voice_id": "nova",
                "confirmed": True,
            })

    assert res.status_code == 200
    vo = res.json()
    assert vo["provider_name"] == "openai"
    assert vo["model_name"] == "gpt-4o-mini-tts"
    assert vo["voice_id"] == "nova"
    assert vo["file_url"] is not None
    assert vo["duration_seconds"] == 0  # unknown duration → 0
    assert vo["provider_job_id"] == "tts_fields_test"


# ---------------------------------------------------------------------------
# Test 17 — Provider run logs created for OpenAI voiceover generation
# ---------------------------------------------------------------------------

def test_provider_run_logs_created_for_openai_voiceover():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()

    mock_audio_bytes = b"fake-mp3-data"
    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tts_log_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tts_log_test",
            "file_url": None,
            "duration_seconds": 0,
            "format": "mp3",
            "status": "COMPLETED",
            "raw_response": {},
            "_audio_bytes": mock_audio_bytes,
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(_oai_mod.OpenAITTSProvider, "generate_voiceover", return_value=mock_job):
            client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "confirmed": True,
            })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    openai_logs = [lg for lg in logs if lg["provider_name"] == "openai" and lg["modality"] == "audio"]
    assert len(openai_logs) >= 1
    assert openai_logs[0]["operation"] == "voiceover_generation"
    assert openai_logs[0]["model_name"] == "gpt-4o-mini-tts"


# ---------------------------------------------------------------------------
# Test 18 — Provider run logs do not contain OPENAI_API_KEY
# ---------------------------------------------------------------------------

def test_provider_run_logs_no_api_key_leakage():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()

    fake_key = "sk-top-secret-key-987654321"
    mock_audio_bytes = b"fake-mp3-data"
    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tts_noleak_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tts_noleak_test",
            "file_url": None,
            "duration_seconds": 0,
            "format": "mp3",
            "status": "COMPLETED",
            "raw_response": {},
            "_audio_bytes": mock_audio_bytes,
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": fake_key}):
        with patch.object(_oai_mod.OpenAITTSProvider, "generate_voiceover", return_value=mock_job):
            client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "confirmed": True,
            })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    for lg in logs:
        req_str = json.dumps(lg.get("request_json", ""))
        resp_str = json.dumps(lg.get("response_json", ""))
        assert fake_key not in req_str, f"API key found in request_json of log {lg['id']}"
        assert fake_key not in resp_str, f"API key found in response_json of log {lg['id']}"


# ---------------------------------------------------------------------------
# Test 19 — Malformed OpenAI TTS response returns 400 and keeps existing voiceover
# ---------------------------------------------------------------------------

def test_malformed_openai_tts_keeps_existing_voiceover():
    project_id = _create_approved_assets_plan()

    # Step 1: Generate mock voiceover
    res1 = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "mock",
        "model_name": "mock-audio",
    })
    assert res1.status_code == 200
    vo1 = res1.json()
    assert vo1["is_active"] is True

    # Step 2: Try OpenAI TTS but make it fail
    _enable_openai_tts()
    from app.providers import openai_provider as _oai_mod

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAITTSProvider,
            "generate_voiceover",
            side_effect=Exception("Simulated TTS failure"),
        ):
            res2 = client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "confirmed": True,
            })

    assert res2.status_code == 400

    # Step 3: Verify old voiceover still active
    active = client.get(f"/api/projects/{project_id}/audio/voiceover").json()
    assert active["id"] == vo1["id"]
    assert active["is_active"] is True
    assert active["provider_name"] == "mock"


# ---------------------------------------------------------------------------
# Test 20 — Failed OpenAI TTS logs a failed provider run without leaking secrets
# ---------------------------------------------------------------------------

def test_failed_openai_tts_logs_failed_run():
    _enable_openai_tts()
    project_id = _create_approved_assets_plan()

    fake_key = "sk-secret-leak-test"
    from app.providers import openai_provider as _oai_mod

    with patch.dict(os.environ, {"OPENAI_API_KEY": fake_key}):
        with patch.object(
            _oai_mod.OpenAITTSProvider,
            "generate_voiceover",
            side_effect=Exception("Simulated TTS error"),
        ):
            client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
                "provider_name": "openai",
                "model_name": "gpt-4o-mini-tts",
                "confirmed": True,
            })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    failed_logs = [lg for lg in logs if lg["status"] == "FAILED"]
    assert len(failed_logs) >= 1
    assert failed_logs[0]["provider_name"] == "openai"
    assert failed_logs[0]["modality"] == "audio"
    # No key leakage
    for lg in logs:
        req_str = json.dumps(lg.get("request_json", ""))
        resp_str = json.dumps(lg.get("response_json", ""))
        err_str = lg.get("error_message", "") or ""
        assert fake_key not in req_str
        assert fake_key not in resp_str
        assert fake_key not in err_str


# ---------------------------------------------------------------------------
# Test 21 — Full mock pipeline still reaches FINAL_RENDER_READY
# ---------------------------------------------------------------------------

def test_full_mock_pipeline_reaches_final_render_ready():
    project_id = _create_project(title="P14 Full Mock Pipeline", topic="Test")

    # Script
    sr = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    assert sr.status_code == 200
    client.post(f"/api/scripts/{sr.json()['id']}/approve")

    # Scenes
    client.post(f"/api/projects/{project_id}/scenes/generate", json={})
    client.post(f"/api/projects/{project_id}/scenes/approve")

    # Prompts
    client.post(f"/api/projects/{project_id}/prompts/generate", json={})
    client.post(f"/api/projects/{project_id}/prompts/approve")

    # Assets
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    client.post(f"/api/projects/{project_id}/assets/approve")

    # Audio + Subtitles (mock voiceover)
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "mock",
        "model_name": "mock-audio",
    })
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    client.post(f"/api/projects/{project_id}/subtitles/approve")

    # Render
    rr = client.post(f"/api/projects/{project_id}/renders/generate")
    assert rr.status_code == 200

    approve_r = client.post(f"/api/projects/{project_id}/renders/approve")
    assert approve_r.status_code == 200

    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "FINAL_RENDER_READY"


# ---------------------------------------------------------------------------
# Test 22 — Existing Phase 1–13 tests still pass (spot check)
# ---------------------------------------------------------------------------

def test_existing_mock_voiceover_still_works():
    """Verify that the backward-compatible mock voiceover generation still works."""
    project_id = _create_approved_assets_plan()

    # Old-style call (no provider specified → defaults to mock)
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    assert res.status_code == 200
    vo = res.json()
    assert vo["provider_job_id"] is not None
    assert vo["duration_seconds"] == 30
    assert vo["is_active"] is True

    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "VOICEOVER_READY"


def test_existing_voiceover_deactivation_still_works():
    """Verify that generating a second voiceover deactivates the first."""
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


def test_estimate_endpoint_requires_valid_project():
    res = client.post("/api/projects/99999/audio/voiceover/estimate", json={})
    assert res.status_code == 404


def test_estimate_endpoint_rejects_before_assets_approved():
    project_id = _create_project()
    # No pipeline steps
    res = client.post(f"/api/projects/{project_id}/audio/voiceover/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
