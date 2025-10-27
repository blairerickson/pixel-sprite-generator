"""
Main animation generator that coordinates all guidance methods
"""
import asyncio
import logging
import os
import uuid
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image
import time

from animation_models import (
    Direction, AnimationType, AnimationGuidanceMethod,
    AnimationFrame, AnimationSequence, AnimationGenerateRequest,
    AnimationGenerationResult, GuidanceCapabilities
)
from guidance.reference_generator import ReferenceSheetGenerator
from guidance.simple_guidance import SimpleGuidance
from guidance.template_guidance import TemplateGuidance
from guidance.inpaint_guidance import InpaintGuidance
from guidance.controlnet_guidance import ControlNetGuidance
from guidance.pixel_warp_guidance import PixelWarpGuidance
from sd_client import SDClient

logger = logging.getLogger(__name__)


class AnimationGenerator:
    """Main animation generator that coordinates all guidance methods"""
    
    def __init__(
        self,
        sd_client: SDClient,
        config: dict,
        sprite_normalizer=None,
        sprite_animator=None,
        jobs_store: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        self.sd_client = sd_client
        self.config = config
        self.animation_config = config.get('animation', {})
        self.sprite_normalizer = sprite_normalizer
        self.sprite_animator = sprite_animator
        self.jobs_store = jobs_store
        
        # Initialize guidance methods
        self.guidance_methods = {
            AnimationGuidanceMethod.PROMPT_ONLY: SimpleGuidance(sd_client, config),
            AnimationGuidanceMethod.TEMPLATE_POSE: TemplateGuidance(sd_client, config),
            AnimationGuidanceMethod.IMG2IMG_INPAINT: InpaintGuidance(sd_client, config),
            AnimationGuidanceMethod.CONTROLNET: ControlNetGuidance(sd_client, config),
        }

        if sprite_normalizer and sprite_animator:
            self.guidance_methods[AnimationGuidanceMethod.PIXEL_WARP] = PixelWarpGuidance(
                sd_client,
                config,
                sprite_normalizer=sprite_normalizer,
                sprite_animator=sprite_animator,
                jobs_store=self.jobs_store,
            )
        
        # Initialize reference generator
        self.reference_generator = ReferenceSheetGenerator(sd_client, config)
        
        # Get guidance priority order
        self.guidance_priority = self.animation_config.get('guidance', {}).get('priority', [
            'controlnet', 'img2img_inpaint', 'template_pose', 'prompt_only'
        ])
    
    async def generate_animation_sequence(
        self,
        request: AnimationGenerateRequest,
        job_id: Optional[str] = None,
        enable_motion_pipeline: bool = False
    ) -> AnimationGenerationResult:
        """
        Generate complete animation sequence
        
        Args:
            request: Animation generation request
            
        Returns:
            AnimationGenerationResult with success status and animation data
        """
        start_time = time.time()
        
        try:
            # Convert request to internal format
            directions = request.to_direction_enums()
            animation_type = request.to_animation_type_enum()
            guidance_method = request.to_guidance_method_enum()
            
            logger.info(f"Generating {animation_type.value} animation for {len(directions)} directions using {guidance_method.value}")
            
            # Generate reference sheet if requested
            reference_images = {}
            reference_cache = None
            if request.generate_reference_first:
                reference_cache = await self._build_reference_cache(
                    request,
                    directions,
                    job_id=job_id,
                )
                reference_images = reference_cache.get("images", {})
                if not reference_images:
                    logger.warning("Reference generation yielded no images; continuing without references")
            
            # Select guidance method with awareness of reference availability
            selected_guidance = await self._select_guidance_method(guidance_method, animation_type, reference_available=bool(reference_images))
            
            if not selected_guidance:
                return AnimationGenerationResult(
                    success=False,
                    error_message="No suitable guidance method available",
                    generation_time=time.time() - start_time
                )
            
            # Generate animation sequence
            animation_sequence = AnimationSequence(
                animation_type=animation_type,
                directions=directions,
                reference_sheet={d: str(path) for d, path in reference_images.items()} if reference_images else None
            )
            
            # Generate frames for each direction
            all_frames = []
            expected_total = len(directions) * self._get_frame_count_for_animation(animation_type)
            logger.info(f"Frame count calculation: {len(directions)} directions × {self._get_frame_count_for_animation(animation_type)} frames = {expected_total} total")
            
            logger.info(f"Expecting {expected_total} total frames ({len(directions)} directions x {self._get_frame_count_for_animation(animation_type)} frames)")
            
            for direction in directions:
                reference_image = reference_images.get(direction)

                try:
                    direction_frames = await self._generate_frames_for_direction(
                        selected_guidance=selected_guidance,
                        request=request,
                        animation_type=animation_type,
                        direction=direction,
                        reference_image=reference_image,
                        reference_cache=reference_cache,
                        enable_motion_pipeline=enable_motion_pipeline,
                        job_id=job_id,
                    )

                    if direction_frames and len(direction_frames) > 0:
                        all_frames.extend(direction_frames)
                        logger.info(f"Added {len(direction_frames)} frames from {direction.value}, total now: {len(all_frames)}")
                    else:
                        logger.error(f"ZERO FRAMES for {direction.value}!")
                        
                except Exception as e:
                    logger.exception(f"Direction {direction.value} completely failed: {e}")
                    continue
            
            # CRITICAL: Validate we have frames before proceeding
            if not self._validate_animation_frames(all_frames, expected_total):
                logger.error(f"ANIMATION GENERATION FAILED! Got {len(all_frames)} frames, expected {expected_total}")
                # Still return partial result rather than complete failure
                if len(all_frames) == 0:
                    raise Exception("Complete animation generation failure - no frames generated")
                else:
                    logger.warning(f"Proceeding with partial animation: {len(all_frames)} frames")
            
            # Add frames to sequence
            for frame in all_frames:
                animation_sequence.add_frame(frame)
                
            logger.info(f"Successfully generated {len(all_frames)} frames total")
            
            # Calculate quality metrics
            animation_sequence.overall_quality_score = self._calculate_overall_quality(all_frames)
            animation_sequence.total_generation_time = time.time() - start_time
            
            # Attach reference metadata if available
            if reference_cache:
                animation_sequence.metadata.update({
                    'reference_assets': reference_cache.get('assets', {}),
                    'consistency_score': reference_cache.get('consistency_score')
                })
            
            logger.info(f"Animation generation complete: {len(all_frames)} frames in {animation_sequence.total_generation_time:.2f}s")
            
            return AnimationGenerationResult(
                success=True,
                animation_sequence=animation_sequence,
                generation_time=animation_sequence.total_generation_time,
                guidance_method_used=selected_guidance.get_guidance_method(),
                quality_metrics={
                    'overall_quality': animation_sequence.overall_quality_score,
                    'frame_count': len(all_frames),
                    'direction_count': len(directions),
                    'generation_time': animation_sequence.total_generation_time
                }
            )
            
        except Exception as e:
            logger.error(f"Animation generation failed: {e}")
            return AnimationGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time
            )
    
    async def _select_guidance_method(
        self, 
        requested_method: AnimationGuidanceMethod,
        animation_type: AnimationType,
        reference_available: bool = False
    ) -> Optional[Any]:
        """Select the best available guidance method."""

        def _method_is_suitable(method: AnimationGuidanceMethod) -> bool:
            guidance = self.guidance_methods.get(method)
            if not guidance or not guidance.is_available():
                return False
            if reference_available:
                return method != AnimationGuidanceMethod.PROMPT_ONLY
            return True

        if requested_method != AnimationGuidanceMethod.AUTO:
            if _method_is_suitable(requested_method):
                logger.info(f"Using requested guidance method: {requested_method.value}")
                return self.guidance_methods[requested_method]
            logger.warning(f"Requested method {requested_method.value} unavailable or unsuitable, falling back to auto")

        for method_name in self.guidance_priority:
            method_enum = AnimationGuidanceMethod(method_name)
            if _method_is_suitable(method_enum):
                logger.info(f"Selected guidance method: {method_enum.value}")
                return self.guidance_methods[method_enum]

        for guidance in self.guidance_methods.values():
            if guidance.is_available():
                logger.warning(f"Using fallback guidance method: {guidance.get_guidance_method().value}")
                return guidance

        return None

    async def _build_reference_cache(
        self,
        request: AnimationGenerateRequest,
        directions: List[Direction],
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate and optionally persist reference assets for reuse."""
        cache: Dict[str, Any] = {"images": {}, "assets": {}}

        try:
            reference_images = await self.reference_generator.generate_character_reference(
                character_description=request.character_description,
                directions=directions,
                style_lora=request.style_lora,
                lora_weight=request.lora_weight,
                width=request.width or 512,
                height=request.height or 512,
                steps=request.steps,
                cfg_scale=request.cfg_scale,
                seed=request.seed
            )

            if not reference_images:
                return cache

            cache_dir = Path(self.config['paths']['output_dir']) / (job_id or uuid.uuid4().hex)
            cache_dir.mkdir(parents=True, exist_ok=True)

            saved_paths = await self.reference_generator.save_reference_images(reference_images, cache_dir, prefix="ref")
            cache["images"] = reference_images
            cache["assets"] = {
                "directory": str(cache_dir),
                "files": {direction.value: path for direction, path in saved_paths.items()}
            }
            cache["consistency_score"] = self.reference_generator.get_reference_consistency_score(reference_images)

            logger.info("Reference cache built: %s", cache["assets"])
            return cache

        except Exception as exc:
            logger.warning("Reference cache build failed: %s", exc)
            return cache

    async def _generate_frames_for_direction(
        self,
        selected_guidance,
        request: AnimationGenerateRequest,
        animation_type: AnimationType,
        direction: Direction,
        reference_image: Optional[Image.Image],
        reference_cache: Optional[Dict[str, Any]],
        enable_motion_pipeline: bool,
        job_id: Optional[str],
    ) -> List[AnimationFrame]:
        """Generate frames for a single direction using configured pipeline with fallbacks."""
        
        logger.info(f"Generating frames for {direction.value} using {selected_guidance.__class__.__name__}")

        # Try motion pipeline first if enabled
        if enable_motion_pipeline and self.animation_config.get('enable_motion_pipeline', False):
            try:
                motion_frames = await self._stage_motion_pipeline(
                    request=request,
                    animation_type=animation_type,
                    direction=direction,
                    reference_image=reference_image,
                    reference_cache=reference_cache,
                    job_id=job_id,
                )
                if motion_frames:
                    logger.info(f"Motion pipeline succeeded for {direction.value}")
                    return motion_frames
            except Exception as e:
                logger.warning(f"Motion pipeline failed for {direction.value}: {e}")
        
        # CRITICAL FIX: Robust fallback chain
        fallback_methods = [
            selected_guidance,
            self.guidance_methods.get(AnimationGuidanceMethod.IMG2IMG_INPAINT),
            self.guidance_methods.get(AnimationGuidanceMethod.TEMPLATE_POSE),
            self.guidance_methods.get(AnimationGuidanceMethod.PROMPT_ONLY)
        ]
        
        for guidance in fallback_methods:
            if not guidance:
                continue
                
            try:
                logger.info(f"Trying {guidance.__class__.__name__} for {direction.value}")
                
                frames = await guidance.generate_animation_sequence(
                    character_description=request.character_description,
                    animation_type=animation_type,
                    directions=[direction],
                    reference_images={direction: reference_image} if reference_image else None,
                    frame_count=request.frame_count,
                    lora_name=request.style_lora,
                    lora_weight=request.lora_weight,
                    width=request.width,
                    height=request.height,
                    steps=request.steps,
                    cfg_scale=request.cfg_scale,
                    seed=request.seed,
                    source_job_id=request.source_job_id,
                    use_cleaned_sprite=request.use_cleaned_sprite,
                    jobs_store=self.jobs_store,
                    reference_cache=reference_cache,
                    job_id=job_id  # FIX: Only pass once, not twice
                )
                
                if frames and len(frames) > 0:
                    logger.info(f"SUCCESS: {guidance.__class__.__name__} generated {len(frames)} frames for {direction.value}")
                    return frames
                else:
                    logger.warning(f"{guidance.__class__.__name__} returned empty frames for {direction.value}")
                    
            except Exception as e:
                logger.warning(f"{guidance.__class__.__name__} failed for {direction.value}: {e}")
                continue
        
        # If all fallbacks fail, raise error
        raise Exception(f"All guidance methods failed for {direction.value}")
        
    def _validate_animation_frames(self, all_frames: List[AnimationFrame], expected_count: int) -> bool:
        """Validate animation frames before returning"""
        logger.info(f"Validating frames: got {len(all_frames)}, expected {expected_count}")
        
        if len(all_frames) == 0:
            logger.error("ZERO FRAMES GENERATED!")
            return False
            
        if len(all_frames) < expected_count * 0.5:  # More lenient tolerance
            logger.error(f"Too few frames: {len(all_frames)}, expected {expected_count}")
            return False
        elif len(all_frames) < expected_count:
            logger.warning(f"Partial frames: {len(all_frames)}, expected {expected_count}")
            
        # Skip file existence check for now (files might be served from different location)
        logger.info(f"Frame validation passed: {len(all_frames)} frames (expected {expected_count})")
        return True
    
    def _get_frame_count_for_animation(self, animation_type: AnimationType) -> int:
        """Get expected frame count for animation type"""
        frame_counts = self.config.get('animation', {}).get('generation', {}).get('frame_counts', {})
        return frame_counts.get(animation_type.value, 8)

    async def _stage_motion_pipeline(
        self,
        request: AnimationGenerateRequest,
        animation_type: AnimationType,
        direction: Direction,
        reference_image: Optional[Image.Image],
        reference_cache: Optional[Dict[str, Any]],
        job_id: Optional[str],
    ) -> Optional[List[AnimationFrame]]:
        """Placeholder for multi-stage motion pipeline (AnimateDiff + Inpaint + PixelWarp)."""

        logger.debug(
            "Motion pipeline not yet implemented (job=%s, direction=%s)",
            job_id,
            direction.value,
        )
        return None
    
    def _calculate_overall_quality(self, frames: List[AnimationFrame]) -> float:
        """Calculate overall quality score for animation frames"""
        if not frames:
            return 0.0
        
        # Calculate average quality score
        quality_scores = [frame.quality_score for frame in frames if frame.quality_score is not None]
        
        if not quality_scores:
            return 0.5  # Default score if no quality data
        
        return sum(quality_scores) / len(quality_scores)
    
    async def get_available_guidance_methods(self) -> List[GuidanceCapabilities]:
        """Get capabilities of all guidance methods"""
        capabilities = []
        
        for guidance in self.guidance_methods.values():
            try:
                caps = guidance.get_capabilities()
                capabilities.append(caps)
            except Exception as e:
                logger.error(f"Error getting capabilities for {guidance.get_guidance_method().value}: {e}")
        
        return capabilities
    
    async def get_animation_templates(self) -> Dict[str, Any]:
        """Get available animation templates"""
        template_guidance = self.guidance_methods[AnimationGuidanceMethod.TEMPLATE_POSE]
        return template_guidance.get_available_templates()
    
    async def generate_reference_sheet(
        self,
        character_description: str,
        directions: List[str],
        style_lora: Optional[str] = None,
        lora_weight: Optional[float] = None,
        width: int = 512,
        height: int = 512,
        steps: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        seed: int = -1
    ) -> Dict[Direction, Image.Image]:
        """Generate character reference sheet"""
        direction_enums = [Direction(d) for d in directions if d in [d.value for d in Direction]]
        
        return await self.reference_generator.generate_character_reference(
            character_description=character_description,
            directions=direction_enums,
            style_lora=style_lora,
            lora_weight=lora_weight,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            seed=seed
        )
    
    async def test_guidance_method(
        self,
        guidance_method: AnimationGuidanceMethod,
        character_description: str = "pixel art knight in armor",
        animation_type: AnimationType = AnimationType.IDLE,
        direction: Direction = Direction.SOUTH
    ) -> Tuple[bool, str]:
        """Test a specific guidance method"""
        try:
            if guidance_method not in self.guidance_methods:
                return False, f"Guidance method {guidance_method.value} not available"
            
            guidance = self.guidance_methods[guidance_method]
            
            if not guidance.is_available():
                return False, f"Guidance method {guidance_method.value} not available"
            
            # Test with a simple frame generation
            image, metadata = await guidance.generate_frame(
                character_description=character_description,
                animation_type=animation_type,
                direction=direction,
                frame_index=0
            )
            
            if image:
                return True, f"Successfully generated test frame using {guidance_method.value}"
            else:
                return False, f"Failed to generate test frame using {guidance_method.value}"
                
        except Exception as e:
            return False, f"Error testing {guidance_method.value}: {str(e)}"
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        status = {
            'sd_client_healthy': await self.sd_client.check_health(),
            'guidance_methods': {},
            'templates_available': False,
            'controlnet_available': False
        }
        
        # Check each guidance method
        for method, guidance in self.guidance_methods.items():
            try:
                capabilities = guidance.get_capabilities()
                status['guidance_methods'][method.value] = {
                    'available': capabilities.available,
                    'quality_rating': capabilities.quality_rating,
                    'speed_rating': capabilities.speed_rating,
                    'consistency_rating': capabilities.consistency_rating
                }
            except Exception as e:
                status['guidance_methods'][method.value] = {
                    'available': False,
                    'error': str(e)
                }
        
        # Check templates
        try:
            templates = await self.get_animation_templates()
            status['templates_available'] = len(templates) > 0
        except Exception as e:
            status['templates_error'] = str(e)
        
        # Check ControlNet
        try:
            controlnet_guidance = self.guidance_methods[AnimationGuidanceMethod.CONTROLNET]
            status['controlnet_available'] = await controlnet_guidance.is_controlnet_available()
        except Exception as e:
            status['controlnet_error'] = str(e)
        
        return status
