import os
import time
import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException
from .base import ImageProvider, VideoProvider, ProviderJob

WAVESPEED_BASE_URL = os.getenv("WAVESPEED_BASE_URL", "https://api.wavespeed.ai/v1")

MAX_POLL_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 120


class WavespeedImageProvider(ImageProvider):
    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        if self._api_key is None:
            key = os.getenv("WAVESPEED_API_KEY")
            if not key:
                raise HTTPException(
                    status_code=400,
                    detail="WAVESPEED_API_KEY is not configured",
                )
            self._api_key = key
        return self._api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str,
        model_name: str = "wavespeed-image-v1",
        negative_prompt: Optional[str] = None,
        default_params: Optional[Dict[str, Any]] = None,
    ) -> ProviderJob:
        api_key = self._get_api_key()
        params: Dict[str, Any] = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "model": model_name,
        }
        if negative_prompt:
            params["negative_prompt"] = negative_prompt
        if default_params:
            for key in ("num_inference_steps", "guidance_scale", "seed", "width", "height"):
                if key in default_params:
                    params[key] = default_params[key]

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                submit_resp = client.post(
                    f"{WAVESPEED_BASE_URL}/images/generations",
                    json=params,
                    headers=self._headers(),
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=502, detail="WaveSpeed request timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"WaveSpeed connection error: {str(e)}")

        if submit_resp.status_code >= 500:
            raise HTTPException(
                status_code=502,
                detail=f"WaveSpeed server error (HTTP {submit_resp.status_code})",
            )

        if submit_resp.status_code >= 400:
            detail = submit_resp.text
            try:
                err_body = submit_resp.json()
                detail = err_body.get("error", err_body.get("message", submit_resp.text))
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"WaveSpeed error: {detail}",
            )

        result = submit_resp.json()

        # If response is synchronous (already has image_url), return immediately
        image_url = result.get("image_url") or result.get("output", {}).get("image_url")
        if image_url:
            return ProviderJob(
                job_id=result.get("id", "unknown"),
                status="COMPLETED",
                result={
                    "provider_job_id": result.get("id", "unknown"),
                    "file_url": image_url,
                    "thumbnail_url": result.get("thumbnail_url") or image_url,
                    "width": result.get("width", 1080),
                    "height": result.get("height", 1920),
                    "status": "COMPLETED",
                    "raw_response": result,
                },
            )

        # Async flow: poll until complete
        job_id = result.get("id") or result.get("job_id")
        if not job_id:
            raise HTTPException(
                status_code=400,
                detail="WaveSpeed returned no job ID for async generation",
            )

        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    poll_resp = client.get(
                        f"{WAVESPEED_BASE_URL}/images/generations/{job_id}",
                        headers=self._headers(),
                    )
            except httpx.TimeoutException:
                raise HTTPException(status_code=502, detail="WaveSpeed poll timed out")
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=502, detail=f"WaveSpeed poll connection error: {str(e)}"
                )

            if poll_resp.status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail=f"WaveSpeed poll server error (HTTP {poll_resp.status_code})",
                )
            if poll_resp.status_code >= 400:
                continue

            poll_result = poll_resp.json()
            status = poll_result.get("status", "").upper()

            if status in ("COMPLETED", "SUCCEEDED", "READY"):
                image_url = poll_result.get("image_url") or poll_result.get("output", {}).get("image_url")
                if not image_url:
                    raise HTTPException(
                        status_code=400,
                        detail="WaveSpeed job completed but no image URL returned",
                    )
                return ProviderJob(
                    job_id=job_id,
                    status="COMPLETED",
                    result={
                        "provider_job_id": job_id,
                        "file_url": image_url,
                        "thumbnail_url": poll_result.get("thumbnail_url") or image_url,
                        "width": poll_result.get("width", 1080),
                        "height": poll_result.get("height", 1920),
                        "status": "COMPLETED",
                        "raw_response": poll_result,
                    },
                )

            if status in ("FAILED", "ERROR", "CANCELLED"):
                err_msg = poll_result.get("error", poll_result.get("message", "Unknown error"))
                raise HTTPException(
                    status_code=400,
                    detail=f"WaveSpeed generation failed: {err_msg}",
                )

        raise HTTPException(
            status_code=504,
            detail=f"WaveSpeed generation timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s",
        )


class WavespeedVideoProvider(VideoProvider):
    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        if self._api_key is None:
            key = os.getenv("WAVESPEED_API_KEY")
            if not key:
                raise HTTPException(
                    status_code=400,
                    detail="WAVESPEED_API_KEY is not configured",
                )
            self._api_key = key
        return self._api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }

    def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: int,
        aspect_ratio: str,
        model_name: str = "wavespeed-video-v1",
        negative_prompt: Optional[str] = None,
        default_params: Optional[Dict[str, Any]] = None,
    ) -> ProviderJob:
        params: Dict[str, Any] = {
            "image_url": image_url,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "model": model_name,
        }
        if negative_prompt:
            params["negative_prompt"] = negative_prompt
        if default_params:
            for key in ("motion_bucket_id", "fps", "seed", "width", "height"):
                if key in default_params:
                    params[key] = default_params[key]

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                submit_resp = client.post(
                    f"{WAVESPEED_BASE_URL}/videos/generations",
                    json=params,
                    headers=self._headers(),
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=502, detail="WaveSpeed request timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"WaveSpeed connection error: {str(e)}")

        if submit_resp.status_code >= 500:
            raise HTTPException(
                status_code=502,
                detail=f"WaveSpeed server error (HTTP {submit_resp.status_code})",
            )

        if submit_resp.status_code >= 400:
            detail = submit_resp.text
            try:
                err_body = submit_resp.json()
                detail = err_body.get("error", err_body.get("message", submit_resp.text))
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"WaveSpeed error: {detail}",
            )

        result = submit_resp.json()

        video_url = result.get("video_url") or result.get("output", {}).get("video_url")
        if video_url:
            return ProviderJob(
                job_id=result.get("id", "unknown"),
                status="COMPLETED",
                result={
                    "provider_job_id": result.get("id", "unknown"),
                    "file_url": video_url,
                    "duration_seconds": result.get("duration", duration),
                    "width": result.get("width", 1080),
                    "height": result.get("height", 1920),
                    "fps": result.get("fps", 24),
                    "status": "COMPLETED",
                    "raw_response": result,
                },
            )

        job_id = result.get("id") or result.get("job_id")
        if not job_id:
            raise HTTPException(
                status_code=400,
                detail="WaveSpeed returned no job ID for async generation",
            )

        for attempt in range(MAX_POLL_ATTEMPTS):
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                    poll_resp = client.get(
                        f"{WAVESPEED_BASE_URL}/videos/generations/{job_id}",
                        headers=self._headers(),
                    )
            except httpx.TimeoutException:
                raise HTTPException(status_code=502, detail="WaveSpeed poll timed out")
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=502, detail=f"WaveSpeed poll connection error: {str(e)}"
                )

            if poll_resp.status_code >= 500:
                raise HTTPException(
                    status_code=502,
                    detail=f"WaveSpeed poll server error (HTTP {poll_resp.status_code})",
                )
            if poll_resp.status_code >= 400:
                continue

            poll_result = poll_resp.json()
            status = poll_result.get("status", "").upper()

            if status in ("COMPLETED", "SUCCEEDED", "READY"):
                video_url = poll_result.get("video_url") or poll_result.get("output", {}).get("video_url")
                if not video_url:
                    raise HTTPException(
                        status_code=400,
                        detail="WaveSpeed job completed but no video URL returned",
                    )
                return ProviderJob(
                    job_id=job_id,
                    status="COMPLETED",
                    result={
                        "provider_job_id": job_id,
                        "file_url": video_url,
                        "duration_seconds": poll_result.get("duration", duration),
                        "width": poll_result.get("width", 1080),
                        "height": poll_result.get("height", 1920),
                        "fps": poll_result.get("fps", 24),
                        "status": "COMPLETED",
                        "raw_response": poll_result,
                    },
                )

            if status in ("FAILED", "ERROR", "CANCELLED"):
                err_msg = poll_result.get("error", poll_result.get("message", "Unknown error"))
                raise HTTPException(
                    status_code=400,
                    detail=f"WaveSpeed video generation failed: {err_msg}",
                )

        raise HTTPException(
            status_code=504,
            detail=f"WaveSpeed generation timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s",
        )
