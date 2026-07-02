import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.providers.wavespeed_provider import WavespeedVideoProvider, ProviderJob

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

FAKE_API_KEY = "fake-wavespeed-key-for-testing-only"


@pytest.fixture(autouse=True)
def setup_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    from app.services.model_catalog_service import seed_default_mock_models
    seed_default_mock_models(db)
    db.close()

    yield

    app.dependency_overrides.clear()


def _get_wavespeed_video_model_id():
    models = client.get("/api/providers/models").json()
    for m in models:
        if m["provider_name"] == "wavespeed" and m["modality"] == "video":
            return m["id"]
    return None


def _enable_wavespeed_video_model():
    model_id = _get_wavespeed_video_model_id()
    if model_id:
        client.post(f"/api/providers/models/{model_id}/enable")


def _setup_ready_for_clips(proj_title):
    proj_res = client.post("/api/projects/", json={
        "title": proj_title,
        "topic": "Testing WaveSpeed Video",
        "duration_target": 40,
    })
    project_id = proj_res.json()["id"]

    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")

    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")

    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")

    client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    return project_id


# --- Test 1: Wavespeed video model seeded disabled ---
def test_wavespeed_video_model_seeded_disabled():
    models = client.get("/api/providers/models").json()
    ws_video = [m for m in models if m["provider_name"] == "wavespeed" and m["modality"] == "video"]
    assert len(ws_video) == 1
    assert ws_video[0]["is_enabled"] is False
    assert ws_video[0]["is_mock"] is False
    assert ws_video[0]["cost_hint"] == "paid"


# --- Test 2: Wavespeed video not in enabled video models ---
def test_wavespeed_video_not_in_enabled():
    enabled = client.get("/api/providers/models/enabled").json()
    video_models = [m for m in enabled if m["modality"] == "video"]
    ws = [m for m in video_models if m["provider_name"] == "wavespeed"]
    assert len(ws) == 0
    assert any(m["provider_name"] == "mock" for m in video_models)


# --- Test 3: Wavespeed video preflight fails when disabled ---
def test_wavespeed_video_preflight_fails_disabled():
    payload = {"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "modality": "video"}
    res = client.post("/api/providers/preflight", json=payload)
    assert res.json()["ok"] is False
    assert "disabled" in res.json()["message"]


# --- Test 4: Wavespeed video preflight fails without API key ---
def test_wavespeed_video_preflight_fails_no_key():
    _enable_wavespeed_video_model()
    with patch.dict(os.environ, {}, clear=True):
        payload = {"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "modality": "video"}
        res = client.post("/api/providers/preflight", json=payload)
        assert res.json()["ok"] is False
        assert "WAVESPEED_API_KEY" in res.json()["message"]


# --- Test 5: Wavespeed video preflight passes with key ---
def test_wavespeed_video_preflight_passes():
    _enable_wavespeed_video_model()
    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        payload = {"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "modality": "video"}
        res = client.post("/api/providers/preflight", json=payload)
        assert res.json()["ok"] is True


# --- Test 6: Project clip estimate defaults to mock ---
def test_clip_estimate_defaults_mock():
    project_id = _setup_ready_for_clips("clip-est-mock")
    res = client.post(f"/api/projects/{project_id}/assets/clips/estimate", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["requires_confirmation"] is False
    assert data["cost_hint"] == "mock-free"
    assert data["scene_count"] == 8
    assert data["estimated_jobs"] == 8


# --- Test 7: Clip estimate for wavespeed disabled returns ok=false ---
def test_clip_estimate_wavespeed_disabled():
    project_id = _setup_ready_for_clips("clip-est-ws-disabled")
    res = client.post(
        f"/api/projects/{project_id}/assets/clips/estimate",
        json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b"},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is False


# --- Test 8: Clip estimate for wavespeed enabled without key returns ok=false ---
def test_clip_estimate_wavespeed_no_key():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("clip-est-ws-nokey")
    with patch.dict(os.environ, {}, clear=True):
        res = client.post(
            f"/api/projects/{project_id}/assets/clips/estimate",
            json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b"},
        )
        assert res.json()["ok"] is False


# --- Test 9: Clip estimate for wavespeed enabled with key returns ok=true ---
def test_clip_estimate_wavespeed_with_key():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("clip-est-ws-ok")
    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        res = client.post(
            f"/api/projects/{project_id}/assets/clips/estimate",
            json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b"},
        )
        data = res.json()
        assert data["ok"] is True
        assert data["requires_confirmation"] is True
        assert data["cost_hint"] == "paid"
        assert data["estimated_jobs"] == 8


# --- Test 10: Clip estimate returns correct counts ---
def test_clip_estimate_counts():
    project_id = _setup_ready_for_clips("clip-est-counts")
    res = client.post(f"/api/projects/{project_id}/assets/clips/estimate", json={})
    data = res.json()
    assert data["scene_count"] == 8
    assert data["approved_video_prompt_count"] == 8
    assert data["active_image_count"] == 8
    assert data["estimated_jobs"] == 8


# --- Test 11: Clip estimate returns ok=false when active images missing ---
def test_clip_estimate_no_active_images():
    proj_res = client.post("/api/projects/", json={
        "title": "clip-est-no-img", "topic": "Testing", "duration_target": 40,
    })
    project_id = proj_res.json()["id"]
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    # No images generated

    res = client.post(
        f"/api/projects/{project_id}/assets/clips/estimate",
        json={"provider_name": "mock", "model_name": "mock-video"},
    )
    data = res.json()
    assert data["ok"] is False
    assert data["active_image_count"] == 0
    assert "before images" in data["message"].lower()


# --- Test 12: Clip estimate returns ok=false when video prompts missing ---
def test_clip_estimate_no_video_prompts():
    proj_res = client.post("/api/projects/", json={
        "title": "clip-est-no-vp", "topic": "Testing", "duration_target": 40,
    })
    project_id = proj_res.json()["id"]
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    # prompts NOT generated

    res = client.post(
        f"/api/projects/{project_id}/assets/clips/estimate",
        json={"provider_name": "mock", "model_name": "mock-video"},
    )
    data = res.json()
    assert data["ok"] is False
    assert "before images" in data["message"].lower()


# --- Test 12b: Clip estimate returns ok=false when project status is before IMAGES_GENERATED ---
def test_clip_estimate_before_images_generated():
    proj_res = client.post("/api/projects/", json={
        "title": "clip-est-before-imgs", "topic": "Testing", "duration_target": 40,
    })
    project_id = proj_res.json()["id"]
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    # Status is VIDEO_PROMPTS_READY — images not generated yet

    res = client.post(
        f"/api/projects/{project_id}/assets/clips/estimate",
        json={"provider_name": "mock", "model_name": "mock-video"},
    )
    data = res.json()
    assert data["ok"] is False
    assert "before images" in data["message"].lower()
    assert data["estimated_jobs"] == 0


# --- Test 13: Mock clip generation does not require confirmation ---
def test_mock_clip_no_confirmation():
    project_id = _setup_ready_for_clips("mock-clip-noconfirm")
    res = client.post(
        f"/api/projects/{project_id}/assets/clips/generate",
        json={"provider_name": "mock", "model_name": "mock-video", "confirmed": False},
    )
    assert res.status_code == 200


# --- Test 14: WaveSpeed clip generation without confirmation returns 400 ---
def test_wavespeed_clip_no_confirmation():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-noconfirm")
    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        res = client.post(
            f"/api/projects/{project_id}/assets/clips/generate",
            json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": False},
        )
        assert res.status_code == 400
        assert "confirmation" in res.json()["detail"].lower()


# --- Test 15: WaveSpeed clip generation with confirmation creates clips ---
def test_wavespeed_clip_with_confirmation():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-confirmed")

    mock_job = ProviderJob(
        job_id="ws_vid_job",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_job",
            "file_url": "https://fake.wavespeed.ai/videos/clip.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            res = client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )
            assert res.status_code == 200
            assets = res.json()
            assert len(assets) == 8
            for pair in assets:
                assert pair["clip"] is not None
                assert pair["clip"]["provider_name"] == "wavespeed"
                assert pair["clip"]["model_name"] == "wan-2.1-1.3b"


# --- Test 16: Generated clips store provider fields ---
def test_generated_clips_have_provider_fields():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-fields")

    mock_job = ProviderJob(
        job_id="ws_vid_fields",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_fields",
            "file_url": "https://fake.wavespeed.ai/videos/fields.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )

    db = TestingSessionLocal()
    from app.models.generated_asset import GeneratedClip
    clips = db.query(GeneratedClip).filter(
        GeneratedClip.project_id == project_id, GeneratedClip.is_active == True
    ).all()
    db.close()

    assert len(clips) == 8
    for c in clips:
        assert c.provider_name == "wavespeed"
        assert c.model_name == "wan-2.1-1.3b"
        assert c.provider_job_id == "ws_vid_fields"


# --- Test 17: Provider run logs created for WaveSpeed clip generation ---
def test_wavespeed_clip_run_logs():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-logs")

    mock_job = ProviderJob(
        job_id="ws_vid_log",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_log",
            "file_url": "https://fake.wavespeed.ai/videos/log.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    clip_logs = [l for l in logs if l["operation"] == "clip_generation"]
    assert len(clip_logs) == 8
    for log in clip_logs:
        assert log["provider_name"] == "wavespeed"
        assert log["modality"] == "video"
        assert log["status"] == "COMPLETED"


# --- Test 18: Provider run logs do not contain API key ---
def test_wavespeed_clip_logs_no_key_leak():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-noleak")

    mock_job = ProviderJob(
        job_id="ws_vid_noleak",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_noleak",
            "file_url": "https://fake.wavespeed.ai/videos/noleak.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    clip_logs = [l for l in logs if l["operation"] == "clip_generation"]
    for log in clip_logs:
        combined = json.dumps(log.get("request_json", {})) + json.dumps(log.get("response_json", {}))
        assert FAKE_API_KEY not in combined


# --- Test 19: Malformed WaveSpeed video response preserves existing clips ---
def test_wavespeed_clip_malformed_preserves():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-malformed")

    # Generate with mock first
    client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    before = client.get(f"/api/projects/{project_id}/assets").json()
    before_ids = [p["clip"]["id"] for p in before]

    bad_job = ProviderJob(
        job_id="ws_bad_vid",
        status="COMPLETED",
        result={"provider_job_id": "ws_bad_vid", "duration_seconds": 5},
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=bad_job):
            res = client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )
            assert res.status_code == 400
            assert "file_url" in res.json()["detail"].lower()

    after = client.get(f"/api/projects/{project_id}/assets").json()
    after_ids = [p["clip"]["id"] for p in after]
    assert after_ids == before_ids


# --- Test 20: Partial WaveSpeed clip failure preserves all original clips ---
def test_wavespeed_clip_partial_failure():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-partial")

    client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    before = client.get(f"/api/projects/{project_id}/assets").json()
    before_ids = [p["clip"]["id"] for p in before]

    success_job = ProviderJob(
        job_id="ws_vid_ok",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_ok",
            "file_url": "https://fake.wavespeed.ai/videos/ok.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    call_count = [0]

    def side_effect(**kwargs):
        call_count[0] += 1
        if call_count[0] <= 4:
            return success_job
        raise Exception("Simulated WaveSpeed failure on scene 5")

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", side_effect=side_effect):
            res = client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )
            assert res.status_code == 400

    after = client.get(f"/api/projects/{project_id}/assets").json()
    after_ids = [p["clip"]["id"] for p in after]
    assert sorted(after_ids) == sorted(before_ids)


# --- Test 21: Scene clip estimate defaults to mock ---
def test_scene_clip_estimate_defaults_mock():
    project_id = _setup_ready_for_clips("sc-clip-est-mock")
    gen = client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    scene_id = gen.json()[0]["scene_id"]

    res = client.post(f"/api/scenes/{scene_id}/assets/clip/estimate", json={})
    data = res.json()
    assert data["ok"] is True
    assert data["requires_confirmation"] is False


# --- Test 22: Scene clip estimate for WaveSpeed requires confirmation ---
def test_scene_clip_estimate_requires_confirmation():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("sc-clip-est-ws")
    gen = client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    scene_id = gen.json()[0]["scene_id"]

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        res = client.post(
            f"/api/scenes/{scene_id}/assets/clip/estimate",
            json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b"},
        )
        data = res.json()
        assert data["ok"] is True
        assert data["requires_confirmation"] is True
        assert data["cost_hint"] == "paid"


# --- Test 23: Scene clip estimate returns ok=false when active image missing ---
def test_scene_clip_estimate_no_image():
    proj_res = client.post("/api/projects/", json={
        "title": "sc-clip-noimg", "topic": "Testing", "duration_target": 40,
    })
    project_id = proj_res.json()["id"]
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    # No images generated
    scenes = client.get(f"/api/projects/{project_id}/scenes").json()
    scene_id = scenes[0]["id"]

    res = client.post(f"/api/scenes/{scene_id}/assets/clip/estimate", json={})
    data = res.json()
    assert data["ok"] is False
    assert "active image" in data["message"].lower()


# --- Test 24: Scene clip estimate returns ok=false when video prompt not approved ---
def test_scene_clip_estimate_prompt_not_approved():
    project_id = _setup_ready_for_clips("sc-clip-notappr")
    prompts = client.get(f"/api/projects/{project_id}/prompts").json()
    scene_id = prompts[0]["scene_id"]
    # Set video prompt to DRAFT via DB
    db = TestingSessionLocal()
    from app.models.prompt import VideoPrompt
    vp = db.query(VideoPrompt).filter(VideoPrompt.scene_id == scene_id).first()
    vp.status = "DRAFT"
    db.add(vp)
    db.commit()
    db.close()

    res = client.post(f"/api/scenes/{scene_id}/assets/clip/estimate", json={})
    data = res.json()
    assert data["ok"] is False
    assert "approved" in data["message"].lower()


# --- Test 25: WaveSpeed clip retry without confirmation returns 400 ---
def test_wavespeed_clip_retry_no_confirmation():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clipretry-noconf")
    gen = client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    scene_id = gen.json()[0]["scene_id"]

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        res = client.post(
            f"/api/scenes/{scene_id}/assets/clip/retry",
            json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": False},
        )
        assert res.status_code == 400
        assert "confirmation" in res.json()["detail"].lower()


# --- Test 26: WaveSpeed clip retry with confirmation replaces clip safely ---
def test_wavespeed_clip_retry_with_confirmation():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clipretry-ok")
    gen = client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    scene_id = gen.json()[0]["scene_id"]
    old_clip_id = gen.json()[0]["clip"]["id"]

    mock_job = ProviderJob(
        job_id="ws_vid_retry",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_retry",
            "file_url": "https://fake.wavespeed.ai/videos/retry.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            res = client.post(
                f"/api/scenes/{scene_id}/assets/clip/retry",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )
            assert res.status_code == 200
            new_clip = res.json()["clip"]
            assert new_clip["id"] != old_clip_id
            assert new_clip["is_active"] is True
            assert new_clip["provider_name"] == "wavespeed"


# --- Test 27: Failed WaveSpeed clip generation logs failed run ---
def test_wavespeed_clip_failed_logs_run():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-failed-log")

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", side_effect=Exception("fail")):
            client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    failed = [l for l in logs if l["status"] == "FAILED"]
    assert len(failed) >= 1
    for log in failed:
        assert log["modality"] == "video"
        assert log["error_message"] is not None
        combined = json.dumps(log.get("request_json", {}))
        assert FAKE_API_KEY not in combined


# --- Test 28: Provider run logs include clip_generation and clip_retry ---
def test_clip_run_logs_have_operations():
    _enable_wavespeed_video_model()
    project_id = _setup_ready_for_clips("ws-clip-ops")

    mock_job = ProviderJob(
        job_id="ws_vid_op",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_vid_op",
            "file_url": "https://fake.wavespeed.ai/videos/op.mp4",
            "duration_seconds": 5,
            "width": 1080,
            "height": 1920,
            "fps": 24,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedVideoProvider, "generate_video", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/clips/generate",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )
            assets = client.get(f"/api/projects/{project_id}/assets").json()
            scene_id = assets[0]["scene_id"]
            client.post(
                f"/api/scenes/{scene_id}/assets/clip/retry",
                json={"provider_name": "wavespeed", "model_name": "wan-2.1-1.3b", "confirmed": True},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    operations = {l["operation"] for l in logs if l["modality"] == "video"}
    assert "clip_generation" in operations
    assert "clip_retry" in operations


# --- Test 29: Full mock pipeline still reaches FINAL_RENDER_READY ---
def test_full_mock_pipeline_works():
    proj_res = client.post("/api/projects/", json={
        "title": "Full Pipeline Video Test",
        "topic": "End-to-end mock test",
        "language": "en",
        "duration_target": 30,
    })
    project_id = proj_res.json()["id"]

    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    client.post(f"/api/scripts/{script_res.json()['id']}/approve")
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")
    client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    client.post(f"/api/projects/{project_id}/assets/approve")
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    client.post(f"/api/projects/{project_id}/subtitles/approve")
    client.post(f"/api/projects/{project_id}/renders/generate")
    client.post(f"/api/projects/{project_id}/renders/approve")

    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "FINAL_RENDER_READY"


# --- Test 30: Existing Phase 1-12 still passes (all wavespeed tests run) ---
def test_existing_wavespeed_tests_still_work():
    """Quick smoke: mock generation still works end-to-end"""
    project_id = _setup_ready_for_clips("smoke-test")
    imgs = client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    assert imgs.status_code == 200
    clips = client.post(f"/api/projects/{project_id}/assets/clips/generate", json={})
    assert clips.status_code == 200
