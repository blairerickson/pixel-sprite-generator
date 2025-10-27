"""Deterministic sprite animation helpers (e.g., breathing cycles)."""

from __future__ import annotations

import math
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image

from sprite_normalizer import NormalizedSprite

logger = logging.getLogger(__name__)


@dataclass
class AnimationFrameInfo:
    """Metadata for a generated animation frame."""

    index: int
    path: Path
    url: str
    offset: Tuple[int, int]
    scale: Tuple[float, float]
    phase: float


@dataclass
class AnimationResult:
    """Container for generated frames and sprite sheets."""

    frames: List[AnimationFrameInfo]
    sprite_sheet_path: Path
    sprite_sheet_url: str
    frame_size: Tuple[int, int]
    frame_count: int
    metadata: Dict[str, Any]


class SpriteAnimator:
    """Generate deterministic pixel animations from normalized sprites."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        animation_cfg = config.get("animation", {})
        generation_cfg = animation_cfg.get("generation", {})
        breathing_cfg = animation_cfg.get("breathing", {})

        self.frame_size = tuple(generation_cfg.get("target_frame_size", (128, 128)))
        self.default_frame_count = breathing_cfg.get("frame_count", 5)
        self.vertical_scale_amplitude = breathing_cfg.get("vertical_scale_amplitude", 0.05)
        self.horizontal_scale_amplitude = breathing_cfg.get("horizontal_scale_amplitude", 0.015)
        self.torso_height_ratio = breathing_cfg.get("torso_height_ratio", 0.55)
        self.sprite_sheet_gap = breathing_cfg.get("sheet_gap", 0)

        self.output_root = Path(config["paths"]["output_dir"])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_breathing_cycle(
        self,
        sprite: NormalizedSprite,
        output_dir: Path,
        frame_count: Optional[int] = None,
    ) -> AnimationResult:
        """Synthesize a looping breathing animation from a normalized sprite."""

        frame_count = frame_count or self.default_frame_count
        if frame_count < 2:
            raise ValueError("Breathing cycle requires at least two frames")

        output_dir.mkdir(parents=True, exist_ok=True)

        base_image = sprite.image.convert("RGBA")
        torso_box = self._compute_torso_box(sprite)
        torso_region = base_image.crop(torso_box)

        frames: List[AnimationFrameInfo] = []
        frame_images: List[Image.Image] = []

        for frame_index in range(frame_count):
            phase = frame_index / frame_count
            eased = 0.5 - 0.5 * math.cos(phase * math.tau)

            scale_x, scale_y = self._compute_scales(eased)

            transformed_torso = self._scale_torso(torso_region, scale_x, scale_y)
            frame_image = self._compose_frame(
                base_image,
                torso_box,
                transformed_torso,
                scale_x,
                scale_y,
            )

            frame_filename = f"frame_{frame_index:02d}.png"
            frame_path = output_dir / frame_filename
            frame_image.save(frame_path)
            frame_images.append(frame_image)

            frames.append(
                AnimationFrameInfo(
                    index=frame_index,
                    path=frame_path,
                    url=f"/output/{output_dir.name}/{frame_filename}",
                    offset=(0, 0),
                    scale=(scale_x, scale_y),
                    phase=phase,
                )
            )

        sheet_path = self._compose_sprite_sheet(output_dir, frame_images)

        metadata = {
            "cycle": "breathing",
            "frame_count": frame_count,
            "vertical_scale_amplitude": self.vertical_scale_amplitude,
            "horizontal_scale_amplitude": self.horizontal_scale_amplitude,
            "torso_box": torso_box,
            "source": sprite.metadata,
        }

        animation_result = AnimationResult(
            frames=frames,
            sprite_sheet_path=sheet_path,
            sprite_sheet_url=f"/output/{output_dir.name}/{sheet_path.name}",
            frame_size=self.frame_size,
            frame_count=frame_count,
            metadata=metadata,
        )

        metadata_path = output_dir / "metadata.json"
        try:
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - best effort write
            logger.warning("Failed to write animation metadata: %s", exc)

        return animation_result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_torso_box(self, sprite: NormalizedSprite) -> Tuple[int, int, int, int]:
        left, top, right, bottom = sprite.content_bounds
        height = bottom - top
        torso_height = max(1, int(height * self.torso_height_ratio))
        torso_top = top
        torso_bottom = min(bottom, torso_top + torso_height)
        return (left, torso_top, right, torso_bottom)

    def _compute_scales(self, eased_phase: float) -> Tuple[float, float]:
        vertical_scale = 1.0 + self.vertical_scale_amplitude * math.sin(eased_phase * math.pi)
        horizontal_scale = 1.0 - self.horizontal_scale_amplitude * math.sin(eased_phase * math.pi)
        return horizontal_scale, vertical_scale

    def _scale_torso(
        self,
        torso: Image.Image,
        scale_x: float,
        scale_y: float,
    ) -> Image.Image:
        width, height = torso.size
        new_width = max(1, int(round(width * scale_x)))
        new_height = max(1, int(round(height * scale_y)))
        if new_width == width and new_height == height:
            return torso
        return torso.resize((new_width, new_height), Image.Resampling.NEAREST)

    def _compose_frame(
        self,
        base_image: Image.Image,
        torso_box: Tuple[int, int, int, int],
        transformed_torso: Image.Image,
        scale_x: float,
        scale_y: float,
    ) -> Image.Image:
        frame = base_image.copy()

        torso_width = torso_box[2] - torso_box[0]
        torso_height = torso_box[3] - torso_box[1]
        new_width, new_height = transformed_torso.size

        # Clear original torso region
        blank = Image.new("RGBA", (torso_width, torso_height), (0, 0, 0, 0))
        frame.paste(blank, (torso_box[0], torso_box[1]))

        bottom_y = torso_box[3]
        left_x = torso_box[0]

        offset_x = left_x + (torso_width - new_width) // 2
        offset_y = bottom_y - new_height

        frame.paste(transformed_torso, (offset_x, offset_y), transformed_torso)

        return frame

    def _compose_sprite_sheet(
        self,
        output_dir: Path,
        frames: List[Image.Image],
    ) -> Path:
        if not frames:
            raise ValueError("No frames generated for sprite sheet")

        frame_width, frame_height = frames[0].size
        gap = self.sprite_sheet_gap
        sheet_width = frame_width * len(frames) + gap * (len(frames) - 1)
        sheet_height = frame_height

        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

        x = 0
        for img in frames:
            sheet.paste(img, (x, 0), img)
            x += frame_width + gap

        sheet_path = output_dir / "breathing_sheet.png"
        sheet.save(sheet_path)
        return sheet_path


__all__ = [
    "SpriteAnimator",
    "NormalizedSprite",
    "AnimationFrameInfo",
    "AnimationResult",
]


