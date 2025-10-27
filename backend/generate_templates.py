"""
Script to generate base animation templates
"""
import sys
import os
from pathlib import Path

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from animation_templates import TemplateManager
from animation_models import AnimationType, Direction

def generate_base_templates():
    """Generate base templates for all animations"""
    template_manager = TemplateManager("templates")
    
    print("Generating base animation templates...")
    
    # Generate templates for 4-direction animations
    animations = [
        AnimationType.IDLE,
        AnimationType.WALK, 
        AnimationType.RUN,
        AnimationType.ATTACK,
        AnimationType.CAST_SPELL,
        AnimationType.DEATH
    ]
    
    directions = Direction.get_4_directions()
    
    for animation_type in animations:
        print(f"\nGenerating {animation_type.value} templates...")
        
        # Get frame count for this animation
        metadata = template_manager.get_template_metadata(animation_type, 4)
        frame_count = metadata.frame_count if metadata else 2
        
        for direction in directions:
            print(f"  {direction.value}: {frame_count} frames")
            for frame_index in range(frame_count):
                template_path = template_manager.get_template_path(animation_type, direction, frame_index)
                if template_path:
                    print(f"    Generated: {template_path}")
    
    print("\nTemplate generation complete!")
    print(f"Templates saved to: {template_manager.templates_dir}")
    
    # List all generated templates
    print("\nGenerated templates:")
    for key, metadata in template_manager.metadata.items():
        print(f"  {key}: {metadata.frame_count} frames, loop={metadata.loop}")

if __name__ == "__main__":
    generate_base_templates()

