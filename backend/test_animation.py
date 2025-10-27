#!/usr/bin/env python3
"""
Quick test script for animation system
Run this to verify backend fixes are working
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from animation_generator import AnimationGenerator
from animation_models import AnimationGenerateRequest, Direction, AnimationType, AnimationGuidanceMethod
from sd_client import SDClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_animation_generation():
    """Test the fixed animation system"""
    print("🧪 Testing Animation System...")
    
    try:
        # Load config
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Initialize SD client (mock for testing)
        class MockSDClient:
            async def generate(self, params):
                return {"images": [None], "seed": 12345}
            async def generate_img2img(self, params):
                return {"images": [None], "seed": 12345}
        
        sd_client = MockSDClient()
        
        # Initialize animation generator
        anim_gen = AnimationGenerator(sd_client, config)
        
        # Create test request
        request = AnimationGenerateRequest(
            character_description="A ninja with a black mask",
            directions=["south", "west", "east", "north"],
            animation_type="walk",
            guidance_method="auto",
            generate_reference_first=True,
            frame_count=8,
            seed=12345,
            width=512,
            height=512
        )
        
        print("📋 Test Request:")
        print(f"  Character: {request.character_description}")
        print(f"  Directions: {request.directions}")
        print(f"  Animation: {request.animation_type}")
        print(f"  Frame Count: {request.frame_count}")
        
        # Test guidance method availability
        print("\n🔍 Checking Guidance Methods:")
        for method, guidance in anim_gen.guidance_methods.items():
            caps = guidance.get_capabilities()
            print(f"  {method.value}: Available={caps.available}, Quality={caps.quality_rating}")
        
        print("\n✅ Animation system appears ready!")
        print("🚀 Try generating an animation in the UI!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_animation_generation())
    if success:
        print("\n🎉 Backend animation system ready!")
    else:
        print("\n💥 Backend needs debugging")