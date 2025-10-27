"""
Quality-First Animation Generator
Focuses on character consistency and proper animation logic
"""
import logging
from typing import Dict, List, Optional, Any
from PIL import Image
from pathlib import Path
import time

from animation_models import (
    AnimationType, Direction, AnimationFrame, AnimationSequence, 
    AnimationGenerationResult, AnimationGenerateRequest
)
from sd_client import SDClient, GenerationParams
from character_consistency import CharacterConsistencyManager
from animation_poses import WalkAnimationPoses, WalkPose

logger = logging.getLogger(__name__)


class QualityAnimationGenerator:
    """Professional animation generator focused on quality and consistency"""
    
    def __init__(self, sd_client: SDClient, config: dict):
        self.sd_client = sd_client
        self.config = config
        self.character_manager = CharacterConsistencyManager(sd_client, config)
        self.pose_manager = WalkAnimationPoses()
        
    async def generate_coherent_animation(
        self, 
        request: AnimationGenerateRequest,
        job_id: Optional[str] = None
    ) -> AnimationGenerationResult:
        """Generate coherent animation with character consistency"""
        
        start_time = time.time()
        logger.info(f"Starting QUALITY animation generation for {request.character_description}")
        logger.info(f"Animation type: {request.animation_type}, Directions: {request.directions}")
        
        try:
            # Enforce frame limits to prevent over-generation
            from frame_count_controller import FrameCountController
            frame_controller = FrameCountController()
            
            frames_per_dir, num_dirs, total_expected = frame_controller.get_frame_limits(
                request.animation_type, 
                "4dir"  # Hardcode to 4dir for now
            )
            
            # Phase 1: Generate and validate master character
            logger.info("Phase 1: Generating master character...")
            master = await self.character_manager.generate_master_character(
                description=request.character_description,
                seed=request.seed,
                style_lora=request.style_lora,
                lora_weight=request.lora_weight,
                width=request.width or 512,
                height=request.height or 512
            )
            
            if not self._validate_character_quality(master):
                raise Exception("Master character quality too low")
            
            # Phase 2: Generate directional references
            logger.info("Phase 2: Generating directional references...")
            references = await self.character_manager.generate_directional_references(
                master_character=master,
                description=request.character_description,
                seed=request.seed,
                style_lora=request.style_lora,
                lora_weight=request.lora_weight
            )
            
            # Validate character consistency
            consistency_score = self.character_manager.validate_character_consistency(references)
            logger.info(f"Character consistency score: {consistency_score:.2f}")
            
            if consistency_score < 0.6:  # Lenient threshold for now
                logger.warning(f"Character consistency below ideal ({consistency_score:.2f}), proceeding anyway")
            
            # Phase 3: Generate walking animation frames with limits
            logger.info("Phase 3: Generating walking animation frames...")
            all_frames = await self._generate_animation_frames(
                references=references,
                request=request,
                job_id=job_id,
                frames_per_direction=frames_per_dir,
                max_total_frames=total_expected
            )
            
            # Phase 4: Build final result
            logger.info(f"Phase 4: Building final animation result...")
            animation_sequence = AnimationSequence(
                animation_type=AnimationType(request.animation_type),
                directions=[Direction(d) for d in request.directions],
                reference_sheet=references
            )
            
            for frame in all_frames:
                animation_sequence.add_frame(frame)
            
            animation_sequence.overall_quality_score = consistency_score
            animation_sequence.total_generation_time = time.time() - start_time
            
            logger.info(f"QUALITY animation complete: {len(all_frames)} frames in {animation_sequence.total_generation_time:.2f}s")
            
            return AnimationGenerationResult(
                success=True,
                animation_sequence=animation_sequence,
                generation_time=animation_sequence.total_generation_time,
                quality_metrics={
                    "character_consistency": consistency_score,
                    "frame_count": len(all_frames),
                    "generation_time": animation_sequence.total_generation_time
                }
            )
            
        except Exception as e:
            logger.exception(f"Quality animation generation failed: {e}")
            return AnimationGenerationResult(
                success=False,
                error_message=str(e),
                generation_time=time.time() - start_time
            )
    
    async def _generate_animation_frames(
        self,
        references: Dict[str, Image.Image],
        request: AnimationGenerateRequest,
        job_id: Optional[str],
        frames_per_direction: int = 8,
        max_total_frames: int = 32
    ) -> List[AnimationFrame]:
        """Generate all animation frames with pose logic and strict limits"""
        
        logger.info(f"Generating frames with STRICT LIMITS: {frames_per_direction} per direction, {max_total_frames} total")
        
        all_frames = []
        pose_sequence = self.pose_manager.get_pose_sequence(request.animation_type)
        
        # Limit pose sequence to frames_per_direction
        limited_poses = pose_sequence[:frames_per_direction]
        logger.info(f"Using {len(limited_poses)} poses (limited from {len(pose_sequence)})")
        
        # Create output directory
        if job_id:
            output_dir = Path(self.config['paths']['output_dir']) / job_id
            output_dir.mkdir(parents=True, exist_ok=True)
        
        for direction in request.directions:
            logger.info(f"Generating {len(limited_poses)} frames for {direction}")
            reference_image = references.get(direction)
            
            if not reference_image:
                logger.error(f"No reference image for {direction}")
                continue
            
            direction_frames = []
            
            for i, pose in enumerate(limited_poses):
                # Safety check: don't exceed total frame limit
                if len(all_frames) >= max_total_frames:
                    logger.warning(f"STOPPING: Reached max frame limit ({max_total_frames})")
                    break
                
                try:
                    logger.info(f"Generating {direction} frame {i+1}/{len(limited_poses)}: {pose.pose_description}")
                    
                    frame_image = await self._generate_single_pose_frame(
                        reference_image=reference_image,
                        character_description=request.character_description,
                        direction=direction,
                        pose=pose,
                        seed=request.seed + pose.frame,  # Slight variation per frame
                        lora=request.style_lora,
                        lora_weight=request.lora_weight
                    )
                    
                    if frame_image:
                        # Save frame with proper naming
                        timestamp = int(time.time() * 1000) + i  # Unique timestamp
                        filename = f"frame_{direction}_{pose.frame}_{timestamp}.png"
                        
                        if job_id:
                            frame_path = output_dir / filename
                            frame_image.save(frame_path)
                            
                            # Also save to project root for serving
                            root_path = Path(self.config['paths']['output_dir']).parent / filename
                            frame_image.save(root_path)
                        
                        # Create AnimationFrame object
                        frame_obj = AnimationFrame(
                            image_url=f"/{filename}",
                            direction=Direction(direction),
                            frame_index=pose.frame,
                            animation_type=AnimationType(request.animation_type),
                            seed=request.seed + pose.frame,
                            guidance_method=None,
                            quality_score=0.8,
                            generation_time=0.0,
                            metadata={
                                "pose_description": pose.pose_description,
                                "weight_shift": pose.weight_shift,
                                "method": "quality_generation"
                            }
                        )
                        
                        direction_frames.append(frame_obj)
                        all_frames.append(frame_obj)
                        
                        logger.info(f"SUCCESS: {direction} frame {pose.frame} generated")
                        
                    else:
                        logger.error(f"Failed to generate {direction} frame {pose.frame}")
                        
                except Exception as e:
                    logger.error(f"Failed to generate {direction} frame {pose.frame}: {e}")
                    continue
            
            logger.info(f"Completed {len(direction_frames)} frames for {direction}")
            
            # Safety check: don't exceed total frame limit
            if len(all_frames) >= max_total_frames:
                logger.warning(f"Reached max frame limit, stopping generation")
                break
        
        logger.info(f"Generated {len(all_frames)} total animation frames (limit was {max_total_frames})")
        
        # Validate final frame count
        from frame_count_controller import FrameCountController
        frame_controller = FrameCountController()
        is_valid = frame_controller.validate_frame_count(len(all_frames), max_total_frames)
        
        if not is_valid:
            logger.warning(f"Frame count validation failed, but proceeding with {len(all_frames)} frames")
        
        return all_frames
    
    async def _generate_single_pose_frame(
        self,
        reference_image: Image.Image,
        character_description: str,
        direction: str,
        pose: WalkPose,
        seed: int,
        lora: Optional[str] = None,
        lora_weight: float = 1.0
    ) -> Optional[Image.Image]:
        """Generate single frame with specific pose"""
        
        try:
            # Build SUPER-SPECIFIC pose prompt for consistency
            base_prompt = f"EXACT SAME CHARACTER: {character_description}"
            
            direction_text = {
                "south": "facing forward",
                "west": "facing left", 
                "east": "facing right",
                "north": "facing backward"
            }.get(direction, "facing forward")
            
            # Enhanced pose prompt with character consistency enforcement
            consistency_prompt = (
                f"{base_prompt}, IDENTICAL to reference image, "
                f"MAINTAIN: same armor design, same color scheme, same facial features, "
                f"same body proportions, same equipment details, "
                f"{direction_text}, {pose.pose_description}, "
                f"walking animation frame {pose.frame + 1}, "
                f"pixel art sprite, character consistency priority"
            )
            
            logger.info(f"Enhanced prompt: {consistency_prompt[:100]}...")
            
            # Generate with very high consistency parameters
            params = GenerationParams(
                prompt=consistency_prompt,
                negative_prompt=self._get_negative_prompt() + ", different character, character inconsistency, design variation",
                preset="character_sprite",
                lora=lora,
                lora_weight=lora_weight,
                width=reference_image.width,
                height=reference_image.height,
                steps=30,  # Higher steps for consistency
                cfg_scale=9.0,  # Very high adherence to prompt
                seed=seed,  # Same base seed
                batch_size=1
            )
            
            # Use regular generation with enhanced prompts
            result = await self.sd_client.generate(params)
            
            if result and 'images' in result and len(result['images']) > 0:
                return result['images'][0]
            else:
                logger.error(f"No image generated for pose {pose.frame}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating pose frame: {e}")
            return None
    
    def _validate_character_quality(self, character_image: Image.Image) -> bool:
        """Validate that character meets quality standards"""
        try:
            # Basic quality checks
            if character_image.size != (512, 512):
                logger.warning("Character image wrong size")
                return False
            
            # Check if image has content (not blank)
            if self._is_blank_image(character_image):
                logger.error("Character image is blank")
                return False
            
            logger.info("Character quality validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Character quality validation failed: {e}")
            return False
    
    def _is_blank_image(self, image: Image.Image) -> bool:
        """Check if image is mostly blank/empty"""
        try:
            # Convert to grayscale and check if mostly one color
            gray = image.convert('L')
            hist = gray.histogram()
            
            # If 90% of pixels are the same color, consider blank
            max_count = max(hist)
            total_pixels = gray.width * gray.height
            
            return max_count > (total_pixels * 0.9)
            
        except Exception:
            return False
    
    def _get_negative_prompt(self) -> str:
        """Get negative prompt for animation generation"""
        return (
            "blurry, low quality, jpeg artifacts, multiple characters, "
            "inconsistent character, bad anatomy, deformed, extra limbs, "
            "wrong number of arms, wrong number of legs, floating limbs"
        )
