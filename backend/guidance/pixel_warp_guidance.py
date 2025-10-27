"""Guidance method that reuses existing sprites via deterministic warping."""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from animation_models import (
    AnimationType,
    Direction,
    AnimationGuidanceMethod,
    AnimationFrame,
    GuidanceCapabilities,
)
from .base_guidance import BaseGuidance

logger = logging.getLogger(__name__)


class PixelWarpGuidance(BaseGuidance):
    """Guidance path that uses the sprite animator instead of new SD renders."""

    def __init__(self, sd_client, config, sprite_normalizer=None, sprite_animator=None, jobs_store=None):
        super().__init__(sd_client, config)
        self.sprite_normalizer = sprite_normalizer
        self.sprite_animator = sprite_animator
        self.jobs_store = jobs_store

    # ------------------------------------------------------------------
    # BaseGuidance overrides
    # ------------------------------------------------------------------

    def get_guidance_method(self) -> AnimationGuidanceMethod:
        return AnimationGuidanceMethod.PIXEL_WARP

    def get_capabilities(self) -> GuidanceCapabilities:
        available = self.sprite_normalizer is not None and self.sprite_animator is not None
        return GuidanceCapabilities(
            method=AnimationGuidanceMethod.PIXEL_WARP,
            available=available,
            quality_rating=0.8,
            speed_rating=0.9,
            consistency_rating=0.95,
            notes="Reuses generated sprite through deterministic warping",
        )

    async def generate_frame(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        reference_image=None,
        template_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[Optional[Any], Dict[str, Any]]:
        raise NotImplementedError("PixelWarpGuidance does not generate single frames directly")

    async def generate_animation_sequence(
        self,
        character_description: str,
        animation_type: AnimationType,
        directions: List[Direction],
        reference_images: Optional[Dict[Direction, Any]] = None,
        frame_count: Optional[int] = None,
        **kwargs,
    ) -> List[AnimationFrame]:
        if not self.get_capabilities().available:
            raise RuntimeError("PixelWarp guidance is unavailable without sprite normalizer/animator")

        if animation_type != AnimationType.IDLE:
            raise ValueError("PixelWarp guidance currently supports idle/breathing animations only")

        source_job_id = kwargs.get("source_job_id")
        if not source_job_id:
            raise ValueError("PixelWarp guidance requires a source job id")

        jobs_store = self.jobs_store or kwargs.get("jobs_store")
        if jobs_store is None or source_job_id not in jobs_store:
            raise ValueError("PixelWarp guidance requires access to existing job data")

        source_job = jobs_store[source_job_id]
        normalized = self.sprite_normalizer.normalize_sprite_from_job(
            source_job,
            use_cleaned=kwargs.get("use_cleaned_sprite", True),
        )

        if not normalized:
            raise RuntimeError("Unable to normalize sprite for PixelWarp guidance")

        output_dir = Path(self.config['paths']['output_dir']) / f"pixelwarp_{source_job_id}"
        animation_result = self.sprite_animator.generate_breathing_cycle(
            normalized,
            output_dir=output_dir,
            frame_count=frame_count,
        )

        frames: List[AnimationFrame] = []
        for frame in animation_result.frames:
            frame_data = AnimationFrame(
                image_url=frame.url,
                direction=Direction.SOUTH,
                frame_index=frame.index,
                animation_type=AnimationType.IDLE,
                seed=-1,
                guidance_method=AnimationGuidanceMethod.PIXEL_WARP,
                quality_score=0.9,
                generation_time=0.0,
                metadata={
                    "phase": frame.phase,
                    "scale": frame.scale,
                    "offset": frame.offset,
                },
            )
            frames.append(frame_data)

        return frames


