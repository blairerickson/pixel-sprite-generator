"""
Frame Count Controller
Enforces strict limits to prevent over-generation
"""
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class FrameCountController:
    """Controls frame generation limits and prevents over-generation"""
    
    def __init__(self):
        self.frame_limits = {
            "walk": 8,
            "run": 8,
            "idle": 4, 
            "attack": 6,
            "cast_spell": 8,
            "death": 6,
            "jump": 4,
            "crouch": 3,
            "hurt": 4
        }
        
        self.direction_limits = {
            "4dir": 4,
            "8dir": 8
        }
    
    def get_frame_limits(self, animation_type: str, direction_mode: str = "4dir") -> Tuple[int, int, int]:
        """Get enforced frame limits for animation"""
        
        frames_per_direction = self.frame_limits.get(animation_type, 8)
        num_directions = self.direction_limits.get(direction_mode, 4) 
        total_expected = frames_per_direction * num_directions
        
        logger.info(f"FRAME LIMITS: {animation_type} = {frames_per_direction} frames/direction")
        logger.info(f"DIRECTION LIMITS: {direction_mode} = {num_directions} directions")
        logger.info(f"TOTAL EXPECTED: {frames_per_direction} × {num_directions} = {total_expected} frames")
        
        return frames_per_direction, num_directions, total_expected
    
    def validate_frame_count(
        self, 
        generated_frames: int,
        expected_frames: int,
        tolerance: float = 0.1
    ) -> bool:
        """Validate that frame count is within expected range"""
        
        min_acceptable = int(expected_frames * (1 - tolerance))
        max_acceptable = int(expected_frames * (1 + tolerance))
        
        is_valid = min_acceptable <= generated_frames <= max_acceptable
        
        logger.info(f"Frame count validation:")
        logger.info(f"  Generated: {generated_frames}")
        logger.info(f"  Expected: {expected_frames}")
        logger.info(f"  Range: {min_acceptable}-{max_acceptable}")
        logger.info(f"  Valid: {is_valid}")
        
        if not is_valid:
            if generated_frames > max_acceptable:
                logger.warning(f"OVER-GENERATION detected: {generated_frames} > {max_acceptable}")
            elif generated_frames < min_acceptable:
                logger.warning(f"UNDER-GENERATION detected: {generated_frames} < {min_acceptable}")
        
        return is_valid
    
    def should_stop_generation(self, current_count: int, expected_count: int) -> bool:
        """Determine if generation should stop to prevent over-generation"""
        
        if current_count >= expected_count:
            logger.warning(f"STOPPING generation: reached limit ({current_count}/{expected_count})")
            return True
        
        # Safety stop at 150% of expected
        safety_limit = int(expected_count * 1.5)
        if current_count >= safety_limit:
            logger.error(f"EMERGENCY STOP: hit safety limit ({current_count}/{safety_limit})")
            return True
        
        return False
