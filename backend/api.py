"""
FastAPI backend for local pixel sprite generation
"""
import os
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import yaml

from sd_client import SDClient, GenerationParams
from sprite_processor import SpriteProcessor
from sprite_normalizer import SpriteNormalizer
from sprite_animator import SpriteAnimator
from animation_generator import AnimationGenerator
from animation_models import (
    AnimationGenerateRequest, ReferenceSheetRequest, 
    AnimationType, Direction, AnimationGuidanceMethod
)
from job_storage import JobStorage
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Allow overriding the Stable Diffusion API URL from the environment
sd_api_override = os.getenv('SD_API_URL')
if sd_api_override:
    config.setdefault('sd', {})['api_url'] = sd_api_override
    print(f"[config] SD API URL overridden by environment variable: {sd_api_override}")

# Initialize FastAPI
app = FastAPI(
    title="Pixel Sprite Generator API",
    description="Local Stable Diffusion API for pixel art sprite generation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config['api']['cors_origins'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for generated images (mount after routes to avoid conflicts)
from fastapi.staticfiles import StaticFiles
output_dir = Path(config['paths']['output_dir'])
output_dir.mkdir(parents=True, exist_ok=True)
assets_dir = Path(__file__).parent.parent / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# Initialize clients
sd_client = SDClient(config)
sprite_processor = SpriteProcessor(config)
sprite_normalizer = SpriteNormalizer(config)
sprite_animator = SpriteAnimator(config)

# Initialize persistent storage
job_storage = JobStorage(Path(config['paths']['output_dir']) / 'job_history.json')

# Job storage (in production, use Redis or database)
jobs: Dict[str, Dict[str, Any]] = {}

animation_generator = AnimationGenerator(
    sd_client,
    config,
    sprite_normalizer=sprite_normalizer,
    sprite_animator=sprite_animator,
    jobs_store=jobs,
)

# Load existing jobs from history on startup
historical_jobs = job_storage.load_history()


def _prepare_job_from_history(job_data: Dict[str, Any]) -> bool:
    """Backfill metadata for historical jobs when possible."""
    updated = False

    job_id = job_data.get('job_id') or job_data.get('id')
    if job_id and job_data.get('job_id') != job_id:
        job_data['job_id'] = job_id
        updated = True

    result = job_data.get('result') or {}

    # Backfill prompt/seed if stored inside result/request payloads
    if not job_data.get('prompt') and 'request' in job_data:
        request_payload = job_data['request']
        prompt = request_payload.get('prompt') or request_payload.get('character_description')
        if prompt:
            job_data['prompt'] = prompt
            updated = True
        seed_val = request_payload.get('seed')
        if seed_val is not None:
            job_data['seed'] = seed_val
            updated = True

    if result and not job_data.get('seed'):
        seed_val = result.get('seed') or result.get('parameters', {}).get('seed')
        if seed_val is not None:
            job_data['seed'] = seed_val
            updated = True

    # Ensure assets index is present for downstream reuse
    if result and 'assets' not in job_data:
        assets = {
            'raw_images': [],
            'processed_images': [],
            'sprites': []
        }
        images = result.get('images') or []
        for idx, image_entry in enumerate(images):
            raw_path = image_entry.get('raw')
            if raw_path:
                assets['raw_images'].append({
                    'index': idx,
                    'path': raw_path,
                    'url': image_entry.get('raw_url')
                })
            processed_path = image_entry.get('processed')
            if processed_path:
                assets['processed_images'].append({
                    'index': idx,
                    'path': processed_path,
                    'url': image_entry.get('processed_url')
                })
            for sprite_idx, sprite_entry in enumerate(image_entry.get('sprites') or []):
                entry = {
                    'image_index': idx,
                    'sprite_index': sprite_idx,
                    'path': sprite_entry.get('path'),
                    'url': sprite_entry.get('url')
                }
                assets['sprites'].append(entry)
        job_data['assets'] = assets
        updated = True

    if 'primary_sprite' not in job_data:
        primary = sprite_normalizer.resolve_primary_sprite(job_data)
        if primary:
            job_data['primary_sprite'] = primary
            updated = True

    return updated


for job_data in historical_jobs:
    was_updated = _prepare_job_from_history(job_data)
    jobs[job_data['job_id']] = job_data
    if was_updated:
        job_storage.save_job(job_data['job_id'], job_data)

# Pydantic Models
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Main prompt for generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    preset: Optional[str] = Field("character_sprite", description="Preset name")
    lora: Optional[str] = Field(None, description="LoRA name to use")
    lora_weight: Optional[float] = Field(None, description="LoRA weight")
    width: Optional[int] = Field(None, description="Image width")
    height: Optional[int] = Field(None, description="Image height")
    steps: Optional[int] = Field(None, description="Sampling steps")
    cfg_scale: Optional[float] = Field(None, description="CFG scale")
    seed: Optional[int] = Field(-1, description="Seed (-1 for random)")
    batch_size: int = Field(1, description="Number of images", ge=1, le=4)
    save_raw: bool = Field(True, description="Save raw (uncleaned) image")
    process_sprites: bool = Field(False, description="Extract and process sprites")
    remove_background: bool = Field(False, description="Remove background")
    
    # Advanced background removal settings
    bg_removal_method: Optional[str] = Field(None, description="Background removal method")
    rembg_aggressiveness: Optional[int] = Field(None, description="Rembg aggressiveness threshold", ge=50, le=95)
    rembg_model: Optional[str] = Field(None, description="Rembg model to use")
    outline_preservation: Optional[int] = Field(None, description="Outline preservation strength", ge=0, le=5)
    force_chromakey: Optional[bool] = Field(None, description="Force chromakey for pixel art")

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: float
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    
    class Config:
        extra = "ignore"  # Ignore extra fields from job storage

# API Routes

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {
        "name": "Pixel Sprite Generator API",
        "version": "1.0.0",
        "status": "running",
        "backend": config['sd']['backend']
    }

@app.get("/health")
async def health_check():
    """Check if SD backend is available"""
    try:
        is_ready = await sd_client.check_health()
        return {
            "status": "healthy" if is_ready else "unhealthy",
            "backend": config['sd']['backend'],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/models")
async def list_models():
    """List available models and LoRAs"""
    # Get available models from SD backend
    available_models = await sd_client.get_available_models()
    
    return {
        "base_model": config['sd']['models']['base_model'],
        "alternative_models": config['sd']['models'].get('alternative_models', []),
        "available_sd_models": available_models,
        "loras": [
            {
                "name": lora['name'],
                "triggers": lora['triggers'],
                "default_weight": lora['default_weight']
            }
            for lora in config['sd']['loras']
        ]
    }

@app.get("/presets")
async def list_presets():
    """List available generation presets"""
    return {
        "presets": {
            name: {
                "width": preset['width'],
                "height": preset['height'],
                "steps": preset['steps'],
                "cfg_scale": preset['cfg_scale']
            }
            for name, preset in config['generation']['presets'].items()
        }
    }

@app.post("/generate", response_model=JobResponse)
async def generate_sprite(request: GenerateRequest, background_tasks: BackgroundTasks):
    """Generate pixel sprite(s) - returns immediately with job ID"""
    
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Job queued",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "prompt": request.prompt,
        "seed": request.seed,
        "request": request.model_dump(),
        "assets": {
            "raw_images": [],
            "processed_images": [],
            "sprites": []
        }
    }
    
    # Add generation task to background
    background_tasks.add_task(process_generation, job_id, request)
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        message="Generation started"
    )

async def process_generation(job_id: str, request: GenerateRequest):
    """Background task to handle generation"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Generating images..."
        jobs[job_id]["progress"] = 0.1
        
        # Build generation parameters
        params = GenerationParams(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            preset=request.preset,
            lora=request.lora,
            lora_weight=request.lora_weight,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed,
            batch_size=request.batch_size,
            sampler=None
        )
        
        # Apply advanced settings from frontend if provided
        if hasattr(request, 'bg_removal_method') and request.bg_removal_method:
            config['sprite_processing']['background_removal']['method'] = request.bg_removal_method
        
        if hasattr(request, 'rembg_aggressiveness') and request.rembg_aggressiveness:
            config['sprite_processing']['background_removal']['rembg']['aggressiveness_threshold'] = request.rembg_aggressiveness
        
        if hasattr(request, 'rembg_model') and request.rembg_model:
            config['sprite_processing']['background_removal']['rembg']['model'] = request.rembg_model
        
        if hasattr(request, 'outline_preservation') and request.outline_preservation is not None:
            config['sprite_processing']['background_removal']['chromakey']['outline_preservation_strength'] = request.outline_preservation
        
        if hasattr(request, 'force_chromakey') and request.force_chromakey:
            config['sprite_processing']['background_removal']['rembg']['force_chromakey_for_pixel_art'] = request.force_chromakey
        
        # Generate images
        jobs[job_id]["progress"] = 0.3
        
        # Try inpainting if background removal is requested for clean magenta borders
        # Falls back to regular generation + flood-fill if inpainting fails
        inpaint_enabled = config['sprite_processing']['background_removal'].get('enable_inpaint', True)
        
        logger.info(f"[Generation] remove_background={request.remove_background}, inpaint_enabled={inpaint_enabled}")
        
        if request.remove_background and inpaint_enabled:
            try:
                jobs[job_id]["message"] = "Generating with inpaint (magenta background)..."
                
                # Create magenta canvas
                width = params.width or 512
                height = params.height or 512
                magenta_canvas = Image.new('RGB', (width, height), (255, 0, 255))
                
                # Create inpaint mask - white center (paint character), black edges (preserve magenta)
                mask = Image.new('L', (width, height), 0)  # Start with black
                draw = ImageDraw.Draw(mask)
                border = config['sprite_processing']['background_removal'].get('inpaint_border', 80)
                draw.rectangle(
                    [(border, border), (width - border, height - border)],
                    fill=255  # White = inpaint this area
                )
                
                results = await sd_client.generate_with_inpaint(params, magenta_canvas, mask)
                logger.info("[Generation] Inpainting successful - pure magenta borders guaranteed")
                
            except Exception as e:
                # Inpainting failed - fall back to regular generation
                error_msg = str(e)
                logger.warning(f"[Generation] Inpainting failed ({error_msg[:100]}), falling back to regular generation + flood-fill")
                jobs[job_id]["message"] = "Inpaint unavailable, using flood-fill..."
                results = await sd_client.generate(params)
        else:
            results = await sd_client.generate(params)
        
        if not results or 'images' not in results:
            raise Exception("No images generated")
        
        jobs[job_id]["progress"] = 0.6
        jobs[job_id]["message"] = "Processing sprites..."
        
        output_dir = Path(config['paths']['output_dir']) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        processed_results = []
        
        qa_records = []

        assets = jobs[job_id].setdefault("assets", {
            "raw_images": [],
            "processed_images": [],
            "sprites": []
        })

        for idx, image_data in enumerate(results['images']):
            # Save raw image first
            raw_path = output_dir / f"raw_{idx}.png"
            image_data.save(raw_path)
            
            result_item = {
                "raw": str(raw_path.absolute()),
                "raw_url": f"/download/{job_id}/{raw_path.name}",
                "original": str(raw_path.absolute()),  # Keep for compatibility
                "processed": None,
                "processed_url": None,
                "sprites": []
            }
            
            assets["raw_images"].append({
                "index": idx,
                "path": str(raw_path.absolute()),
                "filename": raw_path.name,
                "url": f"/download/{job_id}/{raw_path.name}"
            })
            
        # Process if requested
        if request.remove_background or request.process_sprites:
            # Remove background
            if request.remove_background:
                processed_image, qc_info = await sprite_processor.remove_background(
                    image_data,
                    output_dir=output_dir,
                    prefix=f"{job_id}_img{idx}"
                )
            else:
                processed_image = image_data
                qc_info = sprite_processor._default_qc_info(
                    passed=True,
                    method_used='none',
                    notes=['Background removal skipped']
                )
            
            processed_path = output_dir / f"processed_{idx}.png"
            processed_image.save(processed_path)
            result_item["processed"] = str(processed_path.absolute())
            result_item["processed_url"] = f"/download/{job_id}/{processed_path.name}"
            result_item["background_qc"] = qc_info
            qa_records.append({
                "type": "background",
                "label": f"Image {idx + 1}",
                "qc": qc_info
            })

            assets["processed_images"].append({
                "index": idx,
                "path": str(processed_path.absolute()),
                "filename": processed_path.name,
                "url": f"/download/{job_id}/{processed_path.name}",
                "background_qc": qc_info
            })
            
            # Extract sprites
            if request.process_sprites:
                sprites, extraction_qc = await sprite_processor.extract_sprites(processed_image)
                
                for sprite_idx, sprite in enumerate(sprites):
                    sprite_path = output_dir / f"sprite_{idx}_{sprite_idx}.png"
                    sprite['image'].save(sprite_path)

                    sprite_entry = {
                        "path": str(sprite_path.absolute()),
                        "url": f"/download/{job_id}/{sprite_path.name}",
                        "bounds": sprite['bounds'],
                        "size": sprite['size'],
                        "qc": sprite.get('qc', {}),
                    }

                    # Save raw crop from original image for reference variants
                    bounds = sprite['bounds']
                    x1 = max(0, int(bounds[0]))
                    y1 = max(0, int(bounds[1]))
                    x2 = min(image_data.width, int(bounds[2]))
                    y2 = min(image_data.height, int(bounds[3]))
                    raw_crop = image_data.crop((x1, y1, x2, y2))
                    raw_filename = f"sprite_{idx}_{sprite_idx}_raw.png"
                    raw_path = output_dir / raw_filename
                    raw_crop.save(raw_path)

                    sprite_variants = [
                        {
                            "key": "raw",
                            "label": "Raw Crop",
                            "url": f"/download/{job_id}/{raw_filename}",
                            "size": [raw_crop.width, raw_crop.height]
                        },
                        {
                            "key": "processed",
                            "label": "Processed",
                            "url": f"/download/{job_id}/{sprite_path.name}",
                            "size": [sprite['size'][0], sprite['size'][1]]
                        }
                    ]

                    sprite_pixel_image, sprite_pixel_preview, sprite_pixel_meta = sprite_processor.finalize_pixel_art(sprite['image'])
                    sprite_pixel_filename = f"sprite_{idx}_{sprite_idx}_pixel.png"
                    sprite_pixel_path = output_dir / sprite_pixel_filename
                    sprite_pixel_image.save(sprite_pixel_path)

                    pixel_variant = {
                        "key": "pixel",
                        "label": f"Pixel {sprite_pixel_meta.get('scaled_width')}x{sprite_pixel_meta.get('scaled_height')}",
                        "url": f"/download/{job_id}/{sprite_pixel_filename}",
                        "meta": sprite_pixel_meta,
                        "size": [
                            sprite_pixel_meta.get('scaled_width'),
                            sprite_pixel_meta.get('scaled_height')
                        ]
                    }

                    if sprite_pixel_preview is not None:
                        sprite_pixel_preview_filename = f"sprite_{idx}_{sprite_idx}_pixel_preview.png"
                        sprite_pixel_preview_path = output_dir / sprite_pixel_preview_filename
                        sprite_pixel_preview.save(sprite_pixel_preview_path)
                        pixel_variant["preview_url"] = f"/download/{job_id}/{sprite_pixel_preview_filename}"

                    sprite_variants.append(pixel_variant)
                    sprite_entry["variants"] = sprite_variants
                    sprite_entry["raw"] = f"/download/{job_id}/{raw_filename}"

                    result_item["sprites"].append(sprite_entry)
                    assets["sprites"].append({
                        "image_index": idx,
                        "sprite_index": sprite_idx,
                        "path": str(sprite_path.absolute()),
                        "filename": sprite_path.name,
                        "url": f"/download/{job_id}/{sprite_path.name}",
                        "bounds": sprite['bounds'],
                        "size": sprite['size']
                    })
                result_item["sprite_qc"] = extraction_qc
                qa_records.append({
                    "type": "extraction",
                    "label": f"Image {idx + 1} extraction",
                    "qc": extraction_qc
                })
        else:
            processed_image = image_data
            result_item["processed"] = result_item["raw"]
            result_item["processed_url"] = result_item["raw_url"]

        # Pixel art export
        pixel_image, pixel_preview, pixel_meta = sprite_processor.finalize_pixel_art(processed_image)
        pixel_filename = f"pixel_{idx}.png"
        pixel_path = output_dir / pixel_filename
        pixel_image.save(pixel_path)

        pixel_entry = {
            "path": str(pixel_path.absolute()),
            "url": f"/download/{job_id}/{pixel_filename}",
            **pixel_meta
        }

        if pixel_preview is not None:
            preview_filename = f"pixel_{idx}_preview.png"
            preview_path = output_dir / preview_filename
            pixel_preview.save(preview_path)
            pixel_entry["preview"] = {
                "path": str(preview_path.absolute()),
                "url": f"/download/{job_id}/{preview_filename}"
            }

        result_item["pixel_art"] = pixel_entry

        image_variants = [
            {
                "key": "original",
                "label": "Original",
                "url": result_item["raw_url"],
                "size": [image_data.width, image_data.height]
            }
        ]
 
        if result_item.get("processed_url") and result_item["processed_url"] != result_item["raw_url"]:
            image_variants.append({
                "key": "processed",
                "label": "Processed",
                "url": result_item["processed_url"],
                "size": [processed_image.width, processed_image.height]
            })

        pixel_variant = {
            "key": "pixel",
            "label": f"Pixel {pixel_meta.get('scaled_width')}x{pixel_meta.get('scaled_height')}",
            "url": pixel_entry["url"],
            "size": [
                pixel_meta.get('scaled_width'),
                pixel_meta.get('scaled_height')
            ],
            "meta": pixel_meta
        }

        if pixel_entry.get("preview"):
            pixel_variant["preview_url"] = pixel_entry["preview"].get("url")

        image_variants.append(pixel_variant)
        result_item["variants"] = image_variants

        processed_results.append(result_item)
        
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Generation completed"
        jobs[job_id]["result"] = {
            "images": processed_results,
            "seed": results.get('seed', -1),
            "parameters": results.get('parameters', {}),
            "qa": qa_records,
            "assets": assets
        }
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        jobs[job_id]["assets"] = assets
        primary_sprite = sprite_normalizer.resolve_primary_sprite(jobs[job_id])
        if primary_sprite:
            jobs[job_id]["primary_sprite"] = primary_sprite
            jobs[job_id]["result"].setdefault("metadata", {})["primary_sprite"] = primary_sprite
        
        # Save to persistent storage
        job_storage.save_job(job_id, jobs[job_id])
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Generation failed: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a generation job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = jobs[job_id].copy()
    job_data["job_id"] = job_id
    
    # Ensure all required fields are present with defaults
    job_data.setdefault("status", "unknown")
    job_data.setdefault("progress", 0.0)
    job_data.setdefault("message", "")
    job_data.setdefault("result", None)
    job_data.setdefault("error", None)
    job_data.setdefault("created_at", datetime.now().isoformat())
    job_data.setdefault("completed_at", None)

    return JobStatus(**job_data)

@app.get("/jobs")
async def list_jobs(limit: int = 100):
    """List recent jobs sorted by most recent first"""
    all_jobs = [
        {"job_id": job_id, **job_data}
        for job_id, job_data in jobs.items()
    ]
    # Sort by created_at timestamp, most recent first
    all_jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {"jobs": all_jobs[:limit]}

@app.post("/process-image")
async def process_uploaded_image(
    file: UploadFile = File(...),
    remove_background: bool = True,
    extract_sprites: bool = True
):
    """Process an uploaded sprite sheet"""
    try:
        import io
        
        # Read uploaded file
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        job_id = str(uuid.uuid4())
        output_dir = Path(config['paths']['output_dir']) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "original": None,
            "processed": None,
            "sprites": []
        }
        
        # Save original
        original_path = output_dir / "uploaded_original.png"
        image.save(original_path)
        results["original"] = str(original_path.absolute())
        
        # Remove background
        qa_records = []

        if remove_background:
            processed_image, qc_info = await sprite_processor.remove_background(
                image,
                output_dir=output_dir,
                prefix=f"{job_id}_upload"
            )
        else:
            processed_image = image
            qc_info = sprite_processor._default_qc_info(
                passed=True,
                method_used='none',
                notes=['Background removal skipped']
            )
        
        processed_path = output_dir / "processed.png"
        processed_image.save(processed_path)
        results["processed"] = str(processed_path.absolute())
        results["background_qc"] = qc_info
        qa_records.append({
            "type": "background",
            "label": "Upload",
            "qc": qc_info
        })
        
        # Extract sprites
        if extract_sprites:
            sprites, extraction_qc = await sprite_processor.extract_sprites(processed_image)
            
            for idx, sprite in enumerate(sprites):
                sprite_path = output_dir / f"sprite_{idx}.png"
                sprite['image'].save(sprite_path)
                results["sprites"].append({
                    "path": str(sprite_path.absolute()),
                    "bounds": sprite['bounds'],
                    "size": sprite['size'],
                    "qc": sprite.get('qc', {})
                })
                pixel_image, pixel_preview, pixel_meta = sprite_processor.finalize_pixel_art(sprite['image'])
                pixel_filename = f"sprite_{idx}_pixel.png"
                pixel_path = output_dir / pixel_filename
                pixel_image.save(pixel_path)
                pixel_entry = {
                    "path": str(pixel_path.absolute()),
                    "url": f"/download/{job_id}/{pixel_filename}",
                    **pixel_meta
                }
                if pixel_preview is not None:
                    preview_filename = f"sprite_{idx}_pixel_preview.png"
                    preview_path = output_dir / preview_filename
                    pixel_preview.save(preview_path)
                    pixel_entry["preview"] = {
                        "path": str(preview_path.absolute()),
                        "url": f"/download/{job_id}/{preview_filename}"
                    }
                results.setdefault("pixel_art", []).append(pixel_entry)
            results["sprite_qc"] = extraction_qc
            qa_records.append({
                "type": "extraction",
                "label": "Upload extraction",
                "qc": extraction_qc
            })
        
        results["qa"] = qa_records
        
        return {
            "job_id": job_id,
            "status": "completed",
            "result": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

class CleanSpriteRequest(BaseModel):
    job_id: str = Field(..., description="Job ID containing the raw image")
    image_index: int = Field(0, description="Index of image to clean")
    bg_removal_method: Optional[str] = Field(None, description="Override background removal method")
    rembg_aggressiveness: Optional[int] = Field(None, description="Rembg aggressiveness")

@app.post("/clean-sprite")
async def clean_sprite(request: CleanSpriteRequest):
    """Apply background removal to a raw image"""
    try:
        # Load job data
        if request.job_id not in jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job_data = jobs[request.job_id]
        if not job_data.get("result") or not job_data["result"].get("images"):
            raise HTTPException(status_code=400, detail="No images in job")
        
        images = job_data["result"]["images"]
        if request.image_index >= len(images):
            raise HTTPException(status_code=400, detail="Image index out of range")
        
        image_info = images[request.image_index]
        raw_path = Path(image_info['raw'])
        
        if not raw_path.exists():
            raise HTTPException(status_code=404, detail="Raw image file not found")
        
        # Load image
        image = Image.open(raw_path)
        
        # Apply background removal
        cleaned_image, qc_data = await sprite_processor.remove_background(
            image,
            output_dir=raw_path.parent,
            prefix=f"cleaned_{request.image_index}"
        )
        
        # Save cleaned image
        cleaned_path = raw_path.parent / f"cleaned_{request.image_index}.png"
        cleaned_image.save(cleaned_path)
        
        # Update job data
        if "cleaned_images" not in job_data["result"]:
            job_data["result"]["cleaned_images"] = []
        
        pixel_image, pixel_preview, pixel_meta = sprite_processor.finalize_pixel_art(cleaned_image)
        pixel_filename = f"cleaned_{request.image_index}_pixel.png"
        pixel_path = raw_path.parent / pixel_filename
        pixel_image.save(pixel_path)

        cleaned_info = {
            'path': str(cleaned_path),
            'url': f"/output/{request.job_id}/cleaned_{request.image_index}.png",
            'index': request.image_index,
            'qc_data': qc_data,
            'pixel_art': {
                'path': str(pixel_path),
                'url': f"/output/{request.job_id}/{pixel_filename}",
                **pixel_meta
            }
        }

        if pixel_preview is not None:
            preview_filename = f"cleaned_{request.image_index}_pixel_preview.png"
            preview_path = raw_path.parent / preview_filename
            pixel_preview.save(preview_path)
            cleaned_info['pixel_art']['preview'] = {
                'path': str(preview_path),
                'url': f"/output/{request.job_id}/{preview_filename}"
            }
        job_data["result"]["cleaned_images"].append(cleaned_info)
        
        # Save to persistent storage
        job_storage.save_job(request.job_id, job_data)
        
        return {
            "success": True,
            "cleaned_image": cleaned_info,
            "qc_data": qc_data
        }
        
    except Exception as e:
        logger.error(f"Error cleaning sprite: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class AliveAnimationRequest(BaseModel):
    job_id: str = Field(..., description="Source job ID")
    image_index: int = Field(0, description="Image index to animate")
    use_cleaned: bool = Field(False, description="Use cleaned version if available")

@app.post("/generate-alive-animation")
async def generate_alive_animation(request: AliveAnimationRequest, background_tasks: BackgroundTasks):
    """Generate 5-frame breathing animation from existing sprite"""
    
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Alive animation queued",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "source_job_id": request.job_id,
        "animation_type": "alive"
    }
    
    background_tasks.add_task(process_alive_animation, job_id, request)
    
    return {"job_id": job_id, "status": "queued"}

async def process_alive_animation(job_id: str, request: AliveAnimationRequest):
    """Background task for alive animation generation"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Preparing breathing animation..."

        source_job = jobs.get(request.job_id)
        if not source_job:
            raise Exception("Source job not found")

        normalized_sprite = sprite_normalizer.normalize_sprite_from_job(
            source_job,
            use_cleaned=request.use_cleaned,
        )

        if not normalized_sprite:
            raise Exception("Unable to locate sprite for animation")

        output_dir = Path(config['paths']['output_dir']) / job_id
        jobs[job_id]["message"] = "Synthesizing breathing frames..."

        animation_result = sprite_animator.generate_breathing_cycle(
            normalized_sprite,
            output_dir=output_dir,
        )

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = "Alive animation completed"
        jobs[job_id]["result"] = {
            "frames": [
                {
                    "frame_index": frame.index,
                    "url": frame.url,
                    "path": str(frame.path),
                    "offset": frame.offset,
                    "scale": frame.scale,
                    "phase": frame.phase,
                }
                for frame in animation_result.frames
            ],
            "frame_count": animation_result.frame_count,
            "animation_type": "breathing",
            "sprite_sheet": {
                "path": str(animation_result.sprite_sheet_path),
                "url": animation_result.sprite_sheet_url,
                "frame_size": animation_result.frame_size,
            },
            "metadata": animation_result.metadata,
        }
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

        job_storage.save_job(job_id, jobs[job_id])

    except Exception as e:
        logger.error(f"Error generating alive animation: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Alive animation failed: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()


class AliveSequenceRequest(GenerateRequest):
    class Config:
        extra = "ignore"


@app.post("/generate-alive-sequence", response_model=JobResponse)
async def generate_alive_sequence(request: AliveSequenceRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Alive sequence queued",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "prompt": request.prompt,
        "seed": request.seed,
        "request": request.dict(),
        "mode": "alive_sequence"
    }

    background_tasks.add_task(process_alive_sequence_generation, job_id, request)

    return JobResponse(job_id=job_id, status="queued", message="Alive sequence started")


async def process_alive_sequence_generation(job_id: str, request: AliveSequenceRequest):
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Generating sprite sheet..."
        jobs[job_id]["progress"] = 0.1

        params = GenerationParams(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            preset=request.preset,
            lora=request.lora,
            width=request.width,
            height=request.height,
            seed=request.seed,
            batch_size=request.batch_size or 1,
        )

        generation_result = await sd_client.generate(params)

        if not generation_result or 'images' not in generation_result:
            raise Exception("Failed to generate images for Alive sequence")

        jobs[job_id]["message"] = "Processing sprite sheet..."
        jobs[job_id]["progress"] = 0.4

        output_dir = Path(config['paths']['output_dir']) / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        processed_frames: List[Dict[str, Any]] = []
        sprite_sheet_path: Optional[Path] = None

        for idx, pil_image in enumerate(generation_result['images']):
            raw_path = output_dir / f"raw_{idx}.png"
            pil_image.save(raw_path)

            cleaned_image, qc_info = await sprite_processor.remove_background(
                pil_image,
                output_dir=output_dir,
                prefix=f"alive_{idx}"
            )

            processed_path = output_dir / f"processed_{idx}.png"
            cleaned_image.save(processed_path)

            sprites, extraction_qc = await sprite_processor.extract_sprites(cleaned_image)

            pixel_image, pixel_preview, pixel_meta = sprite_processor.finalize_pixel_art(cleaned_image)
            pixel_filename = f"pixel_{idx}.png"
            pixel_path = output_dir / pixel_filename
            pixel_image.save(pixel_path)
            pixel_entry = {
                "path": str(pixel_path.absolute()),
                "url": f"/download/{job_id}/{pixel_filename}",
                **pixel_meta
            }
            if pixel_preview is not None:
                preview_filename = f"pixel_{idx}_preview.png"
                preview_path = output_dir / preview_filename
                pixel_preview.save(preview_path)
                pixel_entry["preview"] = {
                    "path": str(preview_path.absolute()),
                    "url": f"/download/{job_id}/{preview_filename}"
                }

            if not sprites:
                raise Exception("No sprites detected on generated sheet")

            jobs[job_id]["message"] = "Composing Alive frames..."
            jobs[job_id]["progress"] = 0.7

            for sprite_idx, sprite in enumerate(sprites):
                frame_filename = f"frame_{sprite_idx:03d}.png"
                frame_path = output_dir / frame_filename
                sprite['image'].save(frame_path)

                processed_frames.append({
                    "filename": frame_filename,
                    "path": str(frame_path.absolute()),
                    "size": sprite['size'],
                    "width": sprite['size'][0],
                    "height": sprite['size'][1],
                    "qc": sprite.get('qc', {}),
                    "pixel_art": pixel_entry
                })

            sprite_sheet_path = processed_path

        if not processed_frames:
            raise Exception("Alive sequence produced no frames")

        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Alive sequence completed"
        jobs[job_id]["result"] = {
            "alive_sequence": {
                "job_id": job_id,
                "frames": processed_frames,
                "sprite_sheet": {
                    "filename": sprite_sheet_path.name if sprite_sheet_path else None,
                    "path": str(sprite_sheet_path) if sprite_sheet_path else None,
                },
                "metadata": {
                    "prompt": request.prompt,
                    "seed": generation_result.get('seed'),
                    "frame_count": len(processed_frames)
                }
            }
        }
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

        job_storage.save_job(job_id, jobs[job_id])

    except Exception as e:
        logger.error(f"Error generating alive sequence: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Alive sequence failed: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

@app.get("/download/{job_id}/{filename}")
async def download_file(job_id: str, filename: str):
    """Download a generated file"""
    file_path = Path(config['paths']['output_dir']) / job_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/frame_{direction}_{frame_index}_{timestamp}.png")
async def serve_animation_frame(direction: str, frame_index: int, timestamp: str):
    """Serve animation frames directly from root level"""
    filename = f"frame_{direction}_{frame_index}_{timestamp}.png"
    
    # Check project root first
    root_path = Path(__file__).parent.parent / filename
    if root_path.exists():
        return FileResponse(
            root_path,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Access-Control-Allow-Origin": "*"
            }
        )
    
    # Check output directories
    output_dir = Path(config['paths']['output_dir'])
    for job_dir in output_dir.iterdir():
        if job_dir.is_dir():
            frame_path = job_dir / filename
            if frame_path.exists():
                return FileResponse(
                    frame_path,
                    media_type="image/png",
                    headers={
                        "Cache-Control": "public, max-age=3600",
                        "Access-Control-Allow-Origin": "*"
                    }
                )
    
    raise HTTPException(status_code=404, detail="Animation frame not found")

# ============================================================
# Animation API Endpoints
# ============================================================

class AnimationRequestPayload(BaseModel):
    character_description: str
    animation_type: str
    directions: List[str]
    guidance_method: str = "auto"
    frame_count: Optional[int] = None
    generate_reference_first: bool = True
    style_lora: Optional[str] = None
    lora_weight: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    seed: int = Field(-1, description="Seed (-1 for random)")
    batch_size: int = 1
    source_job_id: Optional[str] = None
    use_cleaned_sprite: bool = True
    motion_pipeline: Optional[Dict[str, Any]] = None
    custom_action: Optional[str] = None


@app.post("/generate-animation")
async def generate_animation(request: AnimationRequestPayload, background_tasks: BackgroundTasks):
    """Generate animation sequence"""
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "Queued",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "prompt": request.character_description,
        "seed": request.seed,
        "request": request.dict(),
        "result_assets": {}
    }
    
    background_tasks.add_task(process_animation_generation, job_id, request)
    
    return JobResponse(job_id=job_id, status="queued", message="Animation generation started")
    

async def process_animation_generation(job_id: str, request_payload: AnimationRequestPayload):
    """Process animation generation in background"""
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["message"] = "Preparing animation..."
        jobs[job_id]["progress"] = 0.1
        
        animation_request = AnimationGenerateRequest(
            character_description=request_payload.character_description,
            directions=request_payload.directions,
            animation_type=request_payload.animation_type,
            guidance_method=request_payload.guidance_method,
            frame_count=request_payload.frame_count,
            generate_reference_first=request_payload.generate_reference_first,
            style_lora=request_payload.style_lora,
            lora_weight=request_payload.lora_weight,
            width=request_payload.width,
            height=request_payload.height,
            steps=request_payload.steps,
            cfg_scale=request_payload.cfg_scale,
            seed=request_payload.seed,
            batch_size=request_payload.batch_size,
            source_job_id=request_payload.source_job_id,
            use_cleaned_sprite=request_payload.use_cleaned_sprite,
            motion_pipeline=request_payload.motion_pipeline,
            custom_action=request_payload.custom_action
        )

        # Import quality generator
        from quality_animation_generator import QualityAnimationGenerator
        quality_generator = QualityAnimationGenerator(sd_client, config)

        # Progress updates
        jobs[job_id]["message"] = "Generating character references..."
        jobs[job_id]["progress"] = 0.3

        # Generate animation using QUALITY system
        result = await quality_generator.generate_coherent_animation(animation_request, job_id=job_id)

        logger.info(f"Quality animation generation complete for {job_id}: success={result.success}")

        if result.success:
            jobs[job_id]["progress"] = 1.0
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["message"] = "Professional animation completed"
            
            # Convert result to dict format
            result_dict = {
                "success": True,
                "animation_sequence": {
                    "animation_type": result.animation_sequence.animation_type.value,
                    "directions": [d.value for d in result.animation_sequence.directions],
                    "frames": [
                        {
                            "image_url": frame.image_url,
                            "direction": frame.direction.value,
                            "frame_index": frame.frame_index,
                            "animation_type": frame.animation_type.value,
                            "seed": frame.seed,
                            "quality_score": frame.quality_score,
                            "metadata": frame.metadata
                        }
                        for frame in result.animation_sequence.frames
                    ],
                    "total_generation_time": result.generation_time,
                    "overall_quality_score": result.animation_sequence.overall_quality_score
                },
                "quality_metrics": result.quality_metrics
            }
            
            jobs[job_id]["result"] = result_dict
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result.error_message
            jobs[job_id]["message"] = f"Animation generation failed: {result.error_message}"

        # CRITICAL: Always set completion time to stop polling
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

        # Save to persistent storage
        job_storage.save_job(job_id, {
            "job_id": job_id,
            "status": jobs[job_id]["status"],
            "message": jobs[job_id]["message"],
            "created_at": jobs[job_id]["created_at"],
            "completed_at": jobs[job_id]["completed_at"],
            "frame_count": len(result.animation_sequence.frames) if result.success else 0,
            "request": jobs[job_id].get("request"),
            "error": jobs[job_id].get("error")
        })

    except Exception as e:
        logger.exception("Animation job %s crashed with unexpected error", job_id)
        
        # Ensure job is marked as failed and completed to stop polling
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Animation generation crashed: {str(e)}"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()  # CRITICAL: Stop polling
        
        logger.error(f"Job {job_id} marked as failed and completed to stop polling")
        
        # Save failed job to storage
        job_storage.save_job(job_id, {
            "job_id": job_id,
            "status": "failed",
            "message": jobs[job_id]["message"],
            "created_at": jobs[job_id]["created_at"],
            "completed_at": jobs[job_id]["completed_at"],
            "error": str(e)
        })

@app.post("/generate-reference-sheet")
async def generate_reference_sheet(request: ReferenceSheetRequest):
    """Generate character reference sheet for consistency"""
    try:
        # Convert to direction enums
        directions = request.to_direction_enums()
        
        # Generate reference images
        reference_images = await animation_generator.generate_character_reference(
            character_description=request.character_description,
            directions=[d.value for d in directions],
            style_lora=request.style_lora,
            lora_weight=request.lora_weight,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed
        )
        
        # Convert PIL images to base64 for JSON response
        import base64
        import io
        
        reference_data = {}
        for direction, image in reference_images.items():
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            reference_data[direction.value] = f"data:image/png;base64,{img_base64}"
        
        return {
            "success": True,
            "reference_images": reference_data,
            "directions": [d.value for d in directions],
            "count": len(reference_images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reference generation failed: {str(e)}")

@app.get("/animation-templates")
async def list_animation_templates():
    """List available animation types and templates"""
    try:
        templates = await animation_generator.get_animation_templates()
        return {
            "templates": templates,
            "animation_types": [t.value for t in AnimationType],
            "directions": [d.value for d in Direction]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get templates: {str(e)}")

@app.get("/guidance-methods")
async def list_guidance_methods():
    """List available guidance methods with capabilities"""
    try:
        capabilities = await animation_generator.get_available_guidance_methods()
        return {
            "guidance_methods": [cap.to_dict() for cap in capabilities],
            "priority_order": config.get('animation', {}).get('guidance', {}).get('priority', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get guidance methods: {str(e)}")

@app.get("/animation-status")
async def get_animation_status():
    """Get animation system status"""
    try:
        status = await animation_generator.get_system_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.post("/test-guidance-method")
async def test_guidance_method(method: str, character_description: str = "pixel art knight in armor"):
    """Test a specific guidance method"""
    try:
        guidance_method = AnimationGuidanceMethod(method)
        success, message = await animation_generator.test_guidance_method(
            guidance_method, character_description
        )
        return {
            "method": method,
            "success": success,
            "message": message
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid guidance method: {method}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

BACKGROUND_DIR = Path(config['paths'].get('background_dir', output_dir / 'backgrounds'))
BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)

BACKGROUND_META = BACKGROUND_DIR / 'backgrounds.json'

DEFAULT_PALETTE = {
    "accent1": "#68a4ff",
    "accent2": "#b08bff",
    "accent3": "#ff76b6",
    "accent4": "#77f0c5",
    "amber": "#ffc86b"
}

def _load_background_gallery() -> List[Dict[str, Any]]:
    if BACKGROUND_META.exists():
        try:
            with open(BACKGROUND_META, 'r', encoding='utf-8') as fh:
                return json.load(fh)
        except Exception as exc:
            logger.warning("Failed to load background metadata: %s", exc)
    return []


def _save_background_gallery(items: List[Dict[str, Any]]):
    try:
        with open(BACKGROUND_META, 'w', encoding='utf-8') as fh:
            json.dump(items, fh, indent=2)
    except Exception as exc:
        logger.warning("Failed to save background metadata: %s", exc)


def _safe_frame_count(result_dict: Dict[str, Any]) -> Optional[int]:
    if not result_dict:
        return None
    animation_sequence = result_dict.get("animation_sequence")
    if not animation_sequence:
        return None
    frames = animation_sequence.get("frames")
    if isinstance(frames, list):
        return len(frames)
    return animation_sequence.get("frame_count")


background_gallery = _load_background_gallery()


def _extract_palette(image_path: Path, color_count: int = 5) -> List[str]:
    try:
        with Image.open(image_path) as img:
            thumb = img.convert('RGB').resize((128, 80))
            palette_image = thumb.convert('P', palette=Image.ADAPTIVE, colors=color_count)
            palette = palette_image.getpalette()
            color_counts = palette_image.getcolors()
            if not color_counts:
                raise ValueError('No palette data')
            sorted_colors = sorted(color_counts, reverse=True)
            hex_colors = []
            for count, index in sorted_colors:
                base = index * 3
                rgb = palette[base:base + 3]
                hex_colors.append('#{:02x}{:02x}{:02x}'.format(*rgb))
            return hex_colors[:color_count]
    except Exception as exc:
        logger.warning("Failed to extract palette for %s: %s", image_path, exc)
        return [DEFAULT_PALETTE['accent1'], DEFAULT_PALETTE['accent2'], DEFAULT_PALETTE['accent3']]


class BackgroundRequest(BaseModel):
    prompt: str = Field(..., description="Prompt describing the new background")


class BackgroundUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Rename the background")
    favorite: Optional[bool] = Field(None, description="Mark as favorite")
    is_active: Optional[bool] = Field(None, description="Set as current background")


class GalleryBackgroundRequest(BaseModel):
    url: str = Field(..., description="Absolute or relative URL to image")
    name: Optional[str] = Field(None, description="Display name")
    source: str = Field("gallery", description="Source descriptor")
    palette: Optional[List[str]] = Field(None, description="Optional precomputed palette")


@app.get("/backgrounds")
async def list_backgrounds():
    return {"backgrounds": background_gallery}


@app.post("/generate_background")
async def generate_background(request: BackgroundRequest):
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt required")

    background_id = uuid.uuid4().hex
    target_path = BACKGROUND_DIR / f"{background_id}.png"

    params = GenerationParams(
        prompt=f"{prompt}, sweeping vista, cinematic lighting, 2048x1024, pixel art landscape",
        negative_prompt="low detail, blurry, text, watermark",
        preset=None,
        width=2048,
        height=1024,
        steps=40,
        cfg_scale=7.0,
        seed=-1,
        batch_size=1
    )

    try:
        generation = await sd_client.generate(params)
        images = generation.get('images')
        if not images:
            raise RuntimeError('No image generated')

        image = images[0]
        image.save(target_path)

        palette_colors = _extract_palette(target_path)
        entry = {
            "id": background_id,
            "prompt": prompt,
            "name": prompt[:64].strip() if prompt else f"Background {len(background_gallery) + 1}",
            "created_at": datetime.now().isoformat(),
            "url": f"/backgrounds/{target_path.name}",
            "is_active": True,
            "favorite": False,
            "palette": palette_colors
        }

        for existing in background_gallery:
            existing['is_active'] = False
        background_gallery.insert(0, entry)
        _save_background_gallery(background_gallery)

        return entry
    except Exception as exc:
        logger.exception("Background generation failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.patch("/backgrounds/{background_id}")
async def update_background(background_id: str, payload: BackgroundUpdateRequest):
    entry = next((item for item in background_gallery if item['id'] == background_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Background not found")

    updated = False
    if payload.name is not None:
        entry['name'] = payload.name.strip() or entry['name']
        updated = True
    if payload.favorite is not None:
        entry['favorite'] = payload.favorite
        updated = True
    if payload.is_active:
        for existing in background_gallery:
            existing['is_active'] = existing['id'] == background_id
        updated = True

    if updated:
        _save_background_gallery(background_gallery)

    return entry


@app.get("/backgrounds/{filename}")
async def serve_background(filename: str):
    path = BACKGROUND_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Background not found")
    return FileResponse(path)


@app.post("/backgrounds/reset")
async def reset_background():
    for existing in background_gallery:
        existing['is_active'] = False
    _save_background_gallery(background_gallery)
    return {
        "url": "/assets/background.png",
        "palette": [
            DEFAULT_PALETTE['accent1'],
            DEFAULT_PALETTE['accent2'],
            DEFAULT_PALETTE['accent3'],
            DEFAULT_PALETTE['accent4'],
            DEFAULT_PALETTE['amber']
        ]
    }


@app.post("/backgrounds/from-gallery")
async def set_background_from_gallery(payload: GalleryBackgroundRequest):
    image_url = payload.url
    if not image_url:
        raise HTTPException(status_code=400, detail="Image URL required")

    try:
        if image_url.startswith('http://') or image_url.startswith('https://'):
            raise HTTPException(status_code=400, detail="External URLs not supported")
        else:
            if image_url.startswith('/download/'):
                parts = image_url.strip('/').split('/')
                if len(parts) != 3 or parts[0] != 'download':
                    raise HTTPException(status_code=400, detail="Invalid gallery URL")
                job_id, filename = parts[1], parts[2]
                candidate = Path(config['paths']['output_dir']) / job_id / filename
                if not candidate.exists():
                    raise HTTPException(status_code=404, detail="Gallery asset not found")
                disk_path = candidate
            else:
                relative_path = image_url.lstrip('/')
                disk_path = Path(relative_path)
                if not disk_path.exists():
                    disk_path = Path(config['paths']['output_dir']) / relative_path
                if not disk_path.exists():
                    raise HTTPException(status_code=404, detail="Image not found on disk")
            with open(disk_path, 'rb') as fh:
                content = fh.read()

        background_id = uuid.uuid4().hex
        target_path = BACKGROUND_DIR / f"{background_id}.png"
        with open(target_path, 'wb') as fh:
            fh.write(content)

        palette_colors = payload.palette or _extract_palette(target_path)
        entry = {
            "id": background_id,
            "prompt": payload.name or "Gallery background",
            "name": payload.name or f"Gallery Background {len(background_gallery) + 1}",
            "created_at": datetime.now().isoformat(),
            "url": f"/backgrounds/{target_path.name}",
            "is_active": True,
            "favorite": False,
            "palette": palette_colors,
            "source": payload.source
        }

        for existing in background_gallery:
            existing['is_active'] = False
        background_gallery.insert(0, entry)
        _save_background_gallery(background_gallery)

        return entry

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to set gallery background")
        raise HTTPException(status_code=500, detail=str(exc))

if __name__ == "__main__":
    import uvicorn
    
    # Ensure output directories exist
    Path(config['paths']['output_dir']).mkdir(parents=True, exist_ok=True)
    Path(config['paths']['temp_dir']).mkdir(parents=True, exist_ok=True)
    Path(config['paths']['cache_dir']).mkdir(parents=True, exist_ok=True)
    
    # Mount static files AFTER all routes to avoid conflicts
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
    
    # Mount frontend assets (CSS, JS, images)
    frontend_dir = Path(__file__).parent.parent / "frontend"
    if frontend_dir.exists():
        app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")
    
    # Frame serving handled by specific endpoint above
    
    uvicorn.run(
        app,
        host=config['api']['host'],
        port=config['api']['port'],
        log_level="info"
    )

