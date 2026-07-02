import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.provider import ProviderModel
from app.providers.wavespeed_provider import WavespeedImageProvider, ProviderJob

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


def _get_wavespeed_model_id():
    models = client.get("/api/providers/models").json()
    for m in models:
        if m["provider_name"] == "wavespeed" and m["modality"] == "image":
            return m["id"]
    return None


def _enable_wavespeed_model():
    model_id = _get_wavespeed_model_id()
    if model_id:
        client.post(f"/api/providers/models/{model_id}/enable")


# --- Test 1: WaveSpeed image model is seeded disabled by default ---
def test_wavespeed_model_seeded_disabled():
    models = client.get("/api/providers/models").json()
    ws_models = [m for m in models if m["provider_name"] == "wavespeed" and m["modality"] == "image"]
    assert len(ws_models) == 1
    assert ws_models[0]["is_enabled"] is False
    assert ws_models[0]["is_mock"] is False
    assert ws_models[0]["cost_hint"] == "paid"


# --- Test 2: WaveSpeed does not appear in enabled image models by default ---
def test_wavespeed_not_in_enabled_models_by_default():
    enabled = client.get("/api/providers/models/enabled").json()
    image_models = [m for m in enabled if m["modality"] == "image"]
    ws_models = [m for m in image_models if m["provider_name"] == "wavespeed"]
    assert len(ws_models) == 0
    # mock-image should be present
    mock_models = [m for m in image_models if m["provider_name"] == "mock"]
    assert len(mock_models) >= 1


# --- Test 3: WaveSpeed preflight fails when disabled ---
def test_wavespeed_preflight_fails_when_disabled():
    payload = {
        "provider_name": "wavespeed",
        "model_name": "flux-schnell",
        "modality": "image",
    }
    res = client.post("/api/providers/preflight", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert "disabled" in data["message"]


# --- Test 4: WaveSpeed preflight fails when enabled but API key missing ---
def test_wavespeed_preflight_fails_without_api_key():
    _enable_wavespeed_model()

    # Ensure no API key in env
    with patch.dict(os.environ, {}, clear=True):
        payload = {
            "provider_name": "wavespeed",
            "model_name": "flux-schnell",
            "modality": "image",
        }
        res = client.post("/api/providers/preflight", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is False
        assert "WAVESPEED_API_KEY" in data["message"]


# --- Test 5: WaveSpeed preflight passes when enabled and API key present ---
def test_wavespeed_preflight_passes_with_api_key():
    _enable_wavespeed_model()

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        payload = {
            "provider_name": "wavespeed",
            "model_name": "flux-schnell",
            "modality": "image",
        }
        res = client.post("/api/providers/preflight", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True


# --- Test 6: Mock image generation remains default ---
def test_mock_image_generation_default():
    project_id = _setup_approved_prompts_setup("mock-default-imgs")

    # Call without provider selection
    res = client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    assert res.status_code == 200
    assets = res.json()
    assert len(assets) == 8
    for pair in assets:
        assert pair["image"] is not None
        assert pair["image"]["provider_name"] == "mock"
        assert pair["image"]["model_name"] == "mock-image"


# --- Test 7: Image generation with WaveSpeed disabled returns 400 ---
def test_image_generation_wavespeed_disabled_rejects():
    project_id = _setup_approved_prompts_setup("ws-disabled-reject")

    res = client.post(
        f"/api/projects/{project_id}/assets/images/generate",
        json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
    )
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "disabled" in detail.lower()


# --- Test 8: Image generation with mocked WaveSpeed creates records ---
def test_wavespeed_image_generation_mocked():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-mocked-gen")

    mock_job = ProviderJob(
        job_id="ws_fake_job_001",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_fake_job_001",
            "file_url": "https://fake.wavespeed.ai/images/gen_001.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/gen_001_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {"id": "ws_fake_job_001", "status": "COMPLETED"},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(
            WavespeedImageProvider, "generate_image", return_value=mock_job
        ):
            res = client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 200
            assets = res.json()
            assert len(assets) == 8

            for pair in assets:
                img = pair["image"]
                assert img is not None
                assert img["provider_name"] == "wavespeed"
                assert img["model_name"] == "flux-schnell"
                assert img["provider_job_id"] == "ws_fake_job_001"
                assert img["file_url"] == "https://fake.wavespeed.ai/images/gen_001.png"
                assert img["thumbnail_url"] == "https://fake.wavespeed.ai/images/gen_001_thumb.png"
                assert img["is_active"] is True


# --- Test 9: Generated images store provider/model/url/job_id ---
def test_generated_images_have_provider_fields():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-provider-fields")

    mock_job = ProviderJob(
        job_id="ws_fake_job_fields",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_fake_job_fields",
            "file_url": "https://fake.wavespeed.ai/images/fields_test.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/fields_test_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedImageProvider, "generate_image", return_value=mock_job):
            res = client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 200

            # Verify stored via direct model query
            db = TestingSessionLocal()
            from app.models.generated_asset import GeneratedImage
            imgs = db.query(GeneratedImage).filter(
                GeneratedImage.project_id == project_id,
                GeneratedImage.is_active == True,
            ).all()
            db.close()

            assert len(imgs) == 8
            for img in imgs:
                assert img.provider_name == "wavespeed"
                assert img.model_name == "flux-schnell"
                assert img.provider_job_id == "ws_fake_job_fields"
                assert img.file_url == "https://fake.wavespeed.ai/images/fields_test.png"
                assert img.thumbnail_url == "https://fake.wavespeed.ai/images/fields_test_thumb.png"


# --- Test 10: Provider run logs created for WaveSpeed image generation ---
def test_wavespeed_run_logs_created():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-run-logs")

    mock_job = ProviderJob(
        job_id="ws_fake_runlog",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_fake_runlog",
            "file_url": "https://fake.wavespeed.ai/images/runlog.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/runlog_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedImageProvider, "generate_image", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    image_logs = [l for l in logs if l["operation"] == "image_generation"]
    assert len(image_logs) == 8  # One per scene
    for log in image_logs:
        assert log["provider_name"] == "wavespeed"
        assert log["model_name"] == "flux-schnell"
        assert log["modality"] == "image"
        assert log["status"] == "COMPLETED"
        assert log["project_id"] == project_id
        assert log["scene_id"] is not None


# --- Test 11: Provider run logs do not contain API key ---
def test_wavespeed_run_logs_no_api_key_exposure():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-no-key-leak")

    mock_job = ProviderJob(
        job_id="ws_fake_noleak",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_fake_noleak",
            "file_url": "https://fake.wavespeed.ai/images/noleak.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/noleak_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedImageProvider, "generate_image", return_value=mock_job):
            client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )

    logs = client.get(f"/api/projects/{project_id}/provider-runs").json()
    image_logs = [l for l in logs if l["operation"] == "image_generation"]
    for log in image_logs:
        req_str = json.dumps(log.get("request_json", {}))
        resp_str = json.dumps(log.get("response_json", {}))
        combined = req_str + resp_str
        assert FAKE_API_KEY not in combined, f"API key leaked in log: {log}"
        assert "WAVESPEED_API_KEY" not in combined, f"API key env var name leaked in log: {log}"


# --- Test 12: Malformed WaveSpeed response returns 400, keeps existing images intact ---
def test_wavespeed_malformed_response_preserves_existing():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-malformed")

    # First, generate with mock to get existing active images
    client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    before_assets = client.get(f"/api/projects/{project_id}/assets").json()
    before_image_ids = [p["image"]["id"] for p in before_assets]
    assert len(before_image_ids) == 8

    # Now try with malformed WaveSpeed response (missing file_url)
    bad_job = ProviderJob(
        job_id="ws_bad",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_bad",
            "thumbnail_url": "https://fake.wavespeed.ai/images/thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedImageProvider, "generate_image", return_value=bad_job):
            res = client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 400
            assert "file_url" in res.json()["detail"].lower()

    # Existing active images should still be intact
    after_assets = client.get(f"/api/projects/{project_id}/assets").json()
    after_image_ids = [p["image"]["id"] for p in after_assets]
    assert after_image_ids == before_image_ids


# --- Test 13: Scene image retry creates new active only after valid response ---
def test_scene_retry_wavespeed_new_active_after_valid():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-retry")

    # Generate with mock first
    gen = client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    scene_id = gen.json()[0]["scene_id"]
    old_img_id = gen.json()[0]["image"]["id"]

    mock_job = ProviderJob(
        job_id="ws_retry_001",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_retry_001",
            "file_url": "https://fake.wavespeed.ai/images/retry.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/retry_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(WavespeedImageProvider, "generate_image", return_value=mock_job):
            res = client.post(
                f"/api/scenes/{scene_id}/assets/image/retry",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 200
            new_img = res.json()["image"]
            assert new_img["id"] != old_img_id
            assert new_img["is_active"] is True
            assert new_img["provider_name"] == "wavespeed"

            # Old image should be inactive
            list_res = client.get(f"/api/projects/{project_id}/assets")
            pair = next(p for p in list_res.json() if p["scene_id"] == scene_id)
            assert pair["image"]["id"] == new_img["id"]


# --- Test 14: Failed WaveSpeed retry keeps old active image intact ---
def test_retry_wavespeed_failure_keeps_old_active():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-retry-fail")

    # Generate with mock first
    gen = client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    scene_id = gen.json()[0]["scene_id"]
    old_img_id = gen.json()[0]["image"]["id"]

    # Simulate a provider failure (raise exception)
    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(
            WavespeedImageProvider,
            "generate_image",
            side_effect=Exception("Simulated WaveSpeed failure"),
        ):
            res = client.post(
                f"/api/scenes/{scene_id}/assets/image/retry",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 400

    # Old image should still be active
    list_res = client.get(f"/api/projects/{project_id}/assets")
    pair = next(p for p in list_res.json() if p["scene_id"] == scene_id)
    assert pair["image"]["id"] == old_img_id
    assert pair["image"]["is_active"] is True


# --- Test 15: Full mock pipeline still reaches FINAL_RENDER_READY ---
def test_full_mock_pipeline_still_works():
    proj_res = client.post("/api/projects/", json={
        "title": "Full Pipeline Test",
        "topic": "End-to-end mock test",
        "language": "en",
        "duration_target": 30,
    })
    project_id = proj_res.json()["id"]

    # Script
    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")

    # Scenes
    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")

    # Prompts
    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")

    # Images
    client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    # Clips
    client.post(f"/api/projects/{project_id}/assets/clips/generate")
    # Approve assets
    client.post(f"/api/projects/{project_id}/assets/approve")

    # Audio
    client.post(f"/api/projects/{project_id}/audio/voiceover/generate")
    # Subtitles
    client.post(f"/api/projects/{project_id}/subtitles/generate")
    client.post(f"/api/projects/{project_id}/subtitles/approve")

    # Final render
    client.post(f"/api/projects/{project_id}/renders/generate")
    client.post(f"/api/projects/{project_id}/renders/approve")

    proj = client.get(f"/api/projects/{project_id}").json()
    assert proj["status"] == "FINAL_RENDER_READY"


# --- Test 16: Partial failure in project-wide generation preserves all original images ---
def test_partial_failure_keeps_all_original_images():
    _enable_wavespeed_model()
    project_id = _setup_approved_prompts_setup("ws-partial-fail")

    # First, generate with mock to get existing active images
    client.post(f"/api/projects/{project_id}/assets/images/generate", json={})
    before_assets = client.get(f"/api/projects/{project_id}/assets").json()
    before_image_ids = [p["image"]["id"] for p in before_assets]
    assert len(before_image_ids) == 8

    # Create a mock that succeeds 4 times then fails
    success_job = ProviderJob(
        job_id="ws_ok",
        status="COMPLETED",
        result={
            "provider_job_id": "ws_ok",
            "file_url": "https://fake.wavespeed.ai/images/ok.png",
            "thumbnail_url": "https://fake.wavespeed.ai/images/ok_thumb.png",
            "width": 1080,
            "height": 1920,
            "status": "COMPLETED",
            "raw_response": {},
        },
    )

    call_count = [0]

    def side_effect(prompt, aspect_ratio, model_name, negative_prompt=None, default_params=None):
        call_count[0] += 1
        if call_count[0] <= 4:
            return success_job
        raise Exception("Simulated WaveSpeed failure on scene 5")

    with patch.dict(os.environ, {"WAVESPEED_API_KEY": FAKE_API_KEY}):
        with patch.object(
            WavespeedImageProvider, "generate_image", side_effect=side_effect
        ):
            res = client.post(
                f"/api/projects/{project_id}/assets/images/generate",
                json={"provider_name": "wavespeed", "model_name": "flux-schnell"},
            )
            assert res.status_code == 400

    # All original active image IDs must remain unchanged
    after_assets = client.get(f"/api/projects/{project_id}/assets").json()
    after_image_ids = [p["image"]["id"] for p in after_assets]
    assert sorted(after_image_ids) == sorted(before_image_ids)


# --- Helpers ---

def _setup_approved_prompts_setup(proj_title):
    proj_res = client.post("/api/projects/", json={
        "title": proj_title,
        "topic": "Testing WaveSpeed",
        "duration_target": 40,
    })
    project_id = proj_res.json()["id"]

    script_res = client.post(f"/api/projects/{project_id}/scripts/generate", json={})
    script_id = script_res.json()["id"]
    client.post(f"/api/scripts/{script_id}/approve")

    client.post(f"/api/projects/{project_id}/scenes/generate")
    client.post(f"/api/projects/{project_id}/scenes/approve")

    client.post(f"/api/projects/{project_id}/prompts/generate")
    client.post(f"/api/projects/{project_id}/prompts/approve")

    return project_id
