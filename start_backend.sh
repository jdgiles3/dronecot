#!/bin/bash

# Start Backend Only
cd "$(dirname "$0")/drone_detection_backend"

# Create venv if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Create .env if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

mkdir -p models

echo "Starting backend on http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
