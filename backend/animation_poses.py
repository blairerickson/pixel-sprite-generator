"""
Walking Animation Pose System
Defines proper walking cycles with realistic motion
"""
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WalkPose:
    """Represents a single pose in a walking animation"""
    frame: int
    pose_description: str
    weight_shift: str
    foot_position: str
    body_lean: str


class WalkAnimationPoses:
    """Defines proper walking animation sequences"""
    
    def __init__(self):
        self.walk_cycle = self._define_walk_cycle()
    
    def _define_walk_cycle(self) -> List[WalkPose]:
        """Define 8-frame walking cycle with proper biomechanics"""
        return [
            WalkPose(
                frame=0,
                pose_description="standing ready, neutral stance",
                weight_shift="center",
                foot_position="feet together",
                body_lean="upright"
            ),
            WalkPose(
                frame=1, 
                pose_description="left foot lifting, stepping forward",
                weight_shift="right",
                foot_position="left foot raised",
                body_lean="slight lean forward"
            ),
            WalkPose(
                frame=2,
                pose_description="left foot extended forward, about to contact",
                weight_shift="right", 
                foot_position="left foot forward",
                body_lean="lean forward"
            ),
            WalkPose(
                frame=3,
                pose_description="left foot planted, weight transferring",
                weight_shift="left",
                foot_position="left foot planted forward",
                body_lean="upright"
            ),
            WalkPose(
                frame=4,
                pose_description="right foot lifting, stepping forward",
                weight_shift="left",
                foot_position="right foot raised",
                body_lean="slight lean forward"
            ),
            WalkPose(
                frame=5,
                pose_description="right foot extended forward, about to contact",
                weight_shift="left",
                foot_position="right foot forward", 
                body_lean="lean forward"
            ),
            WalkPose(
                frame=6,
                pose_description="right foot planted, weight transferring",
                weight_shift="right",
                foot_position="right foot planted forward",
                body_lean="upright"
            ),
            WalkPose(
                frame=7,
                pose_description="returning to neutral, cycle completing",
                weight_shift="center",
                foot_position="feet together",
                body_lean="upright"
            )
        ]
    
    def get_walk_sequence(self) -> List[WalkPose]:
        """Get the complete 8-frame walking sequence"""
        return self.walk_cycle
    
    def build_pose_prompt(
        self, 
        character_description: str, 
        direction: str, 
        pose: WalkPose
    ) -> str:
        """Build ENHANCED prompt for character consistency"""
        
        # Direction-specific facing
        direction_text = {
            "south": "facing forward, front view",
            "west": "facing left, side view from right",
            "east": "facing right, side view from left", 
            "north": "facing backward, back view"
        }.get(direction, "facing forward")
        
        # ENHANCED: Build super-specific prompt for consistency
        base_character = f"EXACT SAME CHARACTER: {character_description}"
        consistency_requirements = (
            "MAINTAIN ALL: armor design, color scheme, facial features, "
            "body proportions, equipment details, character identity"
        )
        
        pose_prompt = (
            f"{base_character}, {consistency_requirements}, "
            f"{direction_text}, {pose.pose_description}, "
            f"{pose.foot_position}, {pose.body_lean}, "
            f"walking animation frame {pose.frame + 1}, "
            f"pixel art sprite, character consistency priority, "
            f"same character different pose only"
        )
        
        logger.info(f"Enhanced pose prompt for {direction} frame {pose.frame}")
        return pose_prompt
    
    def get_run_sequence(self) -> List[WalkPose]:
        """Get running animation sequence (faster, more dynamic)"""
        return [
            WalkPose(0, "running start stance", "center", "feet together", "lean forward"),
            WalkPose(1, "left leg pushing off", "right", "left foot back", "lean forward"),
            WalkPose(2, "airborne phase, left leg forward", "center", "left foot forward", "lean forward"),
            WalkPose(3, "left foot landing", "left", "left foot planted", "upright"),
            WalkPose(4, "right leg pushing off", "left", "right foot back", "lean forward"),
            WalkPose(5, "airborne phase, right leg forward", "center", "right foot forward", "lean forward"),
            WalkPose(6, "right foot landing", "right", "right foot planted", "upright"),
            WalkPose(7, "cycle return", "center", "ready for next stride", "lean forward")
        ]
    
    def get_idle_sequence(self) -> List[WalkPose]:
        """Get idle/breathing animation sequence"""
        return [
            WalkPose(0, "standing relaxed, breathing in", "center", "feet apart", "upright"),
            WalkPose(1, "breathing out, slight movement", "center", "feet apart", "slight lean"),
            WalkPose(2, "breathing in return", "center", "feet apart", "upright"),
            WalkPose(3, "breathing out return", "center", "feet apart", "slight lean")
        ]
    
    def get_pose_sequence(self, animation_type: str) -> List[WalkPose]:
        """Get appropriate pose sequence for animation type"""
        sequences = {
            "walk": self.get_walk_sequence(),
            "run": self.get_run_sequence(),
            "idle": self.get_idle_sequence()
        }
        
        return sequences.get(animation_type, self.get_walk_sequence())
