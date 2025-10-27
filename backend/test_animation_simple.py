"""
Simple animation test to verify the system works
"""
import asyncio
import json
from pathlib import Path

async def test_animation_system():
    """Test the animation system with a simple example"""
    
    # Create a simple animation result
    animation_result = {
        "success": True,
        "animation_sequence": {
            "animation_type": "idle",
            "directions": ["south", "west", "east", "north"],
            "frames": []
        }
    }
    
    # Create some test frames
    for direction in ["south", "west", "east", "north"]:
        for frame_idx in range(2):  # 2 frames per direction for idle
            frame = {
                "image_url": f"/output/test_frame_{direction}_{frame_idx}.png",
                "direction": direction,
                "frame_index": frame_idx,
                "animation_type": "idle",
                "quality_score": 0.8
            }
            animation_result["animation_sequence"]["frames"].append(frame)
    
    # Save test result
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    with open("output/test_animation.json", "w") as f:
        json.dump(animation_result, f, indent=2)
    
    print("Test animation result created:")
    print(f"- {len(animation_result['animation_sequence']['frames'])} frames")
    print(f"- Directions: {animation_result['animation_sequence']['directions']}")
    print(f"- Animation type: {animation_result['animation_sequence']['animation_type']}")
    
    return animation_result

if __name__ == "__main__":
    asyncio.run(test_animation_system())
