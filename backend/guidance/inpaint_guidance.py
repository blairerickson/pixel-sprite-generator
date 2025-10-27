"""
Img2Img inpainting guidance for animation generation
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
from guidance.template_guidance import TemplateGuidance
from sd_client import SDClient, GenerationParams

logger = logging.getLogger(__name__)


class InpaintGuidance(BaseGuidance):
    """Img2Img inpainting guidance for consistent animation generation"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        super().__init__(sd_client, config)
        self.template_guidance = TemplateGuidance(sd_client, config)
        self.template_manager = self.template_guidance.template_manager
        self.template_renderer = self.template_guidance.template_renderer
    
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
        """Generate frame using img2img inpainting"""
        try:
            # If no reference image, use simplified generation instead of template fallback
            if reference_image is None:
                logger.info(f"No reference image provided for {direction.value} {frame_index}, using direct generation")
                
                # Generate directly with prompt
                direct_prompt = f"{character_description}, pixel art, sprite, {animation_type.value} animation, {direction.value} facing, frame {frame_index + 1}, full body"
                
                params = GenerationParams(
                    prompt=direct_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=kwargs.get('lora_name'),
                    lora_weight=kwargs.get('lora_weight', 1.0),
                    width=kwargs.get('width', 512),
                    height=kwargs.get('height', 512),
                    steps=kwargs.get('steps', 20),
                    cfg_scale=kwargs.get('cfg_scale', 7.0),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                )
                
                result = await self.sd_client.generate(params)
                
                if result and 'images' in result and len(result['images']) > 0:
                    return result['images'][0], {
                        'method': 'direct_generation',
                        'quality_score': 0.6,
                        'prompt_used': direct_prompt,
                        'seed': result.get('seed', -1)
                    }
                else:
                    return None, {'error': 'Direct generation failed'}
            
            # Try to get template pose mask, but don't fail if unavailable
            template, mask = None, None
            try:
                template, mask = self.template_renderer.render_for_inpainting(
                    animation_type, direction, frame_index, reference_image.size
                )
            except Exception as e:
                logger.warning(f"Template unavailable for {animation_type.value} {direction.value} {frame_index}: {e}")
            
            if not template or not mask:
                logger.info(f"No template/mask available for {animation_type.value} {direction.value} {frame_index}, using reference-only generation")
                return await self.generate_with_reference_only(
                    character_description, animation_type, direction, frame_index,
                    reference_image, **kwargs
                )
            
            # Create inpaint canvas
            canvas = await self._create_inpaint_canvas(reference_image, template, mask)
            
            # Build inpainting prompt
            inpaint_prompt = self._build_inpaint_prompt(character_description, animation_type, direction, frame_index)
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                inpaint_prompt = self._apply_lora_to_prompt(inpaint_prompt, lora_name, lora_weight)
            
            # Generate using img2img inpainting
            result = await self.sd_client.generate_with_inpaint(
                GenerationParams(
                    prompt=inpaint_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=reference_image.width,
                    height=reference_image.height,
                    steps=kwargs.get('steps', 30),
                    cfg_scale=kwargs.get('cfg_scale', 7.5),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                ),
                canvas,
                mask
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'img2img_inpaint',
                    'quality_score': quality_score,
                    'prompt_used': inpaint_prompt,
                    'reference_used': True,
                    'template_path': str(self.template_manager.get_template_path(animation_type, direction, frame_index)),
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in inpaint guidance generation: {e}")
            return None, {'error': str(e)}
    
    async def _create_inpaint_canvas(
        self, 
        reference_image: Image.Image, 
        template: Image.Image, 
        mask: Image.Image
    ) -> Image.Image:
        """Create canvas for inpainting with reference and template"""
        # Start with reference image
        canvas = reference_image.copy()
        
        # Overlay template with low opacity for guidance
        template_alpha = 0.2  # Very low opacity
        template_with_alpha = template.copy()
        template_with_alpha.putalpha(int(255 * template_alpha))
        
        # Composite template onto canvas
        if canvas.mode != 'RGBA':
            canvas = canvas.convert('RGBA')
        
        canvas.paste(template_with_alpha, (0, 0), template_with_alpha)
        
        return canvas
    
    def _build_inpaint_prompt(
        self, 
        character_description: str, 
        animation_type: AnimationType,
        direction: Direction, 
        frame_index: int
    ) -> str:
        """Build prompt for inpainting"""
        # Get pose description
        pose_description = self.template_renderer.render_for_prompt(
            animation_type, direction, frame_index
        )
        
        # Build base prompt
        base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
        
        # Add inpainting-specific instructions
        inpaint_instructions = [
            "maintain character consistency with reference",
            "follow the pose template exactly",
            "pixel art style",
            "clean linework",
            "vibrant colors",
            "solid color background"
        ]
        
        # Combine everything
        inpaint_prompt = f"{base_prompt}, {pose_description}, {', '.join(inpaint_instructions)}"
        
        return inpaint_prompt
    
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of inpaint guidance"""
        return GuidanceCapabilities(
            method=AnimationGuidanceMethod.IMG2IMG_INPAINT,
            available=True,  # Available if img2img is supported
            quality_rating=0.8,  # High quality
            speed_rating=0.6,  # Medium speed
            consistency_rating=0.9,  # Excellent consistency with reference
            notes="Uses reference images and pose templates for high consistency"
        )
    
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        return AnimationGuidanceMethod.IMG2IMG_INPAINT
    
    async def generate_with_reference_only(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        reference_image: Image.Image,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame using only reference image (no template)"""
        try:
            # Build prompt with reference guidance
            base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            
            # Add reference-specific instructions
            reference_prompt = f"{base_prompt}, maintain exact character style from reference, {animation_type.value} animation, {direction.value} facing"
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                reference_prompt = self._apply_lora_to_prompt(reference_prompt, lora_name, lora_weight)
            
            # Use img2img with reference
            result = await self.sd_client.generate_with_inpaint(
                GenerationParams(
                    prompt=reference_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=reference_image.width,
                    height=reference_image.height,
                    steps=kwargs.get('steps', 25),
                    cfg_scale=kwargs.get('cfg_scale', 7.0),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                ),
                reference_image,
                self._create_full_mask(reference_image.size)  # Inpaint entire image
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'reference_only_inpaint',
                    'quality_score': quality_score,
                    'prompt_used': reference_prompt,
                    'reference_used': True,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in reference-only inpaint generation: {e}")
            return None, {'error': str(e)}
    
    def _create_full_mask(self, size: Tuple[int, int]) -> Image.Image:
        """Create a full mask for inpainting entire image"""
        mask = Image.new('L', size, 255)  # White = inpaint
        return mask
    
    async def generate_with_pose_mask(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        reference_image: Image.Image,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame using pose mask for selective inpainting"""
        try:
            # Get pose mask
            mask = self.template_manager.create_pose_mask(
                animation_type, direction, frame_index, reference_image.size
            )
            
            if not mask:
                logger.warning(f"No pose mask available, using full mask")
                mask = self._create_full_mask(reference_image.size)
            
            # Build prompt
            base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
            pose_description = self.template_renderer.render_for_prompt(animation_type, direction, frame_index)
            
            pose_prompt = f"{base_prompt}, {pose_description}, follow pose exactly, maintain character style"
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                pose_prompt = self._apply_lora_to_prompt(pose_prompt, lora_name, lora_weight)
            
            # Generate with pose mask
            result = await self.sd_client.generate_with_inpaint(
                GenerationParams(
                    prompt=pose_prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=reference_image.width,
                    height=reference_image.height,
                    steps=kwargs.get('steps', 30),
                    cfg_scale=kwargs.get('cfg_scale', 7.5),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                ),
                reference_image,
                mask
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'pose_mask_inpaint',
                    'quality_score': quality_score,
                    'prompt_used': pose_prompt,
                    'reference_used': True,
                    'pose_mask_used': True,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in pose mask inpaint generation: {e}")
            return None, {'error': str(e)}
    
    def get_available_templates(self) -> Dict[str, List[str]]:
        """Get list of available templates"""
        return self.template_manager.list_available_animations()
    
    def has_template(self, animation_type: AnimationType, direction: Direction, frame_index: int) -> bool:
        """Check if template exists for given parameters"""
        return self.template_guidance.has_template(animation_type, direction, frame_index)
    
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
        """Generate complete animation sequence using inpainting guidance"""
        try:
            logger.info(f"Starting InpaintGuidance for {animation_type.value} with {len(directions)} directions")
            
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
                                guidance_method=AnimationGuidanceMethod.IMG2IMG_INPAINT,
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
                        
            logger.info(f"InpaintGuidance generated {len(all_frames)} total frames")
            return all_frames
            
        except Exception as e:
            logger.exception(f"InpaintGuidance failed completely: {e}")
            raise

