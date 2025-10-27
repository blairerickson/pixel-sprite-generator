"""
Working API server for animation testing
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
import json
import uuid
from datetime import datetime

app = FastAPI()

# Create output directory
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# Store for jobs
jobs = {}

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Frontend not found"}

@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is running"}

@app.get("/models")
async def models():
    return {"models": ["test_model_1", "test_model_2"]}

@app.post("/generate-animation")
async def generate_animation(request: dict):
    """Generate animated sprite with directional controls"""
    
    job_id = str(uuid.uuid4())
    
    # Store job info
    jobs[job_id] = {
        "status": "processing",
        "progress": 0,
        "message": "Generating animation sequence...",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    
    try:
        # Simulate animation generation
        character_description = request.get("character_description", "A cute pixel art character")
        animation_type = request.get("animation_type", "idle")
        directions = request.get("directions", ["south", "west", "east", "north"])
        
        # Create animation result
        animation_result = {
            "success": True,
            "animation_sequence": {
                "animation_type": animation_type,
                "directions": directions,
                "frames": []
            }
        }
        
        # Generate frames for each direction
        frame_count = 2 if animation_type == "idle" else 8
        
        for direction in directions:
            for frame_idx in range(frame_count):
                frame_filename = f"frame_{direction}_{frame_idx}.png"
                frame_path = output_dir / frame_filename
                
                # Create a simple colored square as placeholder
                from PIL import Image, ImageDraw
                img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Draw a simple colored rectangle based on direction
                colors = {
                    "south": (255, 100, 100),  # Red
                    "west": (100, 255, 100),   # Green  
                    "east": (100, 100, 255),   # Blue
                    "north": (255, 255, 100),  # Yellow
                }
                color = colors.get(direction, (128, 128, 128))
                
                draw.rectangle([100, 100, 400, 400], fill=color)
                draw.text((200, 200), f"{direction}\n{frame_idx}", fill=(255, 255, 255))
                
                img.save(frame_path)
                
                frame = {
                    "image_url": f"/output/{frame_filename}",
                    "direction": direction,
                    "frame_index": frame_idx,
                    "animation_type": animation_type,
                    "quality_score": 0.8
                }
                animation_result["animation_sequence"]["frames"].append(frame)
        
        # Update job status
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = "Animation generation completed"
        jobs[job_id]["result"] = animation_result
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": animation_result
        }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Animation generation failed: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.get("/jobs")
async def list_jobs():
    """List all jobs"""
    return {"jobs": list(jobs.keys())}

# Mount static files
app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# Mount frontend assets
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

if __name__ == "__main__":
    print("Starting working API server...")
    uvicorn.run(app, host="127.0.0.1", port=8010, log_level="info")
