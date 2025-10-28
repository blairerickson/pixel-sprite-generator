# Pixel Sprite Generator - Windows Setup Guide

## ✅ Windows Setup Process

This guide documents the setup process for Windows, addressing the same Python compatibility issues we solved on macOS.

## Prerequisites

- Windows 10/11
- Git installed
- Python 3.10.6 (CRITICAL - not 3.11 or 3.12)
- Visual Studio Build Tools (for compiling packages)

## Step-by-Step Setup

### 1. Install Python 3.10.6
**CRITICAL**: Do NOT use Python 3.11 or 3.12 - they cause the same tokenizers and distutils issues we encountered on macOS.

**Download Python 3.10.6:**
- Go to: https://www.python.org/downloads/release/python-3106/
- Download: `Windows installer (64-bit)` 
- During installation:
  - ✅ Check "Add Python to PATH"
  - ✅ Check "Install for all users" (if you have admin rights)

**Verify installation:**
```cmd
python --version
# Should show: Python 3.10.6
```

### 2. Install Visual Studio Build Tools
Required for compiling Python packages with C extensions.

**Download and install:**
- Go to: https://visualstudio.microsoft.com/downloads/
- Download: "Build Tools for Visual Studio 2022"
- During installation, select:
  - ✅ C++ build tools
  - ✅ Windows 10/11 SDK
  - ✅ CMake tools

### 3. Clone and Setup Repository
```cmd
git clone <your-repo-url>
cd pixel-sprite-generator
python scripts/bootstrap.py setup
```

### 4. Download Required Models
Same models as macOS - download manually:

**Main Model:**
- Download: https://civitai.com/models/34/all-in-one-pixel-model
- Place in: `stable-diffusion-webui\models\Stable-diffusion\allInOnePixelModel_v1.ckpt`

**LoRA Model:**
- Download: https://civitai.com/models/120096/pixel-art-xl  
- Place in: `stable-diffusion-webui\models\Lora\pixelArtDiffusionXL_spriteShaper.safetensors`

### 5. Start the System

**Command Prompt 1 - Stable Diffusion WebUI:**
```cmd
cd stable-diffusion-webui
webui.bat --api --listen --port 7860
```

**Command Prompt 2 - Backend API:**
```cmd
cd backend
venv\Scripts\activate
python api.py
```

**Command Prompt 3 - Frontend (Optional):**
```cmd
cd frontend
python -m http.server 8010
```

### 6. Access the System
- **Web Interface**: http://127.0.0.1:8010
- **API Documentation**: http://127.0.0.1:8010/docs
- **Stable Diffusion WebUI**: http://127.0.0.1:7860

## Windows-Specific Considerations

### GPU Acceleration
- **NVIDIA GPUs**: CUDA support should work automatically
- **AMD GPUs**: May need ROCm or DirectML
- **Intel GPUs**: May need Intel Extension for PyTorch

**Check GPU support:**
```cmd
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### Path Issues
- Use backslashes (`\`) in Windows paths
- Ensure Python is in your PATH environment variable
- Use `cmd` or PowerShell (avoid Git Bash for some operations)

### Virtual Environment
The bootstrap script should create a virtual environment automatically:
```cmd
# If manual activation needed:
cd backend
venv\Scripts\activate
```

## Troubleshooting

### Python Version Issues
**Problem**: Tokenizers compilation errors, distutils module not found
**Solution**: 
- Uninstall any Python 3.11/3.12 versions
- Install Python 3.10.6 specifically
- Delete `stable-diffusion-webui\venv` folder and restart

### Build Tools Issues
**Problem**: "Microsoft Visual C++ 14.0 is required"
**Solution**: Install Visual Studio Build Tools (step 2 above)

### Path Issues
**Problem**: "python is not recognized"
**Solution**: 
- Reinstall Python 3.10.6 with "Add to PATH" checked
- Or manually add Python to PATH in System Environment Variables

### Permission Issues
**Problem**: Access denied errors
**Solution**: Run Command Prompt as Administrator

### Port Already in Use
**Problem**: "Address already in use"
**Solution**: 
```cmd
# Find and kill process using port 7860
netstat -ano | findstr :7860
taskkill /PID <PID_NUMBER> /F
```

## Expected Issues and Solutions

### 1. Tokenizers Compilation Error
```
error: could not compile `tokenizers` (lib) due to 1 previous error
ERROR: Failed building wheel for tokenizers
```
**Cause**: Python 3.11/3.12 compatibility issue
**Solution**: Use Python 3.10.6

### 2. Distutils Module Error
```
ModuleNotFoundError: No module named 'distutils'
```
**Cause**: Python 3.12 removed distutils
**Solution**: Use Python 3.10.6

### 3. CUDA/GPU Issues
```
Warning: caught exception 'Torch not compiled with CUDA enabled'
```
**Cause**: PyTorch not compiled with CUDA support
**Solution**: Install CUDA-enabled PyTorch or use CPU mode

## System Requirements

### Minimum Requirements
- Windows 10 (64-bit)
- 8GB RAM
- 10GB free disk space
- Python 3.10.6

### Recommended Requirements  
- Windows 11 (64-bit)
- 16GB RAM
- 20GB free disk space
- NVIDIA GPU with 8GB+ VRAM
- Python 3.10.6

## Batch Files for Easy Startup

Create these batch files for easy startup:

**start_webui.bat:**
```batch
@echo off
cd stable-diffusion-webui
webui.bat --api --listen --port 7860
pause
```

**start_backend.bat:**
```batch
@echo off
cd backend
call venv\Scripts\activate
python api.py
pause
```

**start_frontend.bat:**
```batch
@echo off
cd frontend
python -m http.server 8010
pause
```

## API Usage Example
```cmd
curl -X POST http://127.0.0.1:8010/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"a cute pixel art cat character\", \"preset\": \"character_sprite\", \"width\": 512, \"height\": 512, \"steps\": 25}"
```

## Generated Files
- Output images: `output\` directory
- Temporary files: `temp\` directory  
- Cache files: `cache\` directory

## Key Differences from macOS

1. **Python Installation**: Use Windows installer instead of Homebrew
2. **Build Tools**: Install Visual Studio Build Tools instead of Xcode Command Line Tools
3. **Paths**: Use backslashes (`\`) instead of forward slashes (`/`)
4. **Virtual Environment**: Use `venv\Scripts\activate` instead of `source venv/bin/activate`
5. **GPU**: CUDA instead of MPS for NVIDIA GPUs

---
*Last updated: October 27, 2025*
*Based on successful macOS setup process*
