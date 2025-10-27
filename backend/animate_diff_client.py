"""Client for coordinating AnimateDiff or video-diffusion backends."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class AnimateDiffResult:
    """Container describing an AnimateDiff motion clip."""

    frames: List[Image.Image]
    fps: int
    metadata: Dict[str, Any]


class AnimateDiffClient:
    """Async-friendly helper that talks to an AnimateDiff (or WAN/Pika) service."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.enabled = config.get("enabled", False)
        self.endpoint = config.get("endpoint")
        self.health_endpoint = config.get("health_endpoint")
        self.default_fps = int(config.get("default_fps", 12))
        self.timeout = int(config.get("timeout", 480))
        self.extra_payload = config.get("extra_payload", {})

        if self.enabled and not self.endpoint:
            logger.warning("AnimateDiff pipeline enabled but no endpoint configured; disabling")
            self.enabled = False

    @property
    def available(self) -> bool:
        return self.enabled and bool(self.endpoint)

    async def is_available(self) -> bool:
        """Ping remote service if health endpoint provided."""

        if not self.available:
            return False

        if not self.health_endpoint:
            return True

        loop = asyncio.get_event_loop()

        def _check() -> bool:
            try:
                response = requests.get(self.health_endpoint, timeout=10)
                return response.status_code == 200
            except Exception as exc:  # pragma: no cover - network failure
                logger.debug("AnimateDiff health check failed: %s", exc)
                return False

        return await loop.run_in_executor(None, _check)

    async def generate_motion_clip(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        reference_image: Optional[Image.Image] = None,
        seed: int = -1,
        steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        frame_count: Optional[int] = None,
        fps: Optional[int] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> AnimateDiffResult:
        """Request a motion clip from the remote AnimateDiff backend."""

        if not self.available:
            raise RuntimeError("AnimateDiff client is not configured")

        payload: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "seed": seed,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "frame_count": frame_count,
            "fps": fps or self.default_fps,
        }

        payload.update(self.extra_payload)

        if extras:
            payload.update(extras)

        if reference_image is not None:
            payload["reference"] = self._image_to_base64(reference_image)

        loop = asyncio.get_event_loop()

        def _request() -> Dict[str, Any]:
            response = requests.post(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"AnimateDiff request failed: {response.status_code} {response.text}"
                )
            return response.json()

        raw = await loop.run_in_executor(None, _request)

        frames: List[Image.Image] = []
        raw_frames = raw.get("frames") or raw.get("images") or []

        for item in raw_frames:
            image_data = None
            if isinstance(item, str):
                image_data = item
            elif isinstance(item, dict):
                image_data = item.get("image") or item.get("data")

            if not image_data:
                continue

            try:
                frames.append(self._decode_image(image_data))
            except Exception as exc:  # pragma: no cover - bad payload
                logger.warning("Failed to decode AnimateDiff frame: %s", exc)

        metadata = raw.get("metadata", {})
        fps_value = int(raw.get("fps", payload.get("fps", self.default_fps)))

        if not frames:
            raise RuntimeError("AnimateDiff request returned no frames")

        return AnimateDiffResult(frames=frames, fps=fps_value, metadata=metadata)

    @staticmethod
    def _image_to_base64(image: Image.Image) -> str:
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    @staticmethod
    def _decode_image(data: str) -> Image.Image:
        decoded = base64.b64decode(data)
        return Image.open(io.BytesIO(decoded)).convert("RGBA")


