# Pixel Sprite Generator

Unified toolchain for generating, cleaning, and previewing pixel art sprites powered by Stable Diffusion.

## Prerequisites

- Windows 10/11, macOS 12+, or a modern Linux distro
- Python 3.10 installed and available on your PATH
- 15 GB free disk space (models + cache)

## First-Time Setup (Windows)

1. Double-click `SETUP_WINDOWS_SIMPLE.bat`
2. Follow the prompts (first run will download SD dependencies and models)
3. After completion, launch with `START_WINDOWS.bat`

## First-Time Setup (macOS / Linux)

1. Install Python 3.10, Git, and system build tools (`xcode-select --install` on macOS, `sudo apt install build-essential python3.10-venv` on Ubuntu)
2. Run:
   ```bash
   python3.10 -m venv backend/venv
   source backend/venv/bin/activate
   python scripts/bootstrap.py setup
   ```
3. Launch services:
   ```bash
   source backend/venv/bin/activate
   python backend/api.py
   ```
   In a second terminal:
   ```bash
   cd frontend
   python -m http.server 8010
   ```
   Optional: start Stable Diffusion on Linux/macOS with `bash stable-diffusion-webui/webui.sh --api --listen --port 7860`

## Daily Usage

1. Launch Stable Diffusion (Windows: `1_START_SD.bat`)
2. Start backend (`START_PEARL_SALON.bat` launches backend + frontend automatically)
3. Open http://127.0.0.1:8010 to use the frontend

## Stable Diffusion Assets

Assets are defined in `sd-assets.manifest.json`; `scripts/bootstrap.py setup` verifies and downloads required checkpoints/LoRAs into `stable-diffusion-webui/models`.

## Troubleshooting

- If Stable Diffusion fails to launch, open `stable-diffusion-webui/webui-user.bat` manually and check console logs.
- The launcher waits for `http://127.0.0.1:7860/sdapi/v1/sd-models`; ensure the API flag is present.
- To refresh assets without full setup: `backend/venv/Scripts/python.exe scripts/bootstrap.py download-assets`

