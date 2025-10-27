"""Sprite normalization utilities for reusable animation inputs."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageChops


@dataclass
class NormalizedSprite:
    """Represents a normalized sprite ready for animation pipelines."""

    image: Image.Image
    source_path: Path
    canvas_size: Tuple[int, int]
    content_bounds: Tuple[int, int, int, int]
    offset: Tuple[int, int]
    scale: float
    metadata: Dict[str, Any]

    def save(self, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(target_path)


class SpriteNormalizer:
    """Utility to locate and normalize sprites for downstream animation."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        animation_cfg = config.get("animation", {})
        generation_cfg = animation_cfg.get("generation", {})
        self.target_frame_size = tuple(
            generation_cfg.get("target_frame_size", (128, 128))
        )
        self.padding = generation_cfg.get("normalization_padding", 8)

    def resolve_primary_sprite(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Select the best sprite candidate from job results."""

        result = job_data.get("result") or {}
        assets = job_data.get("assets") or result.get("assets") or {}

        sprite_entries = assets.get("sprites") or []
        if sprite_entries:
            best = self._select_sprite_entry(sprite_entries)
            return best

        # Fallback to processed images if no extracted sprites
        processed_entries = assets.get("processed_images") or []
        if processed_entries:
            best_processed = processed_entries[0]
            return {
                "path": best_processed.get("path"),
                "filename": best_processed.get("filename"),
                "url": best_processed.get("url"),
                "fallback": True,
            }

        raw_entries = assets.get("raw_images") or []
        if raw_entries:
            return {
                "path": raw_entries[0].get("path"),
                "filename": raw_entries[0].get("filename"),
                "url": raw_entries[0].get("url"),
                "fallback": True,
            }

        return None

    def normalize_sprite_from_job(
        self,
        job_data: Dict[str, Any],
        use_cleaned: bool = True,
    ) -> Optional[NormalizedSprite]:
        """Load and normalize a sprite from job metadata."""

        primary = job_data.get("primary_sprite")
        if not primary:
            primary = self.resolve_primary_sprite(job_data)
            if primary:
                job_data["primary_sprite"] = primary

        if not primary:
            return None

        source_path = None
        if use_cleaned:
            cleaned_images = (job_data.get("result") or {}).get("cleaned_images") or []
            if cleaned_images:
                # prefer cleaned image with matching index
                preferred = next(
                    (
                        img
                        for img in cleaned_images
                        if img.get("index") == primary.get("image_index", 0)
                    ),
                    cleaned_images[0],
                )
                source_path = Path(preferred["path"])

        if not source_path:
            path_value = primary.get("path")
            if not path_value:
                return None
            source_path = Path(path_value)

        if not source_path.exists():
            return None

        image = Image.open(source_path).convert("RGBA")
        normalized = self._normalize_image(image)

        return NormalizedSprite(
            image=normalized["image"],
            source_path=source_path,
            canvas_size=normalized["canvas_size"],
            content_bounds=normalized["content_bounds"],
            offset=normalized["offset"],
            scale=normalized["scale"],
            metadata={
                "source": str(source_path),
                "fallback": primary.get("fallback", False),
                "image_index": primary.get("image_index"),
                "sprite_index": primary.get("sprite_index"),
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_sprite_entry(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        def score(entry: Dict[str, Any]) -> float:
            size = entry.get("size") or (0, 0)
            width, height = size
            area = width * height
            return area

        return max(entries, key=score)

    def _normalize_image(self, image: Image.Image) -> Dict[str, Any]:
        bbox = image.getbbox()
        if not bbox:
            # empty image, return centered blank canvas
            canvas = Image.new("RGBA", self.target_frame_size, (0, 0, 0, 0))
            return {
                "image": canvas,
                "canvas_size": self.target_frame_size,
                "content_bounds": (0, 0, 0, 0),
                "offset": (0, 0),
                "scale": 1.0,
            }

        cropped = image.crop(bbox)
        content_width, content_height = cropped.size

        target_width, target_height = self.target_frame_size
        max_content_dimension = max(content_width, content_height)
        max_target = max(target_width, target_height) - (self.padding * 2)

        if max_content_dimension > 0:
            scale = min(max_target / max_content_dimension, 1.0)
        else:
            scale = 1.0

        if scale != 1.0:
            new_size = (
                max(1, int(math.ceil(content_width * scale))),
                max(1, int(math.ceil(content_height * scale))),
            )
            cropped = cropped.resize(new_size, Image.Resampling.NEAREST)
            content_width, content_height = cropped.size
        else:
            new_size = cropped.size

        canvas = Image.new("RGBA", self.target_frame_size, (0, 0, 0, 0))
        offset_x = (target_width - content_width) // 2
        offset_y = (target_height - content_height) // 2
        canvas.paste(cropped, (offset_x, offset_y))

        bounds_on_canvas = (
            offset_x,
            offset_y,
            offset_x + content_width,
            offset_y + content_height,
        )

        return {
            "image": canvas,
            "canvas_size": self.target_frame_size,
            "content_bounds": bounds_on_canvas,
            "offset": (offset_x, offset_y),
            "scale": scale,
        }


__all__ = ["SpriteNormalizer", "NormalizedSprite"]



