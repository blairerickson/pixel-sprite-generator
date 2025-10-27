"""
Diagnostic CLI for animation system
Tests each guidance method and saves artifacts
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from animation_models import (
    AnimationType, Direction, AnimationGuidanceMethod,
    AnimationGenerateRequest
)
from animation_generator import AnimationGenerator
from sd_client import SDClient
from sprite_normalizer import SpriteNormalizer
from sprite_animator import SpriteAnimator
import yaml
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Load configuration
config_path = Path(__file__).parent.parent / 'config.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

async def test_guidance_method(
    animation_generator: AnimationGenerator,
    method: AnimationGuidanceMethod,
    character_description: str = "pixel art knight in armor"
):
    """Test a single guidance method"""
    print(f"\n{'=' * 60}")
    print(f"Testing: {method.value}")
    print('=' * 60)
    
    try:
        success, message = await animation_generator.test_guidance_method(
            method, character_description
        )
        
        if success:
            print(f"✅ SUCCESS: {message}")
        else:
            print(f"❌ FAILED: {message}")
            
        return success
        
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        logger.exception(f"Error testing {method.value}")
        return False

async def test_storyboard_generation(
    animation_generator: AnimationGenerator,
    output_dir: Path
):
    """Test 5-frame storyboard generation"""
    print(f"\n{'=' * 60}")
    print("Testing: Storyboard 5-Frame Generation")
    print('=' * 60)
    
    try:
        request = AnimationGenerateRequest(
            character_description="pixel art wizard casting fireball",
            directions=["south"],
            animation_type="storyboard",
            guidance_method="auto",
            generate_reference_first=True,
            frame_count=5,
            width=512,
            height=512,
            seed=42
        )
        
        print("Generating storyboard...")
        result = await animation_generator.generate_animation_sequence(request, job_id="diagnostic_storyboard")
        
        if result.success:
            sequence = result.animation_sequence
            print(f"✅ SUCCESS")
            print(f"   Frames: {sequence.get_frame_count()}")
            print(f"   Directions: {sequence.get_direction_count()}")
            print(f"   Guidance: {result.guidance_method_used.value}")
            print(f"   Quality: {sequence.overall_quality_score:.2f}")
            print(f"   Consistency: {sequence.metadata.get('consistency_score', 'N/A')}")
            print(f"   Generation time: {result.generation_time:.2f}s")
            
            # Save test report
            report_path = output_dir / "diagnostic_storyboard_report.txt"
            with open(report_path, 'w') as f:
                f.write(f"Storyboard Diagnostic Report\n")
                f.write(f"{'=' * 40}\n")
                f.write(f"Timestamp: {Path(__file__).stat().st_mtime}\n")
                f.write(f"Success: {result.success}\n")
                f.write(f"Frames: {sequence.get_frame_count()}\n")
                f.write(f"Guidance: {result.guidance_method_used.value}\n")
                f.write(f"Quality: {sequence.overall_quality_score:.2f}\n")
                f.write(f"Consistency: {sequence.metadata.get('consistency_score', 'N/A')}\n")
            
            print(f"   Report saved: {report_path}")
            return True
        else:
            print(f"❌ FAILED: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {str(e)}")
        logger.exception("Storyboard test failed")
        return False

async def run_diagnostics():
    """Run all diagnostic tests"""
    print("🔍 Pearl Pixel Salon - Animation Diagnostics")
    print("=" * 60)
    
    # Initialize clients
    sd_client = SDClient(config)
    sprite_normalizer = SpriteNormalizer(config)
    sprite_animator = SpriteAnimator(config)
    animation_generator = AnimationGenerator(
        sd_client,
        config,
        sprite_normalizer=sprite_normalizer,
        sprite_animator=sprite_animator,
        jobs_store={}
    )
    
    # Create output directory
    output_dir = Path(config['paths']['output_dir']) / 'diagnostics'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check system status
    print("\n1. System Status")
    print("-" * 60)
    try:
        status = await animation_generator.get_system_status()
        print(f"   SD Backend: {'✅ Healthy' if status['sd_client_healthy'] else '❌ Offline'}")
        print(f"   Templates: {'✅ Available' if status['templates_available'] else '❌ Missing'}")
        print(f"   ControlNet: {'✅ Available' if status['controlnet_available'] else '❌ Not installed'}")
    except Exception as e:
        print(f"   ❌ Status check failed: {e}")
    
    # Test each guidance method
    print("\n2. Guidance Methods")
    print("-" * 60)
    
    guidance_results = {}
    for method in [
        AnimationGuidanceMethod.PROMPT_ONLY,
        AnimationGuidanceMethod.TEMPLATE_POSE,
        AnimationGuidanceMethod.IMG2IMG_INPAINT,
        AnimationGuidanceMethod.CONTROLNET
    ]:
        guidance_results[method] = await test_guidance_method(animation_generator, method)
    
    # Test storyboard generation
    print("\n3. Storyboard Generation")
    print("-" * 60)
    storyboard_success = await test_storyboard_generation(animation_generator, output_dir)
    
    # Summary
    print(f"\n{'=' * 60}")
    print("DIAGNOSTIC SUMMARY")
    print('=' * 60)
    
    total_tests = len(guidance_results) + 1
    passed_tests = sum(1 for v in guidance_results.values() if v) + (1 if storyboard_success else 0)
    
    print(f"\nGuidance Methods:")
    for method, success in guidance_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {method.value}")
    
    print(f"\nStoryboard:")
    print(f"   {'✅ PASS' if storyboard_success else '❌ FAIL'} - 5-frame generation")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    print(f"Artifacts saved to: {output_dir}")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = asyncio.run(run_diagnostics())
    sys.exit(0 if success else 1)

