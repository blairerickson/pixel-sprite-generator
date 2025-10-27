"""Utilities for frame interpolation and smoothing."""

from __future__ import annotations

import logging
from typing import List

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class FrameInterpolator:
    """Fallback CPU-based interpolator for modest frame smoothing."""

    def __init__(self, config: dict | None = None):
        config = config or {}
        self.max_output_frames = config.get("max_output_frames", 32)
        self.interpolation_strength = config.get("interpolation_strength", 0.5)

    def interpolate(self, frames: List[Image.Image], target_count: int) -> List[Image.Image]:
        if not frames:
            return []

        if target_count <= len(frames):
            return frames[:target_count]

        if len(frames) == 1:
            return frames * target_count

        if target_count > self.max_output_frames:
            target_count = self.max_output_frames

        source_count = len(frames)
        interpolated: List[Image.Image] = []

        for idx in range(target_count):
            position = idx * (source_count - 1) / (target_count - 1)
            lower = int(np.floor(position))
            upper = int(np.ceil(position))

            if lower == upper:
                interpolated.append(frames[lower])
                continue

            blend = position - lower
            interpolated.append(self._blend(frames[lower], frames[upper], blend))

        return interpolated

    def _blend(self, image_a: Image.Image, image_b: Image.Image, blend: float) -> Image.Image:
        blend = max(0.0, min(1.0, blend))
        alpha = blend * self.interpolation_strength

        arr_a = np.array(image_a.convert("RGBA"), dtype=np.float32)
        arr_b = np.array(image_b.convert("RGBA"), dtype=np.float32)

        blended = (1.0 - alpha) * arr_a + alpha * arr_b
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        return Image.fromarray(blended, mode="RGBA")


