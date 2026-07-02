"""
Phase 15 tests — Real Subtitle Timing via OpenAI Transcription

All tests use mock/stub; no real OpenAI API calls are made.
"""
import json
import os
from pathlib import Path
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

def _create_project(title="P15 Test", topic="Science", duration_target=30):
    r = client.post("/api/projects/", json={"title": title, "topic": topic, "duration_target": duration_target})
    assert r.status_code == 200
    return r.json()["id"]


def _setup_to_voiceover_ready(project_id=None):
    """Run full mock pipeline up to VOICEOVER_READY."""
    if project_id is None:
        project_id = _create_project()
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    sid = client.get(f"/api/projects/{project_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{sid}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    client.post(f"/api/projects/{project_id}/assets/images/generate")
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    client.post(f"/api/projects/{project_id}/assets/approve")
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "mock", "model_name": "mock-audio",
    })
    return project_id


def _get_openai_transcription_model():
    models = client.get("/api/providers/models").json()
    m = next((m for m in models if m["provider_name"] == "openai" and m["modality"] == "transcription"), None)
    assert m is not None, "OpenAI transcription model not in catalog"
    return m


def _enable_openai_transcription():
    m = _get_openai_transcription_model()
    client.post(f"/api/providers/models/{m['id']}/enable")


def _disable_openai_transcription():
    m = _get_openai_transcription_model()
    client.post(f"/api/providers/models/{m['id']}/disable")


# ---------------------------------------------------------------------------
# Test 1 — OpenAI transcription model seeded disabled by default
# ---------------------------------------------------------------------------

def test_openai_transcription_model_seeded_disabled():
    m = _get_openai_transcription_model()
    assert m["is_enabled"] is False
    assert m["modality"] == "transcription"
    assert m["cost_hint"] == "paid"
    assert m["model_name"] == "whisper-1"


# ---------------------------------------------------------------------------
# Test 2 — OpenAI transcription model not in enabled models by default
# ---------------------------------------------------------------------------

def test_openai_transcription_not_in_enabled_by_default():
    enabled = client.get("/api/providers/models/enabled").json()
    trans_models = [m for m in enabled if m["modality"] == "transcription"]
    openai_trans = [m for m in trans_models if m["provider_name"] == "openai"]
    assert len(openai_trans) == 0
    assert any(m["model_name"] == "mock-transcription" for m in trans_models)


# ---------------------------------------------------------------------------
# Test 3 — Preflight fails when disabled
# ---------------------------------------------------------------------------

def test_openai_transcription_preflight_fails_when_disabled():
    _disable_openai_transcription()
    res = client.post("/api/providers/preflight", json={
        "provider_name": "openai",
        "model_name": "whisper-1",
        "modality": "transcription",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "disabled" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test 4 — Preflight fails when enabled but key missing
# ---------------------------------------------------------------------------

def test_openai_transcription_preflight_fails_when_key_missing():
    _enable_openai_transcription()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENAI_API_KEY", None)
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "whisper-1",
            "modality": "transcription",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "OPENAI_API_KEY" in data["message"]


# ---------------------------------------------------------------------------
# Test 5 — Preflight passes when enabled and key mocked
# ---------------------------------------------------------------------------

def test_openai_transcription_preflight_passes_when_enabled_and_key_present():
    _enable_openai_transcription()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        res = client.post("/api/providers/preflight", json={
            "provider_name": "openai",
            "model_name": "whisper-1",
            "modality": "transcription",
        })
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ---------------------------------------------------------------------------
# Test 6 — Subtitle estimate defaults to mock and requires no confirmation
# ---------------------------------------------------------------------------

def test_subtitle_estimate_defaults_to_mock_no_confirmation():
    project_id = _setup_to_voiceover_ready()
    res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["provider_name"] == "mock"
    assert data["model_name"] == "mock-transcription"
    assert data["requires_confirmation"] is False
    assert data["estimated_jobs"] == 1


# ---------------------------------------------------------------------------
# Test 7 — Subtitle estimate for OpenAI disabled returns ok=false
# ---------------------------------------------------------------------------

def test_subtitle_estimate_openai_disabled_returns_not_ok():
    _disable_openai_transcription()
    project_id = _setup_to_voiceover_ready()
    res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={
        "provider_name": "openai",
        "model_name": "whisper-1",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False


# ---------------------------------------------------------------------------
# Test 8 — Subtitle estimate for OpenAI enabled without key returns ok=false
# ---------------------------------------------------------------------------

def test_subtitle_estimate_openai_no_key_returns_not_ok():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENAI_API_KEY", None)
        res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={
            "provider_name": "openai",
            "model_name": "whisper-1",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "OPENAI_API_KEY" in data["message"]


# ---------------------------------------------------------------------------
# Test 9 — Subtitle estimate for OpenAI enabled with key returns ok=true
# ---------------------------------------------------------------------------

def test_subtitle_estimate_openai_with_key_returns_ok():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={
            "provider_name": "openai",
            "model_name": "whisper-1",
        })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["requires_confirmation"] is True
    assert data["cost_hint"] == "paid"


# ---------------------------------------------------------------------------
# Test 10 — Subtitle estimate returns correct voiceover_id, audio_file_url, estimated_jobs=1
# ---------------------------------------------------------------------------

def test_subtitle_estimate_returns_correct_fields():
    project_id = _setup_to_voiceover_ready()
    res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={
        "provider_name": "mock",
        "model_name": "mock-transcription",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["voiceover_id"] is not None
    assert data["audio_file_url"] is not None
    assert data["estimated_jobs"] == 1
    assert data["modality"] == "transcription"


# ---------------------------------------------------------------------------
# Test 11 — Subtitle estimate returns ok=false when active voiceover missing
# ---------------------------------------------------------------------------

def test_subtitle_estimate_missing_voiceover_returns_not_ok():
    project_id = _create_project()
    # No voiceover generated — status is DRAFT_CREATED
    res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False


# ---------------------------------------------------------------------------
# Test 12 — Subtitle estimate returns ok=false before VOICEOVER_READY
# ---------------------------------------------------------------------------

def test_subtitle_estimate_before_voiceover_ready_returns_not_ok():
    project_id = _create_project()
    # Only generate+approve script
    client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    sid = client.get(f"/api/projects/{project_id}/scripts/latest").json()["id"]
    client.post(f"/api/scripts/{sid}/approve")
    # Status is SCRIPT_READY
    res = client.post(f"/api/projects/{project_id}/subtitles/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False


# ---------------------------------------------------------------------------
# Test 13 — Mock subtitle generation does not require confirmation
# ---------------------------------------------------------------------------

def test_mock_subtitle_generation_no_confirmation_required():
    project_id = _setup_to_voiceover_ready()
    res = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "mock",
        "model_name": "mock-transcription",
        "confirmed": False,
    })
    assert res.status_code == 200
    segments = res.json()
    assert len(segments) > 0
    assert segments[0]["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# Test 14 — OpenAI subtitle generation without confirmation returns 400
# ---------------------------------------------------------------------------

def test_openai_subtitle_generation_without_confirmation_returns_400():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()
    res = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "openai",
        "model_name": "whisper-1",
        "confirmed": False,
    })
    assert res.status_code == 400
    assert "confirmation" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 15 — OpenAI subtitle generation with confirmation calls mocked provider
# ---------------------------------------------------------------------------

def test_openai_subtitle_generation_with_confirmation_creates_segments():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()

    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tr_test_abc123",
        status="COMPLETED",
        result={
            "provider_job_id": "tr_test_abc123",
            "text": "Full transcription text.",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "First segment text."},
                {"start": 2.5, "end": 5.0, "text": "Second segment text."},
                {"start": 5.0, "end": 7.5, "text": "Third segment text."},
            ],
            "duration_seconds": 7.5,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    # The voiceover file_url points to a non-existent local path. We need to
    # mock both the provider call AND the audio file existence check.
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider, "transcribe_audio", return_value=mock_job
            ):
                res = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    assert res.status_code == 200
    segments = res.json()
    assert len(segments) == 3
    assert segments[0]["text"] == "First segment text."
    assert segments[0]["start_time"] == 0.0
    assert segments[0]["end_time"] == 2.5
    assert segments[1]["text"] == "Second segment text."
    assert segments[2]["text"] == "Third segment text."


# ---------------------------------------------------------------------------
# Test 16 — Created subtitle segments use provider start/end/text data correctly
# ---------------------------------------------------------------------------

def test_subtitle_segments_use_provider_data():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()

    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tr_data_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tr_data_test",
            "text": "Full text.",
            "segments": [
                {"start": 1.0, "end": 3.5, "text": "Hello world."},
            ],
            "duration_seconds": 3.5,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider, "transcribe_audio", return_value=mock_job
            ):
                res = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    assert res.status_code == 200
    segments = res.json()
    assert len(segments) == 1
    seg = segments[0]
    assert seg["start_time"] == 1.0
    assert seg["end_time"] == 3.5
    assert seg["text"] == "Hello world."
    assert seg["index"] == 0
    assert seg["style"] == "bold_white_black_stroke"
    assert seg["status"] == "DRAFT"


# ---------------------------------------------------------------------------
# Test 17 — Provider run logs created for OpenAI subtitle generation
# ---------------------------------------------------------------------------

def test_provider_run_logs_created_for_openai_subtitles():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()

    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tr_log_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tr_log_test",
            "text": "Text.",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Segment."}],
            "duration_seconds": 2.0,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider, "transcribe_audio", return_value=mock_job
            ):
                client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    trans_logs = [lg for lg in logs if lg["provider_name"] == "openai" and lg["modality"] == "transcription"]
    assert len(trans_logs) >= 1
    assert trans_logs[0]["operation"] == "subtitle_generation"
    assert trans_logs[0]["model_name"] == "whisper-1"


# ---------------------------------------------------------------------------
# Test 18 — Provider run logs do not contain OPENAI_API_KEY
# ---------------------------------------------------------------------------

def test_provider_run_logs_no_api_key_leakage():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()

    fake_key = "sk-top-secret-transcription-key"
    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tr_noleak_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tr_noleak_test",
            "text": "Text.",
            "segments": [{"start": 0.0, "end": 2.0, "text": "Segment."}],
            "duration_seconds": 2.0,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": fake_key}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider, "transcribe_audio", return_value=mock_job
            ):
                client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    for lg in logs:
        req_str = json.dumps(lg.get("request_json", ""))
        resp_str = json.dumps(lg.get("response_json", ""))
        assert fake_key not in req_str, f"API key found in request_json of log {lg['id']}"
        assert fake_key not in resp_str, f"API key found in response_json of log {lg['id']}"


# ---------------------------------------------------------------------------
# Test 19 — Malformed OpenAI transcription returns 400, keeps existing subtitles
# ---------------------------------------------------------------------------

def test_malformed_openai_transcription_keeps_existing_subtitles():
    project_id = _setup_to_voiceover_ready()

    # Step 1: Generate mock subtitles
    res1 = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "mock",
        "model_name": "mock-transcription",
    })
    assert res1.status_code == 200
    original_segments = res1.json()
    original_count = len(original_segments)
    assert original_count > 0

    # Step 2: Try OpenAI transcription but make it fail
    _enable_openai_transcription()
    from app.providers import openai_provider as _oai_mod

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(
            _oai_mod.OpenAITranscriptionProvider,
            "transcribe_audio",
            side_effect=Exception("Simulated transcription failure"),
        ):
            res2 = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                "provider_name": "openai",
                "model_name": "whisper-1",
                "confirmed": True,
            })

    assert res2.status_code == 400

    # Step 3: Verify existing subtitles still intact
    remaining = client.get(f"/api/projects/{project_id}/subtitles").json()
    assert len(remaining) == original_count
    for i, seg in enumerate(remaining):
        assert seg["text"] == original_segments[i]["text"]


# ---------------------------------------------------------------------------
# Test 20 — Failed OpenAI transcription logs a failed provider run without leaking secrets
# ---------------------------------------------------------------------------

def test_failed_openai_transcription_logs_failed_run():
    _enable_openai_transcription()
    project_id = _setup_to_voiceover_ready()

    fake_key = "sk-secret-transcription-leak"
    from app.providers import openai_provider as _oai_mod

    with patch.dict(os.environ, {"OPENAI_API_KEY": fake_key}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider,
                "transcribe_audio",
                side_effect=Exception("Simulated transcription error"),
            ):
                client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    failed_logs = [lg for lg in logs if lg["status"] == "FAILED"]
    assert len(failed_logs) >= 1
    assert failed_logs[0]["provider_name"] == "openai"
    assert failed_logs[0]["modality"] == "transcription"
    # No key leakage
    for lg in logs:
        req_str = json.dumps(lg.get("request_json", ""))
        resp_str = json.dumps(lg.get("response_json", ""))
        err_str = lg.get("error_message", "") or ""
        assert fake_key not in req_str
        assert fake_key not in resp_str
        assert fake_key not in err_str


# ---------------------------------------------------------------------------
# Test 21 — Empty segment response returns 400 and keeps existing subtitles
# ---------------------------------------------------------------------------

def test_empty_segments_response_keeps_existing_subtitles():
    project_id = _setup_to_voiceover_ready()

    # Generate mock subtitles first
    res1 = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "mock",
        "model_name": "mock-transcription",
    })
    assert res1.status_code == 200
    original_segments = res1.json()
    original_count = len(original_segments)

    # Try OpenAI with empty segments
    _enable_openai_transcription()
    from app.providers import openai_provider as _oai_mod
    from app.providers.base import ProviderJob

    mock_job = ProviderJob(
        job_id="tr_empty_test",
        status="COMPLETED",
        result={
            "provider_job_id": "tr_empty_test",
            "text": "",
            "segments": [],
            "duration_seconds": 0,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}):
        with patch.object(Path, "exists", return_value=True):
            with patch.object(
                _oai_mod.OpenAITranscriptionProvider, "transcribe_audio", return_value=mock_job
            ):
                res2 = client.post(f"/api/projects/{project_id}/subtitles/generate", json={
                    "provider_name": "openai",
                    "model_name": "whisper-1",
                    "confirmed": True,
                })

    assert res2.status_code == 400
    assert "no valid subtitle segments" in res2.json()["detail"].lower()

    # Existing subtitles still intact
    remaining = client.get(f"/api/projects/{project_id}/subtitles").json()
    assert len(remaining) == original_count


# ---------------------------------------------------------------------------
# Test 22 — Full mock pipeline still reaches FINAL_RENDER_READY
# ---------------------------------------------------------------------------

def test_full_mock_pipeline_reaches_final_render_ready():
    project_id = _create_project(title="P15 Full Mock Pipeline", topic="Test")

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

    # Audio + Subtitles (mock)
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate", json={
        "provider_name": "mock", "model_name": "mock-audio",
    })
    client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "mock", "model_name": "mock-transcription",
    })
    client.post(f"/api/projects/{project_id}/subtitles/approve")

    # Render
    rr = client.post(f"/api/projects/{project_id}/renders/generate")
    assert rr.status_code == 200

    approve_r = client.post(f"/api/projects/{project_id}/renders/approve")
    assert approve_r.status_code == 200

    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "FINAL_RENDER_READY"


# ---------------------------------------------------------------------------
# Test 23 — Existing Phase 1–14 tests compatibility checks
# ---------------------------------------------------------------------------

def test_existing_subtitle_generation_still_works():
    """Verify backward-compatible subtitle generation."""
    project_id = _setup_to_voiceover_ready()
    # Old-style call (no provider specified → defaults to mock)
    res = client.post(f"/api/projects/{project_id}/subtitles/generate")
    assert res.status_code == 200
    segments = res.json()
    assert len(segments) > 0
    assert segments[0]["status"] == "DRAFT"


def test_existing_subtitle_endpoints_still_work():
    """Verify list, update, approve still function."""
    project_id = _setup_to_voiceover_ready()
    client.post(f"/api/projects/{project_id}/subtitles/generate", json={
        "provider_name": "mock", "model_name": "mock-transcription",
    })

    # List
    res = client.get(f"/api/projects/{project_id}/subtitles")
    assert res.status_code == 200
    assert len(res.json()) > 0

    # Update
    sub_id = res.json()[0]["id"]
    update_res = client.patch(f"/api/subtitles/{sub_id}", json={"text": "Updated text!"})
    assert update_res.status_code == 200
    assert update_res.json()["text"] == "Updated text!"

    # Approve
    approve_res = client.post(f"/api/projects/{project_id}/subtitles/approve")
    assert approve_res.status_code == 200
    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "SUBTITLES_READY"


def test_subtitle_estimate_requires_valid_project():
    res = client.post("/api/projects/99999/subtitles/estimate", json={})
    assert res.status_code == 404


def test_subtitle_generation_before_voiceover_returns_400():
    project_id = _create_project()
    # No voiceover
    res = client.post(f"/api/projects/{project_id}/subtitles/generate")
    assert res.status_code == 400
    assert "before voiceover" in res.json()["detail"]


def test_missing_entities():
    assert client.post("/api/projects/999/subtitles/generate").status_code == 404
    assert client.get("/api/projects/999/subtitles").status_code == 404
    assert client.patch("/api/subtitles/999", json={"text": "hi"}).status_code == 404
    assert client.post("/api/projects/999/subtitles/approve").status_code == 404
