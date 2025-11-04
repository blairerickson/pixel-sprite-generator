#!/bin/bash
# Start Backend API

cd "$(dirname "$0")/backend"
source venv/bin/activate
python api.py


