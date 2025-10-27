"""
Template-based guidance for animation generation
"""
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import time

from animation_models import (
    Direction, AnimationType, AnimationGuidanceMethod, 
    AnimationFrame, GuidanceCapabilities
)
from animation_templates import TemplateManager, TemplateRenderer
from guidance.base_guidance import BaseGuidance
from sd_client import SDClient, GenerationParams

logger = logging.getLogger(__name__)


class TemplateGuidance(BaseGuidance):
    """Template-based guidance using pose templates"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        super().__init__(sd_client, config)
        self.template_manager = TemplateManager(config.get('animation', {}).get('guidance', {}).get('template_pose', {}).get('template_directory', 'templates'))
        self.template_renderer = TemplateRenderer(self.template_manager)
    
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
        """Generate frame using template guidance"""
        try:
            # Try to get template pose description, but don't fail if unavailable
            pose_description = None
            try:
                pose_description = self.template_renderer.render_for_prompt(
                    animation_type, direction, frame_index
                )
            except Exception as e:
                logger.warning(f"Template description unavailable for {animation_type.value} {direction.value} {frame_index}: {e}")
                
            # Build enhanced prompt with template guidance
            base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            
            # Add template-specific guidance (or fallback)
            if pose_description:
                template_prompt = self._build_template_prompt(base_prompt, pose_description, reference_image)
            else:
                # Fallback to basic animation prompt
                template_prompt = f"{base_prompt}, {animation_type.value} animation, frame {frame_index + 1}"
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                template_prompt = self._apply_lora_to_prompt(template_prompt, lora_name, lora_weight)
            
            # Build generation parameters
            params = GenerationParams(
                prompt=template_prompt,
                negative_prompt=self._get_negative_prompt(),
                preset="character_sprite",
                lora=lora_name,
                lora_weight=lora_weight,
                width=kwargs.get('width', 512),
                height=kwargs.get('height', 512),
                steps=kwargs.get('steps', 30),  # More steps for template guidance
                cfg_scale=kwargs.get('cfg_scale', 7.5),  # Higher CFG for better template adherence
                seed=kwargs.get('seed', -1),
                batch_size=1
            )
            
            # Generate image
            result = await self.sd_client.generate(params)
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'template_pose',
                    'quality_score': quality_score,
                    'prompt_used': template_prompt,
                    'pose_description': pose_description,
                    'template_path': str(self.template_manager.get_template_path(animation_type, direction, frame_index)),
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in template guidance generation: {e}")
            return None, {'error': str(e)}
    
    def _build_template_prompt(
        self, 
        base_prompt: str, 
        pose_description: str,
        reference_image: Optional[Image.Image] = None
    ) -> str:
        """Build prompt with template guidance"""
        # Add template-specific instructions
        template_instructions = [
            "follow the pose exactly",
            "maintain character consistency",
            "pixel art style",
            "clean linework",
            "vibrant colors"
        ]
        
        if reference_image:
            template_instructions.append("match the reference character style")
        
        # Combine base prompt with template guidance
        template_prompt = f"{base_prompt}, {pose_description}, {', '.join(template_instructions)}"
        
        return template_prompt
    
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of template guidance"""
        return GuidanceCapabilities(
            method=AnimationGuidanceMethod.TEMPLATE_POSE,
            available=True,  # Always available if templates exist
            quality_rating=0.6,  # Medium quality
            speed_rating=0.7,  # Medium speed
            consistency_rating=0.7,  # Good consistency with templates
            notes="Uses pose templates for guidance, good consistency"
        )
    
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        return AnimationGuidanceMethod.TEMPLATE_POSE
    
    async def generate_with_template_overlay(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame with template overlay (alternative method)"""
        try:
            # Get template image
            template_path = self.template_manager.get_template_path(animation_type, direction, frame_index)
            if not template_path or not template_path.exists():
                logger.warning(f"No template found for {animation_type.value} {direction.value} {frame_index}")
                return await self._generate_without_template(character_description, animation_type, direction, frame_index, **kwargs)
            
            # Load template
            template = Image.open(template_path).convert('RGBA')
            
            # Create composite image with template overlay
            width = kwargs.get('width', 512)
            height = kwargs.get('height', 512)
            
            # Resize template to match target size
            template = template.resize((width, height), Image.Resampling.LANCZOS)
            
            # Create base canvas
            canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            
            # Overlay template with low opacity for guidance
            template_alpha = 0.3  # Low opacity so it doesn't dominate
            template_with_alpha = template.copy()
            template_with_alpha.putalpha(int(255 * template_alpha))
            canvas.paste(template_with_alpha, (0, 0), template_with_alpha)
            
            # Build prompt with template reference
            base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            template_prompt = f"{base_prompt}, use the pose template as reference, follow the pose structure"
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                template_prompt = self._apply_lora_to_prompt(template_prompt, lora_name, lora_weight)
            
            # Build generation parameters
            params = GenerationParams(
                prompt=template_prompt,
                negative_prompt=self._get_negative_prompt(),
                preset="character_sprite",
                lora=lora_name,
                lora_weight=lora_weight,
                width=width,
                height=height,
                steps=kwargs.get('steps', 30),
                cfg_scale=kwargs.get('cfg_scale', 7.5),
                seed=kwargs.get('seed', -1),
                batch_size=1
            )
            
            # Generate image
            result = await self.sd_client.generate(params)
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'template_overlay',
                    'quality_score': quality_score,
                    'prompt_used': template_prompt,
                    'template_path': str(template_path),
                    'overlay_alpha': template_alpha,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in template overlay generation: {e}")
            return None, {'error': str(e)}
    
    def get_available_templates(self) -> Dict[str, List[str]]:
        """Get list of available templates"""
        return self.template_manager.list_available_animations()
    
    def has_template(self, animation_type: AnimationType, direction: Direction, frame_index: int) -> bool:
        """Check if template exists for given parameters"""
        template_path = self.template_manager.get_template_path(animation_type, direction, frame_index)
        return template_path is not None and template_path.exists()
    
    async def _generate_without_template(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame without template (fallback method)"""
        try:
            # Build prompt without template
            base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            
            # Add animation-specific instructions
            animation_prompt = f"{base_prompt}, {animation_type.value} animation, {direction.value} facing, pixel art style"
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                animation_prompt = self._apply_lora_to_prompt(animation_prompt, lora_name, lora_weight)
            
            # Generate using standard SD
            result = await self.sd_client.generate(
                GenerationParams(
                    prompt=animation_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=kwargs.get('width', 512),
                    height=kwargs.get('height', 512),
                    steps=kwargs.get('steps', 20),
                    cfg_scale=kwargs.get('cfg_scale', 7.5),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                )
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'no_template_fallback',
                    'quality_score': quality_score,
                    'prompt_used': animation_prompt,
                    'template_used': False,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in no-template generation: {e}")
            return None, {'error': str(e)}
    
    async def create_pose_mask(
        self,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        target_size: Tuple[int, int] = (512, 512)
    ) -> Optional[Image.Image]:
        """Create pose mask for inpainting"""
        return self.template_manager.create_pose_mask(animation_type, direction, frame_index, target_size)
    
    async def render_for_controlnet(
        self,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        target_size: Tuple[int, int] = (512, 512)
    ) -> Optional[Image.Image]:
        """Render template for ControlNet"""
        return self.template_renderer.render_for_controlnet(animation_type, direction, frame_index, target_size)
    
    async def render_for_inpainting(
        self,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        target_size: Tuple[int, int] = (512, 512)
    ) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
        """Render template and mask for inpainting"""
        return self.template_renderer.render_for_inpainting(animation_type, direction, frame_index, target_size)
    
    # CRITICAL FIX: Add missing generate_animation_sequence method
    async def generate_animation_sequence(
        self,
        character_description: str,
        animation_type: AnimationType,
        directions: List[Direction],
        reference_images: Optional[Dict[Direction, Any]] = None,
        frame_count: Optional[int] = None,
        **kwargs
    ) -> List[AnimationFrame]:
        """Generate complete animation sequence using template guidance"""
        try:
            logger.info(f"Starting TemplateGuidance for {animation_type.value} with {len(directions)} directions")
            
            # Get frame count from config
            frame_counts = self.config.get('animation', {}).get('generation', {}).get('frame_counts', {})
            frames_per_direction = frame_count or frame_counts.get(animation_type.value, 8)
            logger.info(f"Frame count config: {frame_counts}")
            logger.info(f"Frames per direction for {animation_type.value}: {frames_per_direction}")
            
            all_frames = []
            
            # Generate frames for each direction
            for direction in directions:
                logger.info(f"Generating {frames_per_direction} frames for {direction.value}")
                reference_img = reference_images.get(direction) if reference_images else None
                
                for frame_idx in range(frames_per_direction):
                    try:
                        logger.info(f"Generating frame {frame_idx+1}/{frames_per_direction} for {direction.value}")
                        
                        # Generate single frame
                        frame_image, metadata = await self.generate_frame(
                            character_description=character_description,
                            animation_type=animation_type,
                            direction=direction,
                            frame_index=frame_idx,
                            reference_image=reference_img,
                            **kwargs
                        )
                        
                        if frame_image:
                            # Save frame with proper naming
                            job_id_param = kwargs.get('job_id', 'unknown')
                            logger.info(f"Saving frame with job_id: {job_id_param}")
                            timestamp = int(time.time() * 1000)
                            filename = f"frame_{direction.value}_{frame_idx}_{timestamp}.png"
                            
                            # Save to job-specific output directory
                            output_dir = Path(self.config['paths']['output_dir']) / str(job_id_param)
                            output_dir.mkdir(parents=True, exist_ok=True)
                            frame_path = output_dir / filename
                            frame_image.save(frame_path)
                            
                            # Also copy to root for serving (temporary solution)
                            root_path = Path(self.config['paths']['output_dir']).parent / filename
                            frame_image.save(root_path)
                            
                            # Create AnimationFrame object
                            frame_obj = AnimationFrame(
                                image_url=f"/{filename}",  # Serve from root
                                direction=direction,
                                frame_index=frame_idx,
                                animation_type=animation_type,
                                seed=metadata.get('seed', -1),
                                guidance_method=AnimationGuidanceMethod.TEMPLATE_POSE,
                                quality_score=metadata.get('quality_score', 0.7),
                                generation_time=0.0,
                                metadata=metadata
                            )
                            
                            all_frames.append(frame_obj)
                            logger.info(f"Generated frame {frame_idx} for {direction.value}")
                        else:
                            logger.error(f"Frame {frame_idx} failed for {direction.value}")
                            
                    except Exception as e:
                        logger.error(f"Frame {frame_idx} for {direction.value} failed: {e}")
                        continue
                        
            logger.info(f"TemplateGuidance generated {len(all_frames)} total frames")
            return all_frames
            
        except Exception as e:
            logger.exception(f"TemplateGuidance failed completely: {e}")
            raise

