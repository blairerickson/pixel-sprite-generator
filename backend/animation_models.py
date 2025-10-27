"""
Animation system data models and enums
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
import json
from datetime import datetime


class Direction(Enum):
    """Character facing directions"""
    SOUTH = "south"
    WEST = "west" 
    EAST = "east"
    NORTH = "north"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    
    @classmethod
    def get_4_directions(cls) -> List['Direction']:
        """Get standard 4-direction set"""
        return [cls.SOUTH, cls.WEST, cls.EAST, cls.NORTH]
    
    @classmethod
    def get_8_directions(cls) -> List['Direction']:
        """Get full 8-direction set"""
        return [
            cls.SOUTH, cls.SOUTHWEST, cls.WEST, cls.NORTHWEST,
            cls.NORTH, cls.NORTHEAST, cls.EAST, cls.SOUTHEAST
        ]


class AnimationType(Enum):
    """Types of character animations"""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    DEATH = "death"
    JUMP = "jump"
    CROUCH = "crouch"
    HURT = "hurt"
    STORYBOARD = "storyboard"
    
    @classmethod
    def get_default_frame_counts(cls) -> Dict['AnimationType', int]:
        """Get default frame counts for each animation type"""
        return {
            cls.IDLE: 2,
            cls.WALK: 8,
            cls.RUN: 8,
            cls.ATTACK: 6,
            cls.CAST_SPELL: 8,
            cls.DEATH: 6,
            cls.JUMP: 4,
            cls.CROUCH: 3,
            cls.HURT: 4,
            cls.STORYBOARD: 5,
        }


class AnimationGuidanceMethod(Enum):
    """Methods for guiding animation generation"""
    CONTROLNET = "controlnet"
    IMG2IMG_INPAINT = "img2img_inpaint"
    TEMPLATE_POSE = "template_pose"
    PROMPT_ONLY = "prompt_only"
    PIXEL_WARP = "pixel_warp"
    AUTO = "auto"  # Automatically select best available method
    
    @classmethod
    def get_priority_order(cls) -> List['AnimationGuidanceMethod']:
        """Get guidance methods in order of preference (best to worst)"""
        return [
            cls.CONTROLNET,
            cls.IMG2IMG_INPAINT,
            cls.TEMPLATE_POSE,
            cls.PIXEL_WARP,
            cls.PROMPT_ONLY
        ]


@dataclass
class AnimationFrame:
    """Metadata for a single animation frame"""
    image_url: str
    direction: Direction
    frame_index: int
    animation_type: AnimationType
    seed: int
    guidance_method: AnimationGuidanceMethod
    quality_score: float = 0.0
    generation_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    pose_data: Optional[Dict[str, Any]] = None
    template_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'image_url': self.image_url,
            'direction': self.direction.value,
            'frame_index': self.frame_index,
            'animation_type': self.animation_type.value,
            'seed': self.seed,
            'guidance_method': self.guidance_method.value,
            'quality_score': self.quality_score,
            'generation_time': self.generation_time,
            'metadata': self.metadata,
            'pose_data': self.pose_data,
            'template_path': self.template_path
        }


@dataclass
class AnimationSequence:
    """Complete animation sequence with all frames"""
    animation_type: AnimationType
    directions: List[Direction]
    frames: List[AnimationFrame] = field(default_factory=list)
    reference_sheet: Optional[Dict[Direction, str]] = None  # Paths to reference images
    total_generation_time: Optional[float] = None
    overall_quality_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_frame(self, frame: AnimationFrame):
        """Add a frame to the sequence"""
        self.frames.append(frame)
    
    def get_frames_for_direction(self, direction: Direction) -> List[AnimationFrame]:
        """Get all frames for a specific direction"""
        return [f for f in self.frames if f.direction == direction]
    
    def get_frame_count(self) -> int:
        """Get total number of frames"""
        return len(self.frames)
    
    def get_direction_count(self) -> int:
        """Get number of directions"""
        return len(self.directions)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        reference_sheet = None
        if self.reference_sheet:
            reference_sheet = {
                (direction.value if isinstance(direction, Direction) else str(direction)): str(path)
                for direction, path in self.reference_sheet.items()
            }

        return {
            'animation_type': self.animation_type.value,
            'directions': [d.value for d in self.directions],
            'frames': [f.to_dict() for f in self.frames],
            'reference_sheet': reference_sheet,
            'total_generation_time': self.total_generation_time,
            'overall_quality_score': self.overall_quality_score,
            'metadata': self.metadata
        }


@dataclass
class AnimationGenerateRequest:
    """Request for generating an animation sequence"""
    character_description: str
    directions: List[str]  # Will be converted to Direction enums
    animation_type: str
    guidance_method: str = "auto"
    frame_count: Optional[int] = None  # Auto if None
    generate_reference_first: bool = True
    style_lora: Optional[str] = None
    lora_weight: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    seed: int = -1
    batch_size: int = 1
    source_job_id: Optional[str] = None
    use_cleaned_sprite: bool = True
    
    def to_direction_enums(self) -> List[Direction]:
        """Convert direction strings to Direction enums"""
        direction_map = {d.value: d for d in Direction}
        return [direction_map[d.lower()] for d in self.directions if d.lower() in direction_map]
    
    def to_animation_type_enum(self) -> AnimationType:
        """Convert animation type string to enum"""
        type_map = {t.value: t for t in AnimationType}
        return type_map.get(self.animation_type.lower(), AnimationType.WALK)
    
    def to_guidance_method_enum(self) -> AnimationGuidanceMethod:
        """Convert guidance method string to enum"""
        method_map = {m.value: m for m in AnimationGuidanceMethod}
        return method_map.get(self.guidance_method.lower(), AnimationGuidanceMethod.AUTO)


@dataclass
class ReferenceSheetRequest:
    """Request for generating a character reference sheet"""
    character_description: str
    directions: List[str] = field(default_factory=lambda: ["south", "west", "east", "north"])
    style_lora: Optional[str] = None
    lora_weight: Optional[float] = None
    width: int = 512
    height: int = 512
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    seed: int = -1
    
    def to_direction_enums(self) -> List[Direction]:
        """Convert direction strings to Direction enums"""
        direction_map = {d.value: d for d in Direction}
        return [direction_map[d.lower()] for d in self.directions if d.lower() in direction_map]


@dataclass
class TemplateMetadata:
    """Metadata for animation templates"""
    animation_type: AnimationType
    direction_count: int  # 4 or 8
    frame_count: int
    keyframes: List[int] = field(default_factory=list)
    loop: bool = True
    breathing_effect: bool = False
    template_files: Dict[str, List[str]] = field(default_factory=dict)  # direction -> [file_paths]
    motion_profile: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'animation_type': self.animation_type.value,
            'direction_count': self.direction_count,
            'frame_count': self.frame_count,
            'keyframes': self.keyframes,
            'loop': self.loop,
            'breathing_effect': self.breathing_effect,
            'template_files': self.template_files,
            'motion_profile': self.motion_profile,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TemplateMetadata':
        """Create from dictionary"""
        return cls(
            animation_type=AnimationType(data['animation_type']),
            direction_count=data['direction_count'],
            frame_count=data['frame_count'],
            keyframes=data.get('keyframes', []),
            loop=data.get('loop', True),
            breathing_effect=data.get('breathing_effect', False),
            template_files=data.get('template_files', {}),
            motion_profile=data.get('motion_profile'),
            notes=data.get('notes', []),
        )


@dataclass
class GuidanceCapabilities:
    """Capabilities of a guidance method"""
    method: AnimationGuidanceMethod
    available: bool
    requires_models: List[str] = field(default_factory=list)
    quality_rating: float = 0.0  # 0-1 scale
    speed_rating: float = 0.0  # 0-1 scale
    consistency_rating: float = 0.0  # 0-1 scale
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'method': self.method.value,
            'available': self.available,
            'requires_models': self.requires_models,
            'quality_rating': self.quality_rating,
            'speed_rating': self.speed_rating,
            'consistency_rating': self.consistency_rating,
            'notes': self.notes
        }


@dataclass
class AnimationGenerationResult:
    """Result of animation generation"""
    success: bool
    animation_sequence: Optional[AnimationSequence] = None
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    guidance_method_used: Optional[AnimationGuidanceMethod] = None
    fallback_used: bool = False
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'animation_sequence': self.animation_sequence.to_dict() if self.animation_sequence else None,
            'error_message': self.error_message,
            'generation_time': self.generation_time,
            'guidance_method_used': self.guidance_method_used.value if self.guidance_method_used else None,
            'fallback_used': self.fallback_used,
            'quality_metrics': self.quality_metrics
        }
