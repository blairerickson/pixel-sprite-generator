"""
Simple test for animation generation
"""
import asyncio
from animation_generator import AnimationGenerator
from sd_client import SDClient
from animation_models import AnimationGenerateRequest, AnimationType, Direction, AnimationGuidanceMethod
import yaml

async def test_simple_animation():
    """Test basic animation generation"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize SD client
    sd_client = SDClient(config)
    
    # Check if SD is available
    if not await sd_client.check_health():
        print("SD client not available - skipping test")
        return
    
    # Initialize animation generator
    animation_generator = AnimationGenerator(sd_client, config)
    
    # Create test request
    request = AnimationGenerateRequest(
        character_description="A cute pixel art frog with big blue eyes",
        animation_type=AnimationType.IDLE.value,
        directions=[Direction.SOUTH.value, Direction.WEST.value],
        guidance_method=AnimationGuidanceMethod.PROMPT_ONLY.value,
        frame_count=2,
        generate_reference_first=False,
        width=512,
        height=512,
        steps=10,  # Low steps for testing
        seed=42
    )
    
    print("Testing animation generation...")
    print(f"Character: {request.character_description}")
    print(f"Animation: {request.animation_type}")
    print(f"Directions: {request.directions}")
    print(f"Frames per direction: {request.frame_count}")
    
    try:
        # Generate animation
        result = await animation_generator.generate_animation_sequence(request)
        
        if result.success:
            print("Animation generation successful!")
            print(f"Generated {len(result.animation_sequence.frames)} frames")
            print(f"Generation time: {result.generation_time:.2f}s")
            
            # Print frame details
            for i, frame in enumerate(result.animation_sequence.frames):
                print(f"  Frame {i+1}: {frame.direction.value} - {frame.image_url}")
        else:
            print(f"Animation generation failed: {result.error_message}")
            
    except Exception as e:
        print(f"Error during animation generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_animation())
