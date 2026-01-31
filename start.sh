#!/bin/bash

# Drone Detection System - Automated Start Script
# This script starts both the backend and frontend servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/drone_detection_backend"
FRONTEND_DIR="$SCRIPT_DIR/drone_detection_frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           DRONE DETECTION SYSTEM - STARTUP                   ║"
echo "║     YOLO-powered Cross-Screen Tracking with RAG AI           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Cleanup complete.${NC}"
}

trap cleanup EXIT

# Check Python
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    exit 1
fi

# Check Node.js
if ! command_exists node; then
    echo -e "${RED}Error: Node.js is required but not installed.${NC}"
    exit 1
fi

# Setup Backend
echo -e "${BLUE}[1/4] Setting up Backend...${NC}"
cd "$BACKEND_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env from example..."
    cp .env.example .env
fi

# Create models directory
mkdir -p models

echo -e "${GREEN}Backend setup complete.${NC}"

# Setup Frontend
echo -e "${BLUE}[2/4] Setting up Frontend...${NC}"
cd "$FRONTEND_DIR"

# Install npm dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing npm dependencies..."
    npm install --silent
fi

echo -e "${GREEN}Frontend setup complete.${NC}"

# Start Backend
echo -e "${BLUE}[3/4] Starting Backend Server...${NC}"
cd "$BACKEND_DIR"
source venv/bin/activate

# Start uvicorn in background
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo -e "${GREEN}Backend started on http://localhost:8000${NC}"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - WebSocket: ws://localhost:8000/ws"

# Wait for backend to be ready
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/status > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready!${NC}"
        break
    fi
    sleep 1
done

# Start Frontend
echo -e "${BLUE}[4/4] Starting Frontend Server...${NC}"
cd "$FRONTEND_DIR"

npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}Frontend started on http://localhost:3000${NC}"

# Print summary
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    SYSTEM READY                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  http://localhost:3000                            ║"
echo "║  Backend:   http://localhost:8000                            ║"
echo "║  API Docs:  http://localhost:8000/docs                       ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Features:                                                   ║"
echo "║  - 6 simulated drone camera feeds                            ║"
echo "║  - YOLO object detection with tracking                       ║"
echo "║  - Cross-screen object prediction                            ║"
echo "║  - Leaflet map with live coordinates                         ║"
echo "║  - Mistral AI chat (configure API key in settings)           ║"
echo "║  - RAG-based detection history query                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Press Ctrl+C to stop all services                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Wait for processes
wait
