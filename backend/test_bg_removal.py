"""
Test background removal on a specific image
"""
import sys
from pathlib import Path
from PIL import Image
import asyncio
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sprite_processor import SpriteProcessor

async def test_removal(image_path):
    """Test background removal on an image"""
    
    print("=" * 60)
    print("Background Removal Test")
    print("=" * 60)
    print()
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Load image
    print(f"Loading: {image_path}")
    image = Image.open(image_path)
    print(f"Size: {image.size}")
    print(f"Mode: {image.mode}")
    print()
    
    # Process
    processor = SpriteProcessor(config)
    result, qc = await processor.remove_background(image)
    
    # Save result
    output_path = Path(image_path).parent / f"{Path(image_path).stem}_TRANSPARENT.png"
    result.save(output_path)
    
    print()
    print(f"Saved to: {output_path}")
    print("QC Summary:")
    for key, value in qc.items():
        print(f"  - {key}: {value}")
    print()
    print("Open both files to compare:")
    print(f"  Original: {image_path}")
    print(f"  Result:   {output_path}")
    print()
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_bg_removal.py <image_path>")
        print()
        print("Example:")
        print('  python test_bg_removal.py "../output/abc123.../original_0.png"')
        sys.exit(1)
    
    asyncio.run(test_removal(sys.argv[1]))

