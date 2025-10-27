"""
Base guidance class for animation generation
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image
import time

from animation_models import (
    Direction, AnimationType, AnimationGuidanceMethod, 
    AnimationFrame, GuidanceCapabilities
)
from sd_client import SDClient, GenerationParams

logger = logging.getLogger(__name__)


class BaseGuidance(ABC):
    """Base class for all animation guidance methods"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        self.sd_client = sd_client
        self.config = config
        self.animation_config = config.get('animation', {})
        self.guidance_config = self.animation_config.get('guidance', {})
    
    @abstractmethod
    async def generate_frame(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        reference_image: Optional[Image.Image] = None,
        template_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """
        Generate a single animation frame
        
        Args:
            character_description: Description of the character
            animation_type: Type of animation (idle, walk, etc.)
            direction: Direction character is facing
            frame_index: Index of frame in animation sequence
            reference_image: Reference image for consistency
            template_data: Template pose data
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (generated_image, metadata)
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of this guidance method"""
        pass
    
    def is_available(self) -> bool:
        """Check if this guidance method is available"""
        return self.get_capabilities().available
    
    def get_quality_rating(self) -> float:
        """Get quality rating for this method (0-1)"""
        return self.get_capabilities().quality_rating
    
    def get_speed_rating(self) -> float:
        """Get speed rating for this method (0-1)"""
        return self.get_capabilities().speed_rating
    
    def get_consistency_rating(self) -> float:
        """Get consistency rating for this method (0-1)"""
        return self.get_capabilities().consistency_rating
    
    async def generate_animation_sequence(
        self,
        character_description: str,
        animation_type: AnimationType,
        directions: List[Direction],
        reference_images: Optional[Dict[Direction, Image.Image]] = None,
        frame_count: Optional[int] = None,
        **kwargs
    ) -> List[AnimationFrame]:
        """
        Generate complete animation sequence for all directions
        
        Args:
            character_description: Description of the character
            animation_type: Type of animation
            directions: List of directions to generate
            reference_images: Reference images for each direction
            frame_count: Number of frames per direction (auto if None)
            **kwargs: Additional parameters
            
        Returns:
            List of AnimationFrame objects
        """
        if frame_count is None:
            frame_count = self._get_default_frame_count(animation_type)
        
        frames = []
        
        for direction in directions:
            reference_image = reference_images.get(direction) if reference_images else None
            
            for frame_index in range(frame_count):
                try:
                    start_time = time.time()
                    
                    # Generate frame
                    image, metadata = await self.generate_frame(
                        character_description=character_description,
                        animation_type=animation_type,
                        direction=direction,
                        frame_index=frame_index,
                        reference_image=reference_image,
                        **kwargs
                    )
                    
                    generation_time = time.time() - start_time
                    
                    if image:
                        # Save image and get URL
                        frame_filename = f"frame_{direction.value}_{frame_index}_{int(time.time() * 1000)}.png"
                        frame_path = Path(self.config['paths']['output_dir']) / frame_filename
                        frame_path.parent.mkdir(parents=True, exist_ok=True)
                        image.save(frame_path)
                        
                        frame = AnimationFrame(
                            image_url=f"/output/{frame_filename}",
                            direction=direction,
                            frame_index=frame_index,
                            animation_type=animation_type,
                            seed=metadata.get('seed', -1),
                            guidance_method=self.get_guidance_method(),
                            generation_time=generation_time,
                            pose_data=metadata
                        )
                        frames.append(frame)
                        logger.info(f"Generated {animation_type.value} {direction.value} frame {frame_index} in {generation_time:.2f}s")
                    else:
                        logger.warning(f"Failed to generate {animation_type.value} {direction.value} frame {frame_index}")
                        
                except Exception as e:
                    logger.error(f"Error generating frame {direction.value} {frame_index}: {e}")
                    continue
        
        return frames
    
    def _get_default_frame_count(self, animation_type: AnimationType) -> int:
        """Get default frame count for animation type"""
        frame_counts = self.animation_config.get('generation', {}).get('frame_counts', {})
        return frame_counts.get(animation_type.value, 8)
    
    def _build_base_prompt(
        self, 
        character_description: str, 
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int
    ) -> str:
        """Build base prompt for generation"""
        # Get base template
        base_template = self.animation_config.get('generation', {}).get('prompt_template',
            "{description}, pixel art, {animation_type} animation, {direction}, frame {frame_index}, sprite, full body, clean linework, vibrant colors, solid color background")
        
        direction_prompts = {
            Direction.SOUTH: "facing forward",
            Direction.WEST: "facing left", 
            Direction.EAST: "facing right",
            Direction.NORTH: "facing backward",
            Direction.SOUTHEAST: "facing forward-right",
            Direction.SOUTHWEST: "facing forward-left",
            Direction.NORTHEAST: "facing backward-right",
            Direction.NORTHWEST: "facing backward-left"
        }
        
        direction_text = direction_prompts.get(direction, "facing forward")
        
        prompt = base_template.format(
            description=character_description,
            animation_type=animation_type.value,
            direction=direction_text,
            frame_index=frame_index + 1
        )
        
        return prompt
    
    def _get_negative_prompt(self) -> str:
        """Get negative prompt"""
        return self.config.get('generation', {}).get('default_negative',
            "blurry, low quality, jpeg artifacts, watermark, text, signature, realistic, photograph, transparent background, gradient background")
    
    def _get_lora_config(self, lora_name: str) -> Optional[dict]:
        """Get LoRA configuration by name"""
        for lora in self.config.get('sd', {}).get('loras', []):
            if lora['name'] == lora_name:
                return lora
        return None
    
    def _apply_lora_to_prompt(self, prompt: str, lora_name: str, lora_weight: float = 1.0) -> str:
        """Apply LoRA to prompt"""
        lora_config = self._get_lora_config(lora_name)
        if not lora_config:
            return prompt
        
        # Add LoRA triggers
        triggers = " ".join(lora_config.get('triggers', []))
        if triggers:
            prompt = f"{triggers}, {prompt}"
        
        # Add LoRA weight
        prompt += f" <lora:{lora_name}:{lora_weight}>"
        
        return prompt
    
    def _calculate_quality_score(self, image: Image.Image, metadata: Dict[str, Any]) -> float:
        """Calculate quality score for generated image"""
        try:
            # Simple quality metrics
            score = 0.5  # Base score
            
            # Check image size
            width, height = image.size
            if width >= 256 and height >= 256:
                score += 0.2
            
            # Check if image has content (not just background)
            if image.mode == 'RGBA':
                alpha = image.split()[-1]
                non_transparent = sum(1 for pixel in alpha.getdata() if pixel > 0)
                total_pixels = alpha.size[0] * alpha.size[1]
                if total_pixels > 0:
                    content_ratio = non_transparent / total_pixels
                    if 0.1 < content_ratio < 0.9:  # Good content ratio
                        score += 0.3
            
            return min(1.0, score)
            
        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 0.5
    
    @abstractmethod
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        """Get the guidance method enum"""
        pass


class PromptOnlyGuidance(BaseGuidance):
    """Simple prompt-only guidance (baseline method)"""
    
    async def generate_frame(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        reference_image: Optional[Image.Image] = None,
        template_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame using only prompt guidance"""
        try:
            # Build enhanced prompt
            prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                prompt = self._apply_lora_to_prompt(prompt, lora_name, lora_weight)
            
            # Build generation parameters
            params = GenerationParams(
                prompt=prompt,
                negative_prompt=self._get_negative_prompt(),
                preset="character_sprite",
                lora=lora_name,
                lora_weight=lora_weight,
                width=kwargs.get('width', 512),
                height=kwargs.get('height', 512),
                steps=kwargs.get('steps', 25),
                cfg_scale=kwargs.get('cfg_scale', 7.0),
                seed=kwargs.get('seed', -1),
                batch_size=1
            )
            
            # Generate image
            result = await self.sd_client.generate(params)
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'prompt_only',
                    'quality_score': quality_score,
                    'prompt_used': prompt,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in prompt-only generation: {e}")
            return None, {'error': str(e)}
    
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of prompt-only guidance"""
        return GuidanceCapabilities(
            method=AnimationGuidanceMethod.PROMPT_ONLY,
            available=True,  # Always available
            quality_rating=0.3,  # Low quality
            speed_rating=0.9,  # Fast
            consistency_rating=0.2,  # Poor consistency
            notes="Baseline method, always available but low quality"
        )
    
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        return AnimationGuidanceMethod.PROMPT_ONLY

