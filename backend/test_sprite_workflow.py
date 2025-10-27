import json
from pathlib import Path

import pytest
from PIL import Image

from sprite_normalizer import SpriteNormalizer
from sprite_animator import SpriteAnimator


@pytest.fixture
def config(tmp_path):
    cfg = {
        "paths": {
            "output_dir": str(tmp_path / "out"),
            "temp_dir": str(tmp_path / "temp"),
            "cache_dir": str(tmp_path / "cache"),
        },
        "animation": {
            "generation": {
                "target_frame_size": (128, 128),
                "normalization_padding": 4,
            },
            "breathing": {
                "frame_count": 5,
                "vertical_scale_amplitude": 0.05,
                "horizontal_scale_amplitude": 0.02,
            },
        },
    }
    return cfg


@pytest.fixture
def sample_sprite(tmp_path):
    image = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    for x in range(16, 48):
        for y in range(16, 80):
            image.putpixel((x, y), (200, 120, 80, 255))
    sprite_path = tmp_path / "sprite.png"
    image.save(sprite_path)
    job_data = {
        "result": {
            "images": [
                {
                    "raw": str(sprite_path),
                    "processed": str(sprite_path),
                    "sprites": [],
                }
            ],
            "assets": {
                "raw_images": [
                    {
                        "index": 0,
                        "path": str(sprite_path),
                        "filename": "sprite.png",
                        "url": "/output/job/sprite.png",
                    }
                ],
            },
        }
    }
    return job_data


def test_sprite_normalizer_centers_sprite(config, sample_sprite):
    normalizer = SpriteNormalizer(config)
    normalized = normalizer.normalize_sprite_from_job(sample_sprite, use_cleaned=False)

    assert normalized is not None
    assert normalized.image.size == (128, 128)
    left, top, right, bottom = normalized.content_bounds
    content_width = right - left
    content_height = bottom - top
    assert content_width <= 128
    assert content_height <= 128
    assert left < right and top < bottom


def test_sprite_animator_generates_breathing_cycle(config, sample_sprite, tmp_path):
    normalizer = SpriteNormalizer(config)
    animator = SpriteAnimator(config)
    normalized = normalizer.normalize_sprite_from_job(sample_sprite, use_cleaned=False)
    assert normalized is not None

    output_dir = Path(config["paths"]["output_dir"]) / "breathing"
    result = animator.generate_breathing_cycle(normalized, output_dir)

    assert result.frame_count == 5
    assert len(result.frames) == 5
    assert result.sprite_sheet_path.exists()
    for frame in result.frames:
        assert frame.path.exists()
        frame_image = Image.open(frame.path)
        assert frame_image.size == tuple(result.frame_size)

    with open(output_dir / "metadata.json", "w", encoding="utf-8") as fp:
        json.dump(result.metadata, fp)

