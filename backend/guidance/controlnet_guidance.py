"""
ControlNet guidance for animation generation
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


class ControlNetGuidance(BaseGuidance):
    """ControlNet guidance for high-quality animation generation"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        super().__init__(sd_client, config)
        self.template_guidance = TemplateGuidance(sd_client, config)
        self.template_manager = self.template_guidance.template_manager
        self.template_renderer = self.template_guidance.template_renderer
        
        # ControlNet configuration
        self.controlnet_config = self.guidance_config.get('controlnet', {})
        self.preferred_models = self.controlnet_config.get('preferred_models', ['control_openpose', 'control_canny'])
        self.preprocessor = self.controlnet_config.get('preprocessor', 'openpose_full')
        
        # Cache for ControlNet availability
        self._controlnet_available = None
        self._available_models = None
        self._available_preprocessors = None
    
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
        """Generate frame using ControlNet guidance"""
        try:
            # Check if ControlNet is available
            if not await self.is_controlnet_available():
                logger.warning("ControlNet not available, falling back to template guidance")
                return await self.template_guidance.generate_frame(
                    character_description, animation_type, direction, frame_index,
                    reference_image, template_data, **kwargs
                )
            
            # Get control image from template
            control_image = await self.template_renderer.render_for_controlnet(
                animation_type, direction, frame_index, 
                (kwargs.get('width', 512), kwargs.get('height', 512))
            )
            
            if not control_image:
                logger.warning(f"No control image available for {animation_type.value} {direction.value} {frame_index}, falling back to template guidance")
                return await self.template_guidance.generate_frame(
                    character_description, animation_type, direction, frame_index,
                    reference_image, template_data, **kwargs
                )
            
            # Select best ControlNet model
            controlnet_model = await self._select_controlnet_model(animation_type)
            preprocessor = await self._select_preprocessor(animation_type)
            
            # Build prompt
            prompt = self._build_controlnet_prompt(character_description, animation_type, direction, frame_index)
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                prompt = self._apply_lora_to_prompt(prompt, lora_name, lora_weight)
            
            # ControlNet parameters
            control_weight = kwargs.get('control_weight', 1.0)
            guidance_start = kwargs.get('guidance_start', 0.0)
            guidance_end = kwargs.get('guidance_end', 1.0)
            
            # Generate using ControlNet
            result = await self.sd_client.generate_with_controlnet(
                GenerationParams(
                    prompt=prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=kwargs.get('width', 512),
                    height=kwargs.get('height', 512),
                    steps=kwargs.get('steps', 35),  # More steps for ControlNet
                    cfg_scale=kwargs.get('cfg_scale', 8.0),  # Higher CFG for ControlNet
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                ),
                control_image,
                controlnet_model,
                preprocessor,
                control_weight,
                guidance_start,
                guidance_end
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'controlnet',
                    'quality_score': quality_score,
                    'prompt_used': prompt,
                    'controlnet_model': controlnet_model,
                    'preprocessor': preprocessor,
                    'control_weight': control_weight,
                    'template_path': str(self.template_manager.get_template_path(animation_type, direction, frame_index)),
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in ControlNet guidance generation: {e}")
            return None, {'error': str(e)}
    
    async def is_controlnet_available(self) -> bool:
        """Check if ControlNet is available"""
        if self._controlnet_available is None:
            self._controlnet_available = await self.sd_client.is_controlnet_available()
        return self._controlnet_available
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get available ControlNet models"""
        if self._available_models is None:
            self._available_models = await self.sd_client.get_controlnet_models()
        return self._available_models
    
    async def get_available_preprocessors(self) -> List[str]:
        """Get available ControlNet preprocessors"""
        if self._available_preprocessors is None:
            self._available_preprocessors = await self.sd_client.get_controlnet_preprocessors()
        return self._available_preprocessors
    
    async def _select_controlnet_model(self, animation_type: AnimationType) -> str:
        """Select best ControlNet model for animation type"""
        available_models = await self.get_available_models()
        model_names = [model.get('model_name', '') for model in available_models]
        
        # Prefer pose-based models for character animations
        pose_models = ['control_openpose', 'control_openpose_full', 'control_openpose_face']
        for model in pose_models:
            if model in model_names:
                return model
        
        # Fall back to edge detection for other animations
        edge_models = ['control_canny', 'control_mlsd', 'control_hed']
        for model in edge_models:
            if model in model_names:
                return model
        
        # Use first available model
        if model_names:
            return model_names[0]
        
        # Default fallback
        return 'control_openpose'
    
    async def _select_preprocessor(self, animation_type: AnimationType) -> str:
        """Select best preprocessor for animation type"""
        available_preprocessors = await self.get_available_preprocessors()
        
        # Prefer pose preprocessors for character animations
        pose_preprocessors = ['openpose_full', 'openpose', 'openpose_face']
        for preprocessor in pose_preprocessors:
            if preprocessor in available_preprocessors:
                return preprocessor
        
        # Fall back to edge detection
        edge_preprocessors = ['canny', 'mlsd', 'hed']
        for preprocessor in edge_preprocessors:
            if preprocessor in available_preprocessors:
                return preprocessor
        
        # Use first available
        if available_preprocessors:
            return available_preprocessors[0]
        
        # Default fallback
        return 'openpose_full'
    
    def _build_controlnet_prompt(
        self, 
        character_description: str, 
        animation_type: AnimationType,
        direction: Direction, 
        frame_index: int
    ) -> str:
        """Build prompt optimized for ControlNet"""
        # Get pose description
        pose_description = self.template_renderer.render_for_prompt(
            animation_type, direction, frame_index
        )
        
        # Build base prompt
        base_prompt = self._build_base_prompt(character_description, animation_type, direction, frame_index)
        
        # Add ControlNet-specific instructions
        controlnet_instructions = [
            "follow the pose structure exactly",
            "maintain character proportions",
            "pixel art style",
            "clean linework",
            "vibrant colors",
            "solid color background"
        ]
        
        # Combine everything
        controlnet_prompt = f"{base_prompt}, {pose_description}, {', '.join(controlnet_instructions)}"
        
        return controlnet_prompt
    
    def get_capabilities(self) -> GuidanceCapabilities:
        """Get capabilities of ControlNet guidance"""
        # Check availability synchronously (will be updated by async calls)
        available = self._controlnet_available if self._controlnet_available is not None else False
        
        return GuidanceCapabilities(
            method=AnimationGuidanceMethod.CONTROLNET,
            available=available,
            requires_models=['controlnet_extension'],
            quality_rating=0.9,  # Highest quality
            speed_rating=0.5,  # Slower due to ControlNet processing
            consistency_rating=0.95,  # Excellent consistency
            notes="Highest quality method, requires ControlNet extension"
        )
    
    def get_guidance_method(self) -> AnimationGuidanceMethod:
        return AnimationGuidanceMethod.CONTROLNET
    
    async def generate_with_pose_control(
        self,
        character_description: str,
        animation_type: AnimationType,
        direction: Direction,
        frame_index: int,
        pose_image: Image.Image,
        **kwargs
    ) -> Tuple[Optional[Image.Image], Dict[str, Any]]:
        """Generate frame using custom pose image"""
        try:
            if not await self.is_controlnet_available():
                logger.warning("ControlNet not available, falling back to template guidance")
                return await self.template_guidance.generate_frame(
                    character_description, animation_type, direction, frame_index,
                    None, None, **kwargs
                )
            
            # Select ControlNet model
            controlnet_model = await self._select_controlnet_model(animation_type)
            preprocessor = await self._select_preprocessor(animation_type)
            
            # Build prompt
            prompt = self._build_controlnet_prompt(character_description, animation_type, direction, frame_index)
            
            # Apply LoRA if specified
            lora_name = kwargs.get('lora_name')
            lora_weight = kwargs.get('lora_weight', 1.0)
            if lora_name:
                prompt = self._apply_lora_to_prompt(prompt, lora_name, lora_weight)
            
            # Generate using custom pose
            result = await self.sd_client.generate_with_controlnet(
                GenerationParams(
                    prompt=prompt,
                    negative_prompt=self._get_negative_prompt(),
                    preset="character_sprite",
                    lora=lora_name,
                    lora_weight=lora_weight,
                    width=kwargs.get('width', 512),
                    height=kwargs.get('height', 512),
                    steps=kwargs.get('steps', 35),
                    cfg_scale=kwargs.get('cfg_scale', 8.0),
                    seed=kwargs.get('seed', -1),
                    batch_size=1
                ),
                pose_image,
                controlnet_model,
                preprocessor,
                kwargs.get('control_weight', 1.0),
                kwargs.get('guidance_start', 0.0),
                kwargs.get('guidance_end', 1.0)
            )
            
            if result and 'images' in result and len(result['images']) > 0:
                image = result['images'][0]
                quality_score = self._calculate_quality_score(image, {})
                
                metadata = {
                    'method': 'controlnet_custom_pose',
                    'quality_score': quality_score,
                    'prompt_used': prompt,
                    'controlnet_model': controlnet_model,
                    'preprocessor': preprocessor,
                    'custom_pose_used': True,
                    'seed': result.get('seed', -1)
                }
                
                return image, metadata
            else:
                return None, {'error': 'No image generated'}
                
        except Exception as e:
            logger.error(f"Error in custom pose ControlNet generation: {e}")
            return None, {'error': str(e)}
    
    async def get_controlnet_info(self) -> Dict[str, Any]:
        """Get ControlNet system information"""
        try:
            models = await self.get_available_models()
            preprocessors = await self.get_available_preprocessors()
            
            return {
                'available': await self.is_controlnet_available(),
                'models': models,
                'preprocessors': preprocessors,
                'preferred_models': self.preferred_models,
                'default_preprocessor': self.preprocessor
            }
        except Exception as e:
            logger.error(f"Error getting ControlNet info: {e}")
            return {
                'available': False,
                'models': [],
                'preprocessors': [],
                'error': str(e)
            }

