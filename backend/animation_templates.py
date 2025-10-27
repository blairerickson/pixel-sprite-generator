"""
Animation template system for pose guidance
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont
import logging

from animation_models import (
    AnimationType, Direction, TemplateMetadata, 
    AnimationFrame, AnimationGuidanceMethod
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages animation templates and pose data"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.templates_dir / "metadata.json"
        self.metadata: Dict[str, TemplateMetadata] = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load template metadata from JSON file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for key, meta_data in data.items():
                        self.metadata[key] = TemplateMetadata.from_dict(meta_data)
                logger.info(f"Loaded {len(self.metadata)} template metadata entries")
            except Exception as e:
                logger.error(f"Failed to load template metadata: {e}")
                self.metadata = {}
        else:
            logger.info("No template metadata found, creating default structure")
            self._create_default_metadata()
    
    def _create_default_metadata(self):
        """Create default template metadata structure"""
        # Create basic metadata for common animations
        animations = [
            (AnimationType.IDLE, 2, True, True),
            (AnimationType.WALK, 8, True, False),
            (AnimationType.RUN, 8, True, False),
            (AnimationType.ATTACK, 6, False, False),
            (AnimationType.CAST_SPELL, 8, False, False),
            (AnimationType.DEATH, 6, False, False),
            (AnimationType.STORYBOARD, 5, False, False),
        ]
        
        for anim_type, frame_count, loop, breathing in animations:
            for dir_count in [4, 8]:
                key = f"{anim_type.value}_{dir_count}dir"
                notes = []
                motion_profile = None
                if anim_type == AnimationType.STORYBOARD:
                    notes = [
                        "5-frame vignette: setup, anticipation, action, impact, settle",
                        "Use storyboard motion descriptors for limb offsets"
                    ]
                    motion_profile = "storyboard_v1"

                self.metadata[key] = TemplateMetadata(
                    animation_type=anim_type,
                    direction_count=dir_count,
                    frame_count=frame_count,
                    keyframes=self._get_keyframes(frame_count),
                    loop=loop,
                    breathing_effect=breathing,
                    template_files={},
                    motion_profile=motion_profile,
                    notes=notes,
                )
        
        self._save_metadata()
    
    def _get_keyframes(self, frame_count: int) -> List[int]:
        """Get keyframe indices for an animation"""
        if frame_count <= 2:
            return [0, frame_count - 1] if frame_count > 1 else [0]
        elif frame_count <= 4:
            return [0, frame_count // 2, frame_count - 1]
        else:
            # For longer animations, select key poses
            return [0, frame_count // 4, frame_count // 2, 3 * frame_count // 4, frame_count - 1]
    
    def _save_metadata(self):
        """Save template metadata to JSON file"""
        try:
            data = {key: meta.to_dict() for key, meta in self.metadata.items()}
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Template metadata saved")
        except Exception as e:
            logger.error(f"Failed to save template metadata: {e}")
    
    def get_template_metadata(self, animation_type: AnimationType, direction_count: int) -> Optional[TemplateMetadata]:
        """Get metadata for a specific animation type and direction count"""
        key = f"{animation_type.value}_{direction_count}dir"
        return self.metadata.get(key)
    
    def get_template_path(self, animation_type: AnimationType, direction: Direction, frame_index: int) -> Optional[Path]:
        """Get path to template file for specific animation, direction, and frame"""
        direction_count = 4 if direction in Direction.get_4_directions() else 8
        metadata = self.get_template_metadata(animation_type, direction_count)
        
        if not metadata:
            return None
        
        # Check if template file exists
        template_dir = self.templates_dir / animation_type.value / f"{direction_count}dir"
        template_file = template_dir / f"{animation_type.value}_{direction.value}_{frame_index:02d}.png"
        
        if template_file.exists():
            return template_file
        
        # If specific template doesn't exist, try to generate it
        return self._generate_template(animation_type, direction, frame_index, template_dir)
    
    def _generate_template(self, animation_type: AnimationType, direction: Direction, 
                          frame_index: int, template_dir: Path) -> Optional[Path]:
        """Generate a simple template if it doesn't exist"""
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / f"{animation_type.value}_{direction.value}_{frame_index:02d}.png"
        
        try:
            # Create a simple stick figure template
            template_img = self._create_stick_figure_template(animation_type, direction, frame_index)
            template_img.save(template_file)
            logger.info(f"Generated template: {template_file}")
            return template_file
        except Exception as e:
            logger.error(f"Failed to generate template {template_file}: {e}")
            return None
    
    def _create_stick_figure_template(self, animation_type: AnimationType, direction: Direction, 
                                    frame_index: int) -> Image.Image:
        """Create a simple stick figure template for pose guidance"""
        # Create a 256x256 transparent image
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Define stick figure proportions
        center_x, center_y = 128, 128
        head_radius = 20
        body_length = 60
        arm_length = 40
        leg_length = 50
        
        # Calculate direction offset
        direction_angle = self._get_direction_angle(direction)
        
        # Draw head
        head_x = center_x
        head_y = center_y - body_length // 2
        draw.ellipse([head_x - head_radius, head_y - head_radius, 
                     head_x + head_radius, head_y + head_radius], 
                    outline=(255, 255, 255, 255), width=2)
        
        # Draw body
        body_end_y = head_y + body_length
        draw.line([head_x, head_y, head_x, body_end_y], 
                 fill=(255, 255, 255, 255), width=2)
        
        # Draw arms based on animation type and frame
        arm_angle = self._get_arm_angle(animation_type, frame_index, direction_angle)
        left_arm_x = head_x + arm_length * arm_angle[0]
        left_arm_y = head_y + 20 + arm_length * arm_angle[1]
        right_arm_x = head_x - arm_length * arm_angle[0]
        right_arm_y = head_y + 20 + arm_length * arm_angle[1]
        
        draw.line([head_x, head_y + 20, left_arm_x, left_arm_y], 
                 fill=(255, 255, 255, 255), width=2)
        draw.line([head_x, head_y + 20, right_arm_x, right_arm_y], 
                 fill=(255, 255, 255, 255), width=2)
        
        # Draw legs based on animation type and frame
        leg_angle = self._get_leg_angle(animation_type, frame_index, direction_angle)
        left_leg_x = body_end_y + leg_length * leg_angle[0]
        left_leg_y = body_end_y + leg_length * leg_angle[1]
        right_leg_x = body_end_y - leg_length * leg_angle[0]
        right_leg_y = body_end_y + leg_length * leg_angle[1]
        
        draw.line([head_x, body_end_y, left_leg_x, left_leg_y], 
                 fill=(255, 255, 255, 255), width=2)
        draw.line([head_x, body_end_y, right_leg_x, right_leg_y], 
                 fill=(255, 255, 255, 255), width=2)
        
        return img
    
    def _get_direction_angle(self, direction: Direction) -> float:
        """Get angle offset for direction (in radians)"""
        angle_map = {
            Direction.SOUTH: 0,
            Direction.SOUTHEAST: 0.25,
            Direction.EAST: 0.5,
            Direction.NORTHEAST: 0.75,
            Direction.NORTH: 1.0,
            Direction.NORTHWEST: 1.25,
            Direction.WEST: 1.5,
            Direction.SOUTHWEST: 1.75
        }
        return angle_map.get(direction, 0) * 3.14159 * 2
    
    def _get_arm_angle(self, animation_type: AnimationType, frame_index: int, direction_angle: float) -> Tuple[float, float]:
        """Get arm angle based on animation type and frame"""
        if animation_type == AnimationType.IDLE:
            # Slight breathing motion
            breath_offset = 0.1 * (1 if frame_index % 2 == 0 else -1)
            return (0.3 + breath_offset, 0.1)
        elif animation_type == AnimationType.WALK:
            # Walking arm swing
            cycle = (frame_index % 8) / 8.0
            swing = 0.5 * (1 if cycle < 0.5 else -1)
            return (0.2 + swing, 0.3)
        elif animation_type == AnimationType.ATTACK:
            # Attack pose
            if frame_index < 2:
                return (0.1, 0.1)  # Wind up
            elif frame_index < 4:
                return (0.8, 0.2)  # Strike
            else:
                return (0.3, 0.1)  # Recovery
        else:
            return (0.3, 0.1)  # Default
    
    def _get_leg_angle(self, animation_type: AnimationType, frame_index: int, direction_angle: float) -> Tuple[float, float]:
        """Get leg angle based on animation type and frame"""
        if animation_type == AnimationType.IDLE:
            return (0.1, 0.9)  # Standing
        elif animation_type == AnimationType.WALK:
            # Walking leg cycle
            cycle = (frame_index % 8) / 8.0
            if cycle < 0.5:
                # Left leg forward
                return (0.3, 0.7)
            else:
                # Right leg forward
                return (-0.3, 0.7)
        elif animation_type == AnimationType.ATTACK:
            # Attack stance
            return (0.2, 0.8)
        else:
            return (0.1, 0.9)  # Default
    
    def get_animation_frames(self, animation_type: AnimationType, direction: Direction) -> List[AnimationFrame]:
        """Get all frames for an animation in a specific direction"""
        direction_count = 4 if direction in Direction.get_4_directions() else 8
        metadata = self.get_template_metadata(animation_type, direction_count)
        
        if not metadata:
            return []
        
        frames = []
        for frame_index in range(metadata.frame_count):
            template_path = self.get_template_path(animation_type, direction, frame_index)
            frame = AnimationFrame(
                image_url="",  # Template frames don't have images yet
                direction=direction,
                frame_index=frame_index,
                animation_type=animation_type,
                seed=-1,  # No seed for template frames
                guidance_method=AnimationGuidanceMethod.TEMPLATE_POSE,
                template_path=str(template_path) if template_path else None
            )
            frames.append(frame)
        
        return frames
    
    def create_pose_mask(self, animation_type: AnimationType, direction: Direction, 
                        frame_index: int, target_size: Tuple[int, int] = (512, 512)) -> Optional[Image.Image]:
        """Create a pose mask from template for inpainting"""
        template_path = self.get_template_path(animation_type, direction, frame_index)
        if not template_path or not template_path.exists():
            return None
        
        try:
            # Load template
            template = Image.open(template_path).convert('RGBA')
            
            # Resize to target size
            template = template.resize(target_size, Image.Resampling.LANCZOS)
            
            # Create mask (white where pose exists, black elsewhere)
            mask = Image.new('L', target_size, 0)
            template_data = template.getdata()
            mask_data = []
            
            for pixel in template_data:
                # If pixel is not transparent, make mask white
                if pixel[3] > 0:
                    mask_data.append(255)
                else:
                    mask_data.append(0)
            
            mask.putdata(mask_data)
            return mask
            
        except Exception as e:
            logger.error(f"Failed to create pose mask: {e}")
            return None
    
    def list_available_animations(self) -> List[Dict[str, Any]]:
        """List all available animations with metadata"""
        animations = []
        for key, metadata in self.metadata.items():
            animations.append({
                'animation_type': metadata.animation_type.value,
                'direction_count': metadata.direction_count,
                'frame_count': metadata.frame_count,
                'loop': metadata.loop,
                'breathing_effect': metadata.breathing_effect,
                'keyframes': metadata.keyframes
            })
        return animations
    
    def add_template_file(self, animation_type: AnimationType, direction: Direction, 
                         frame_index: int, template_path: str):
        """Add a custom template file"""
        direction_count = 4 if direction in Direction.get_4_directions() else 8
        key = f"{animation_type.value}_{direction_count}dir"
        
        if key not in self.metadata:
            self.metadata[key] = TemplateMetadata(
                animation_type=animation_type,
                direction_count=direction_count,
                frame_count=frame_index + 1,
                template_files={}
            )
        
        direction_key = direction.value
        if direction_key not in self.metadata[key].template_files:
            self.metadata[key].template_files[direction_key] = []
        
        # Ensure we have enough slots
        while len(self.metadata[key].template_files[direction_key]) <= frame_index:
            self.metadata[key].template_files[direction_key].append("")
        
        self.metadata[key].template_files[direction_key][frame_index] = template_path
        self._save_metadata()
        logger.info(f"Added template file: {template_path}")


class TemplateRenderer:
    """Renders templates for different guidance methods"""
    
    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
    
    def render_for_controlnet(self, animation_type: AnimationType, direction: Direction, 
                            frame_index: int, target_size: Tuple[int, int] = (512, 512)) -> Optional[Image.Image]:
        """Render template optimized for ControlNet"""
        template_path = self.template_manager.get_template_path(animation_type, direction, frame_index)
        if not template_path or not template_path.exists():
            return None
        
        try:
            template = Image.open(template_path).convert('RGBA')
            template = template.resize(target_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB for ControlNet
            rgb_template = Image.new('RGB', target_size, (0, 0, 0))
            rgb_template.paste(template, mask=template.split()[-1])
            
            return rgb_template
        except Exception as e:
            logger.error(f"Failed to render template for ControlNet: {e}")
            return None
    
    def render_for_inpainting(self, animation_type: AnimationType, direction: Direction, 
                            frame_index: int, target_size: Tuple[int, int] = (512, 512)) -> Tuple[Optional[Image.Image], Optional[Image.Image]]:
        """Render template and mask for inpainting"""
        template = self.render_for_controlnet(animation_type, direction, frame_index, target_size)
        mask = self.template_manager.create_pose_mask(animation_type, direction, frame_index, target_size)
        return template, mask
    
    def render_for_prompt(self, animation_type: AnimationType, direction: Direction, 
                         frame_index: int) -> str:
        """Generate prompt description for template"""
        direction_desc = {
            Direction.SOUTH: "facing forward",
            Direction.WEST: "facing left", 
            Direction.EAST: "facing right",
            Direction.NORTH: "facing backward",
            Direction.SOUTHEAST: "facing forward-right",
            Direction.SOUTHWEST: "facing forward-left",
            Direction.NORTHEAST: "facing backward-right",
            Direction.NORTHWEST: "facing backward-left"
        }
        
        pose_desc = {
            AnimationType.IDLE: "standing idle",
            AnimationType.WALK: f"walking step {frame_index + 1}",
            AnimationType.RUN: f"running step {frame_index + 1}",
            AnimationType.ATTACK: f"attack pose {frame_index + 1}",
            AnimationType.CAST_SPELL: f"casting spell {frame_index + 1}",
            AnimationType.DEATH: f"death pose {frame_index + 1}"
        }
        
        direction_text = direction_desc.get(direction, "facing forward")
        pose_text = pose_desc.get(animation_type, "standing")
        
        return f"{pose_text}, {direction_text}, pixel art sprite, animation frame"

