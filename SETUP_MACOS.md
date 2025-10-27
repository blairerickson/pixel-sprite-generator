# Pixel Sprite Generator - macOS Setup Guide

## ✅ Successfully Tested Setup Process

This guide documents the working setup process for macOS (tested on macOS with Apple Silicon).

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3)
- Homebrew installed
- Git installed

## Quick Setup Steps

### 1. Install Python 3.10
```bash
brew install python@3.10
```

### 2. Clone and Setup
```bash
git clone <your-repo-url>
cd pixel-sprite-generator
python3 scripts/bootstrap.py setup
```

### 3. Download Required Models
The system requires these models to be downloaded manually:

**Main Model:**
- Download: https://civitai.com/models/34/all-in-one-pixel-model
- Place in: `stable-diffusion-webui/models/Stable-diffusion/allInOnePixelModel_v1.ckpt`

**LoRA Model:**
- Download: https://civitai.com/models/120096/pixel-art-xl
- Place in: `stable-diffusion-webui/models/Lora/pixelArtDiffusionXL_spriteShaper.safetensors`

### 4. Start the System

**Terminal 1 - Stable Diffusion WebUI:**
```bash
cd stable-diffusion-webui
PYTHON=/opt/homebrew/bin/python3.10 bash webui.sh --api --listen --port 7860 --skip-python-version-check
```

**Terminal 2 - Backend API:**
```bash
cd backend
source venv/bin/activate
python api.py
```

**Terminal 3 - Frontend (Optional):**
```bash
cd frontend
python3 -m http.server 8010
```

### 5. Access the System
- **Web Interface**: http://127.0.0.1:8010
- **API Documentation**: http://127.0.0.1:8010/docs
- **Stable Diffusion WebUI**: http://127.0.0.1:7860

## Important Notes

### Python Version Compatibility
- **CRITICAL**: Use Python 3.10.19 (not 3.12)
- Python 3.12 causes tokenizers compilation errors and distutils module issues
- The WebUI is tested with Python 3.10.6

### GPU Acceleration
- The system supports Apple Silicon GPU acceleration via MPS (Metal Performance Shaders)
- GPU acceleration is automatically detected and enabled when available
- Check GPU usage with: `python3 -c "import torch; print('MPS available:', torch.backends.mps.is_available())"`

### Troubleshooting

**If you get tokenizers compilation errors:**
- Ensure you're using Python 3.10
- Delete the `stable-diffusion-webui/venv` folder and restart

**If you get "distutils module not found" errors:**
- This is a Python 3.12 compatibility issue
- Downgrade to Python 3.10

**If models aren't loading:**
- Check that model files are in the correct directories
- Verify file names match exactly (case-sensitive)

## System Status
✅ Python 3.10.19 compatibility  
✅ Tokenizers compilation resolved  
✅ Distutils module issues resolved  
✅ All services communicating properly  
✅ Generation requests working  
✅ GPU acceleration available  

## API Usage Example
```bash
curl -X POST http://127.0.0.1:8010/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a cute pixel art cat character",
    "preset": "character_sprite",
    "width": 512,
    "height": 512,
    "steps": 25
  }'
```

## Generated Files
- Output images: `output/` directory
- Temporary files: `temp/` directory
- Cache files: `cache/` directory

---
*Last updated: October 27, 2025*
*Tested on: macOS with Apple Silicon*
