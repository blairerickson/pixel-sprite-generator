import os
import sys
import platform
import pathlib
import subprocess

BASE = pathlib.Path(__file__).resolve().parent
BACKEND = BASE / 'backend'
VENVBIN = BACKEND / 'venv' / 'bin'

REPORT = {}

Report sections = []

# Python versions
REPORT['python_env'] = {
    'sys.version': sys.version,
    'sys.executable': sys.executable,
    'platform': platform.platform(),
    'cwd': os.getcwd(),
}

# Virtualenv check
venv_exists = VENVBIN.exists()
REPORT['backend_venv_exists'] = venv_exists
if venv_exists:
    REPORT['backend_venv_contents'] = sorted(p.name for p in VENVBIN.glob('*'))

# config.yaml snippet
config_path = BACKEND / 'config.yaml'
if config_path.exists():
    REPORT['backend_config'] = config_path.read_text().splitlines()[:40]

# pip freeze for backend
freeze_output = subprocess.run([
    str(VENVBIN / 'python'), '-m', 'pip', 'freeze'
], capture_output=True, text=True)
REPORT['pip_freeze_backend'] = freeze_output.stdout.splitlines()[:200]

# Backend health
from urllib import request, error
try:
    REPORT['health'] = request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode()
except Exception as exc:
    REPORT['health_error'] = str(exc)

# Check Windows SD port from WSL
try:
    REPORT['sd_docs'] = request.urlopen('http://172.23.224.1:7860/docs', timeout=3).status
except Exception as exc:
    REPORT['sd_docs_error'] = str(exc)

import json
print(json.dumps(REPORT, indent=2))
