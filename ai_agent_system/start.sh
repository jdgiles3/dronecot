#!/bin/bash

# AI Agent System - Start Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          MULTI-AGENT AI SYSTEM - 2026 EDITION                ║"
echo "║     Orchestrated Small Language Models with Full Pipeline    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Warning: Docker not found. Infrastructure services won't start.${NC}"
    DOCKER_AVAILABLE=false
else
    DOCKER_AVAILABLE=true
fi

# Start infrastructure if Docker available
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo -e "${PURPLE}[1/4] Starting infrastructure services...${NC}"
    cd "$SCRIPT_DIR"
    docker-compose up -d 2>/dev/null || echo "Docker services may already be running"
    
    echo "Waiting for services to be ready..."
    sleep 10
fi

# Setup Python environment
echo -e "${PURPLE}[2/4] Setting up Python environment...${NC}"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium 2>/dev/null || echo "Playwright browsers may already be installed"

# Create .env if needed
if [ ! -f ".env" ]; then
    cp .env.example .env
fi

# Setup frontend
echo -e "${PURPLE}[3/4] Setting up frontend...${NC}"
cd "$SCRIPT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm install --silent 2>/dev/null || echo "npm install may have issues"
fi

# Start services
echo -e "${PURPLE}[4/4] Starting application...${NC}"

# Start backend
cd "$SCRIPT_DIR"
source venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 5

# Start frontend
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Shutdown complete.${NC}"
}

trap cleanup EXIT

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    SYSTEM READY                              ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Dashboard:  http://localhost:3001                           ║"
echo "║  API:        http://localhost:8001                           ║"
echo "║  API Docs:   http://localhost:8001/docs                      ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Agents: alert, analysis, task, vision, data                 ║"
echo "║  Services: Kafka, Redis, OpenSearch, SeaweedFS, Tika         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Press Ctrl+C to stop                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

wait
