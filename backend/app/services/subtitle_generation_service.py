import json
import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.video_project import VideoProject
from app.models.scene import Scene
from app.models.audio import Voiceover
from app.schemas.subtitle_schema import SubtitleSegmentCreate
from app.schemas.provider_schema import (
    ProviderRunLogCreate,
    SubtitleGenerationEstimateResponse,
)
from app.services import provider_registry, provider_run_service, provider_preflight_service


def _resolve_audio_path(file_url: str) -> Path:
    """Convert a storage file_url to a local filesystem path."""
    # file_url looks like /storage/projects/{project_id}/audio/voiceover_xxx.mp3
    rel = file_url.lstrip("/")
    return Path(rel)


def _require_confirmation_if_paid(db: Session, provider_name: str, model_name: str, confirmed: bool) -> None:
    """Check that paid provider usage is explicitly confirmed for transcription."""
    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "transcription")
    if not model or not model.is_enabled:
        return
    is_paid = model.cost_hint == "paid" or model.is_mock is False
    if is_paid and not confirmed:
        raise HTTPException(status_code=400, detail="Paid provider generation requires explicit confirmation.")


def estimate_subtitle_generation(
    db: Session,
    project: VideoProject,
    voiceover: Voiceover,
    provider_name: str = "mock",
    model_name: str = "mock-transcription",
) -> SubtitleGenerationEstimateResponse:
    """Estimate subtitle generation without calling the provider."""
    # Preflight the provider/model
    preflight = provider_preflight_service.preflight_provider_model(
        db, provider_name, model_name, "transcription"
    )
    if not preflight.ok:
        return SubtitleGenerationEstimateResponse(
            ok=False,
            provider_name=provider_name,
            model_name=model_name,
            voiceover_id=voiceover.id,
            audio_file_url=voiceover.file_url,
            message=preflight.message,
        )

    from app.services import model_catalog_service
    model = model_catalog_service.get_model(db, provider_name, model_name, "transcription")
    cost_hint = model.cost_hint if model else "mock-free"
    requires_confirmation = (cost_hint == "paid" or (model and model.is_mock is False))

    return SubtitleGenerationEstimateResponse(
        ok=True,
        provider_name=provider_name,
        model_name=model_name,
        voiceover_id=voiceover.id,
        audio_file_url=voiceover.file_url,
        estimated_jobs=1,
        cost_hint=cost_hint or "unknown",
        requires_confirmation=requires_confirmation,
        message=f"Ready to generate subtitles with {provider_name} {model_name}."
        if preflight.ok
        else preflight.message,
    )


def _segments_from_provider_result(result: dict, project_id: int, voiceover_id: int) -> List[SubtitleSegmentCreate]:
    """Normalize provider segments into SubtitleSegmentCreate rows."""
    segments_raw = result.get("segments", [])
    if not segments_raw:
        return []

    cleaned = []
    for seg in segments_raw:
        start = max(0.0, float(seg.get("start", 0)))
        end = float(seg.get("end", 0))
        text = (seg.get("text", "") or "").strip()
        if not text:
            continue
        if end <= start:
            continue
        cleaned.append((start, end, text))

    if not cleaned:
        return []

    # Sort by start time
    cleaned.sort(key=lambda x: x[0])

    return [
        SubtitleSegmentCreate(
            project_id=project_id,
            voiceover_id=voiceover_id,
            index=i,
            start_time=round(start, 2),
            end_time=round(end, 2),
            text=text,
            style="bold_white_black_stroke",
            status="DRAFT",
        )
        for i, (start, end, text) in enumerate(cleaned)
    ]


def generate_subtitles(
    db: Session,
    project: VideoProject,
    voiceover: Voiceover,
    scenes: List[Scene],
    provider_name: str = "mock",
    model_name: str = "mock-transcription",
    operation: str = "subtitle_generation",
) -> List[SubtitleSegmentCreate]:
    """
    Dispatcher: generate subtitles via mock or real provider.

    For mock: keeps current deterministic subtitle generation from scenes.
    For OpenAI: preflight → resolve audio path → transcribe → normalize segments.
    """
    provider_preflight_service.require_provider_model(db, provider_name, model_name, "transcription")

    if provider_name == "mock":
        return generate_mock_subtitles(project, voiceover, scenes)

    # --- OpenAI / non-mock transcription ---
    provider = provider_registry.get_provider(provider_name, "transcription")
    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"No transcription provider adapter registered for '{provider_name}'.",
        )

    # Resolve audio file path from voiceover file_url
    audio_path = _resolve_audio_path(voiceover.file_url)
    if not audio_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Voiceover audio file not found at: {audio_path}",
        )

    from app.services import model_catalog_service

    model = model_catalog_service.get_model(db, provider_name, model_name, "transcription")
    default_params = {}
    if model and model.default_params_json:
        try:
            default_params = json.loads(model.default_params_json)
        except (json.JSONDecodeError, TypeError):
            pass

    response_format = default_params.get("response_format", "verbose_json")
    timestamp_granularities = default_params.get("timestamp_granularities", ["segment"])

    try:
        job = provider.transcribe_audio(
            audio_file_path=str(audio_path),
            model_name=model_name,
            language=project.language,
            response_format=response_format,
            timestamp_granularities=timestamp_granularities,
        )
    except Exception as e:
        provider_run_service.create_run_log(db, ProviderRunLogCreate(
            project_id=project.id,
            provider_name=provider_name,
            model_name=model_name,
            modality="transcription",
            operation=operation,
            provider_job_id=None,
            status="FAILED",
            error_message=str(e)[:500],
        ))
        raise HTTPException(
            status_code=400,
            detail=f"Subtitle generation failed: {str(e)}",
        )

    result = job.result or {}

    segments = _segments_from_provider_result(result, project.id, voiceover.id)
    if not segments:
        raise HTTPException(
            status_code=400,
            detail="OpenAI transcription returned no valid subtitle segments.",
        )

    provider_run_service.create_run_log(db, ProviderRunLogCreate(
        project_id=project.id,
        provider_name=provider_name,
        model_name=model_name,
        modality="transcription",
        operation=operation,
        provider_job_id=job.job_id,
        request_json={
            "voiceover_id": voiceover.id,
            "audio_file_url": voiceover.file_url,
            "language": project.language,
            "response_format": response_format,
            "timestamp_granularities": timestamp_granularities,
        },
        response_json={
            "provider_job_id": job.job_id,
            "segment_count": len(segments),
            "duration_seconds": result.get("duration_seconds", 0),
        },
    ))

    return segments


def generate_mock_subtitles(project: VideoProject, voiceover: Voiceover, scenes: List[Scene]) -> List[SubtitleSegmentCreate]:
    """
    Generates deterministic subtitle segments from scenes.
    For this MVP, we create one segment per scene using estimated timing.
    """
    segments = []

    if not scenes:
        return segments

    # We estimate segment timing based on equal division of total duration for MVP
    # Or, if scene prompts have durations, we could use them. But scenes don't directly have duration.
    # Let's just divide the voiceover duration equally across scenes.
    duration_per_scene = voiceover.duration_seconds / len(scenes)

    current_time = 0.0

    for i, scene in enumerate(scenes):
        start_time = current_time
        end_time = current_time + duration_per_scene

        # Avoid slight floating point overruns
        if i == len(scenes) - 1:
            end_time = float(voiceover.duration_seconds)

        segment = SubtitleSegmentCreate(
            project_id=project.id,
            voiceover_id=voiceover.id,
            index=i,
            start_time=round(start_time, 2),
            end_time=round(end_time, 2),
            text=scene.narration_text if scene.narration_text else f"Mock subtitle {i+1}",
            style="bold_white_black_stroke",
            status="DRAFT"
        )
        segments.append(segment)

        current_time += duration_per_scene

    return segments
