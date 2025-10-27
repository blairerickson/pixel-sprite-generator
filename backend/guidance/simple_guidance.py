"""
Simple working guidance implementation for testing
"""
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image
import uuid

from sd_client import SDClient, GenerationParams
from animation_models import AnimationType, Direction, AnimationGuidanceMethod, AnimationFrame
from .base_guidance import BaseGuidance, GuidanceCapabilities

class SimpleGuidance(BaseGuidance):
    """Simple working guidance that actually generates images"""
    
    def __init__(self, sd_client: SDClient, config: Dict[str, Any]):
        super().__init__(sd_client, config)
        self.method_type = AnimationGuidanceMethod.PROMPT_ONLY
        self.output_dir = Path(config['paths']['output_dir'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of this guidance method"""
        return GuidanceCapabilities(
            method=self.method_type,
            available=True,
            quality_rating=0.6,
            speed_rating=0.8,
            consistency_rating=0.5,
            notes="Simple prompt-based generation with basic consistency"
        )
    
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        """Get the guidance method type"""
        return self.method_type
    
    async def generate_frame(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        total_frames: int,
        reference_images: Optional[Dict[Direction, Image.Image]] = None,
        lora_name: Optional[str] = None,
        lora_weight: Optional[float] = None,
        width: int = 512,
        height: int = 512,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: int = -1
    ) -> AnimationFrame:
        """Generate a single frame"""
        # Create frame-specific prompt
        frame_prompt = self._create_frame_prompt(
            character_description, animation_type, direction, frame_index, total_frames
        )
        
        # Generate image
        params = GenerationParams(
            prompt=frame_prompt,
            negative_prompt="blurry, realistic, low detail, 3d, rendered",
            lora=lora_name,
            lora_weight=lora_weight,
            width=width,
            height=height,
            steps=steps or 20,
            cfg_scale=cfg_scale or 7.5,
            seed=seed if seed != -1 else -1,
            batch_size=1
        )
        
        # Generate image using SD client
        result = await self.sd_client.generate(params)
        
        if not result or not result.get('images'):
            raise Exception(f"Failed to generate frame {frame_index} for {direction.value}")
        
        image = result['images'][0]
        
        # Save image
        frame_filename = f"frame_{int(time.time() * 1000)}_{frame_index}.png"
        frame_path = self.output_dir / frame_filename
        image.save(frame_path)
        
        # Create AnimationFrame object
        return AnimationFrame(
            image_url=f"/output/{frame_filename}",  # Relative URL for serving
            direction=direction,
            frame_index=frame_index,
            animation_type=animation_type,
            seed=result.get('seed', seed),
            guidance_method=self.method_type,
            quality_score=0.7,  # Placeholder
            generation_time=5.0,  # Placeholder
            metadata={
                'guidance_method': self.method_type.value,
                'prompt': frame_prompt
            }
        )
    
    async def generate_animation_sequence(
        self,
        character_description: str,
        animation_type: AnimationType,
        directions: List[Direction],
        reference_images: Optional[Dict[Direction, Image.Image]] = None,
        frame_count: Optional[int] = None,
        lora_name: Optional[str] = None,
        lora_weight: Optional[float] = None,
        width: int = 512,
        height: int = 512,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: int = -1
    ) -> List[AnimationFrame]:
        """Generate animation sequence using simple prompt-based approach"""
        
        # Determine frame count
        if frame_count is None:
            frame_counts = {
                AnimationType.IDLE: 2,
                AnimationType.WALK: 8,
                AnimationType.RUN: 8,
                AnimationType.ATTACK: 6,
                AnimationType.CAST_SPELL: 8,
                AnimationType.DEATH: 6,
                AnimationType.JUMP: 4,
                AnimationType.CROUCH: 3,
                AnimationType.HURT: 4
            }
            frame_count = frame_counts.get(animation_type, 4)
        
        all_frames = []
        
        for direction in directions:
            for frame_index in range(frame_count):
                # Create frame-specific prompt
                frame_prompt = self._create_frame_prompt(
                    character_description, animation_type, direction, frame_index, frame_count
                )
                
                # Generate image
                params = GenerationParams(
                    prompt=frame_prompt,
                    negative_prompt="blurry, realistic, low detail, 3d, rendered",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=width,
                    height=height,
                    steps=steps or 20,
                    cfg_scale=cfg_scale or 7.5,
                    seed=seed if seed != -1 else -1,
                    batch_size=1
                )
                
                try:
                    # Generate image using SD client
                    result = await self.sd_client.generate(params)
                    
                    if result and result.get('images'):
                        image = result['images'][0]
                        
                        # Save image
                        frame_filename = f"frame_{len(all_frames)}.png"
                        frame_path = self.output_dir / frame_filename
                        image.save(frame_path)
                        
                        # Create AnimationFrame object
                        frame_data = AnimationFrame(
                            image_url=f"/output/{frame_filename}",  # Relative URL for serving
                            direction=direction,
                            frame_index=frame_index,
                            animation_type=animation_type,
                            seed=result.get('seed', seed),
                            guidance_method=self.method_type,
                            quality_score=0.7,  # Placeholder
                            generation_time=5.0,  # Placeholder
                            metadata={
                                'guidance_method': self.method_type.value,
                                'prompt': frame_prompt
                            }
                        )
                        
                        all_frames.append(frame_data)
                        
                        print(f"Generated frame {frame_index} for {direction.value}: {frame_filename}")
                        
                    else:
                        print(f"Failed to generate frame {frame_index} for {direction.value}")
                        
                except Exception as e:
                    print(f"Error generating frame {frame_index} for {direction.value}: {e}")
                    continue
        
        return all_frames
    
    def _create_frame_prompt(
        self, 
        character_description: str, 
        animation_type: AnimationType, 
        direction: Direction, 
        frame_index: int, 
        total_frames: int
    ) -> str:
        """Create frame-specific prompt"""
        
        # Base prompt
        base_prompt = f"{character_description}, pixel art, sprite, full body, clean linework, vibrant colors"
        
        # Add animation-specific terms
        animation_prompts = {
            AnimationType.IDLE: "standing still, breathing, idle pose",
            AnimationType.WALK: "walking, stepping, walking cycle",
            AnimationType.RUN: "running, sprinting, fast movement",
            AnimationType.ATTACK: "attacking, striking, combat pose",
            AnimationType.CAST_SPELL: "casting spell, magic, wizard pose",
            AnimationType.DEATH: "dying, falling, death pose",
            AnimationType.JUMP: "jumping, leaping, mid-air",
            AnimationType.CROUCH: "crouching, low pose, sneaking",
            AnimationType.HURT: "hurt, injured, taking damage"
        }
        
        animation_prompt = animation_prompts.get(animation_type, "character pose")
        
        # Add direction
        direction_prompts = {
            Direction.SOUTH: "facing forward, front view",
            Direction.WEST: "facing left, side view",
            Direction.EAST: "facing right, side view", 
            Direction.NORTH: "facing backward, back view",
            Direction.SOUTHWEST: "facing forward-left, diagonal view",
            Direction.SOUTHEAST: "facing forward-right, diagonal view",
            Direction.NORTHWEST: "facing backward-left, diagonal view",
            Direction.NORTHEAST: "facing backward-right, diagonal view"
        }
        
        direction_prompt = direction_prompts.get(direction, "facing forward")
        
        # Add frame timing
        if total_frames > 1:
            frame_timing = f", frame {frame_index + 1} of {total_frames}"
        else:
            frame_timing = ""
        
        # Combine all parts
        full_prompt = f"{base_prompt}, {animation_prompt}, {direction_prompt}{frame_timing}, solid color background"
        
        return full_prompt
