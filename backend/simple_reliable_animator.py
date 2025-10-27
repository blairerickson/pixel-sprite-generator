"""
Simple Reliable Animator
Simplified approach that focuses on working consistently
"""
import logging
from typing import Dict, List, Optional
from PIL import Image
from pathlib import Path
import time

from animation_models import (
    AnimationType, Direction, AnimationFrame, AnimationSequence,
    AnimationGenerationResult, AnimationGenerateRequest
)
from sd_client import SDClient, GenerationParams

logger = logging.getLogger(__name__)


class SimpleReliableAnimator:
    """Simplified animation system focused on reliability over complexity"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        self.sd_client = sd_client
        self.config = config
        
    async def generate_walk_animation(
        self,
        character_description: str,
        directions: List[str],
        seed: int,
        job_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, List[Image.Image]]:
        """Generate simple but reliable walking animation"""
        
        logger.info(f"SIMPLE ANIMATOR: Generating walk for {character_description}")
        
        # Step 1: Generate single master character
        master = await self._generate_master(character_description, seed, **kwargs)
        
        # Step 2: Create walking frames using master as base
        all_frames = {}
        walk_prompts = self._get_walk_prompts()
        
        if job_id:
            output_dir = Path(self.config['paths']['output_dir']) / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
        
        for direction in directions:
            logger.info(f"Generating {len(walk_prompts)} frames for {direction}")
            frames = []
            
            for i, walk_prompt in enumerate(walk_prompts):
                try:
                    # Build direction-specific prompt
                    direction_text = {
                        "south": "facing forward",
                        "west": "facing left", 
                        "east": "facing right",
                        "north": "facing backward"
                    }.get(direction, "facing forward")
                    
                    full_prompt = f"{character_description}, same character, {direction_text}, {walk_prompt}, pixel art sprite, walking animation"
                    
                    params = GenerationParams(
                        prompt=full_prompt,
                        negative_prompt=self._get_negative_prompt(),
                        preset="character_sprite",
                        lora=kwargs.get('style_lora'),
                        lora_weight=kwargs.get('lora_weight', 1.0),
                        width=kwargs.get('width', 512),
                        height=kwargs.get('height', 512),
                        steps=25,
                        cfg_scale=7.0,
                        seed=seed + i,  # Slight variation per frame
                        batch_size=1
                    )
                    
                    result = await self.sd_client.generate(params)
                    
                    if result and 'images' in result and len(result['images']) > 0:
                        frame_image = result['images'][0]
                        
                        # Save frame
                        if job_id:
                            timestamp = int(time.time() * 1000) + i
                            filename = f"frame_{direction}_{i}_{timestamp}.png"
                            frame_path = output_dir / filename
                            frame_image.save(frame_path)
                            
                            # Save to root for serving
                            root_path = Path(self.config['paths']['output_dir']).parent / filename
                            frame_image.save(root_path)
                        
                        frames.append(frame_image)
                        logger.info(f"Generated {direction} frame {i}: {walk_prompt}")
                        
                    else:
                        logger.error(f"Failed to generate {direction} frame {i}")
                        
                except Exception as e:
                    logger.error(f"Error generating {direction} frame {i}: {e}")
                    continue
            
            all_frames[direction] = frames
            logger.info(f"Completed {len(frames)} frames for {direction}")
        
        total_frames = sum(len(frames) for frames in all_frames.values())
        logger.info(f"SIMPLE ANIMATOR generated {total_frames} total frames")
        
        return all_frames
    
    async def _generate_master(
        self, 
        character_description: str, 
        seed: int,
        **kwargs
    ) -> Image.Image:
        """Generate master character for consistency"""
        
        master_prompt = f"{character_description}, pixel art, sprite, character reference, front view, full body, high quality"
        
        params = GenerationParams(
            prompt=master_prompt,
            negative_prompt=self._get_negative_prompt(),
            preset="character_sprite",
            lora=kwargs.get('style_lora'),
            lora_weight=kwargs.get('lora_weight', 1.0),
            width=kwargs.get('width', 512),
            height=kwargs.get('height', 512),
            steps=30,  # High quality for master
            cfg_scale=8.0,
            seed=seed,
            batch_size=1
        )
        
        result = await self.sd_client.generate(params)
        
        if not result or 'images' not in result or len(result['images']) == 0:
            raise Exception("Failed to generate master character")
        
        return result['images'][0]
    
    def _get_walk_prompts(self) -> List[str]:
        """Define proper walking sequence prompts"""
        return [
            "standing ready to walk",
            "left foot stepping forward",
            "left foot planted, body moving forward",
            "passing position, weight centered",
            "right foot stepping forward", 
            "right foot planted, body moving forward",
            "passing position return",
            "cycle return to start"
        ]
    
    def _get_negative_prompt(self) -> str:
        """Get negative prompt for animation generation"""
        return (
            "blurry, low quality, jpeg artifacts, multiple characters, "
            "inconsistent character, bad anatomy, deformed, extra limbs"
        )
