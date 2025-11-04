#!/bin/bash
# Start Stable Diffusion WebUI

cd "$(dirname "$0")/stable-diffusion-webui"
PYTHON=/opt/homebrew/bin/python3.10 bash webui.sh --api --listen --port 7860 --skip-python-version-check


