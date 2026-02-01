# DroneCOT Extended Systems

This repository contains two advanced AI-powered systems built on top of the DroneCOT platform:

1. **Drone Detection System** - YOLO-based object detection with cross-screen tracking
2. **Multi-Agent AI System** - Orchestrated small language models with full data pipeline

---

## Table of Contents

- [Quick Start](#quick-start)
- [System 1: Drone Detection](#system-1-drone-detection)
- [System 2: Multi-Agent AI](#system-2-multi-agent-ai)
- [Infrastructure Services](#infrastructure-services)
- [User Experience Guide](#user-experience-guide)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

The devcontainer automatically installs:
- Python 3.12
- Node.js 20
- npm 10

### Running the Drone Detection System

```bash
# Terminal 1: Start backend
cd drone_detection_backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
cd drone_detection_frontend
npm install
npm run dev
```

**Access Points:**
- Frontend Dashboard: `http://localhost:3000`
- API Documentation: `http://localhost:8000/docs`
- WebSocket: `ws://localhost:8000/ws`

### Running the Multi-Agent AI System

```bash
# Terminal 1: Start backend
cd ai_agent_system
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Start frontend
cd ai_agent_system/frontend
npm install
npm run dev
```

**Access Points:**
- Dashboard: `http://localhost:3001`
- API Documentation: `http://localhost:8001/docs`
- WebSocket: `ws://localhost:8001/ws`

---

## System 1: Drone Detection

### Overview

A real-time drone detection system using YOLOv8 with cross-screen object tracking capabilities.

### Features

| Feature | Description |
|---------|-------------|
| **6-Camera Grid** | 2x3 video player layout with glassmorphism UI |
| **YOLO Detection** | Real-time object detection using YOLOv8 |
| **Cross-Screen Tracking** | Predicts object movement across camera gaps |
| **Live Map** | Leaflet map with GPS coordinates |
| **AI Chat** | Mistral AI integration for detection queries |
| **RAG Storage** | ChromaDB for detection history |

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│  │ Cam 1   │ │ Cam 2   │ │ Cam 3   │  ← 6 Video       │
│  ├─────────┤ ├─────────┤ ├─────────┤    Players        │
│  │ Cam 4   │ │ Cam 5   │ │ Cam 6   │                   │
│  └─────────┘ └─────────┘ └─────────┘                   │
│  ┌─────────────────┐ ┌─────────────────┐               │
│  │   Leaflet Map   │ │   AI Chat       │               │
│  └─────────────────┘ └─────────────────┘               │
└─────────────────────────────────────────────────────────┘
                          │ WebSocket
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ YOLO Detector│  │ Video Proc.  │  │ RAG Engine   │  │
│  │ + Tracking   │  │ 6 Streams    │  │ ChromaDB     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Cross-Screen Tracking

The system predicts object movement across camera gaps:

1. **Velocity Calculation** - Tracks object velocity over multiple frames
2. **Exit Prediction** - Determines which edge the object will exit from
3. **Entry Prediction** - Calculates entry point on adjacent screen
4. **Track Continuity** - Maintains consistent track ID across screens

```
Screen Layout:
┌───────┐ ┌───────┐ ┌───────┐
│   0   │ │   1   │ │   2   │
├───────┤ ├───────┤ ├───────┤
│   3   │ │   4   │ │   5   │
└───────┘ └───────┘ └───────┘

Object moving right from Screen 0 → predicted to enter Screen 1
```

### Configuration

Edit `drone_detection_backend/.env`:

```env
# Mistral AI (for chat functionality)
MISTRAL_API_KEY=your_key_here

# Detection thresholds
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45

# Cross-screen tracking
VELOCITY_PREDICTION_ENABLED=true
```

---

## System 2: Multi-Agent AI

### Overview

An orchestrated system of 5 specialized AI agents powered by local small language models (via Ollama).

### The 5 Agents

| Agent | Model | Capabilities |
|-------|-------|--------------|
| **Alert Agent** | Phi-3 Mini | Anomaly detection, threshold monitoring, alert generation |
| **Analysis Agent** | Mistral 7B | Pattern recognition, insights, reports, forecasting |
| **Task Agent** | CodeLlama 7B | Playwright automation, code generation, web scraping |
| **Vision Agent** | LLaVA 7B | Image analysis, OCR, visual task guidance |
| **Data Agent** | TinyLlama | Database queries, shift logs, search operations |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + Framer Motion)             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           Triple-Glass Floating Panel UI                 │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                  │    │
│  │  │ AI Chat │  │  Stats  │  │  Data   │  ← Flip panels   │    │
│  │  └─────────┘  └─────────┘  └─────────┘    on corners    │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐       │    │
│  │  │    Live Map         │  │   Agent Status      │       │    │
│  │  │  (Clustering)       │  │                     │       │    │
│  │  └─────────────────────┘  └─────────────────────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │ WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (FastAPI)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Intelligent Task Router                       │  │
│  │   "analyze patterns" → Analysis Agent                      │  │
│  │   "create alert" → Alert Agent                             │  │
│  │   "scrape website" → Task Agent                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │           │           │           │           │        │
│         ▼           ▼           ▼           ▼           ▼        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Alert   │ │Analysis │ │  Task   │ │ Vision  │ │  Data   │   │
│  │ Agent   │ │ Agent   │ │  Agent  │ │  Agent  │ │  Agent  │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE SERVICES                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │  Kafka  │ │  Redis  │ │OpenSearch│ │SeaweedFS│ │  Tika   │   │
│  │ Messages│ │  Cache  │ │  Search │ │ Storage │ │   OCR   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OLLAMA                                   │
│              Local Small Language Models                         │
│  phi3:mini | mistral:7b | codellama:7b | llava:7b | tinyllama   │
└─────────────────────────────────────────────────────────────────┘
```

### Infrastructure Services

| Service | Port | Purpose | Required |
|---------|------|---------|----------|
| **Kafka** | 29092 | Message broker for async events | Optional |
| **Redis** | 6379 | Caching, sessions, rate limiting | Optional |
| **OpenSearch** | 9200 | Full-text search, vector storage | Optional |
| **SeaweedFS** | 8888 | Distributed file storage | Optional |
| **Tika** | 9998 | Document processing, OCR | Optional |
| **Ollama** | 11434 | Local LLM inference | Required |

**Note:** The system gracefully degrades if services are unavailable. Only Ollama is required for core AI functionality.

### Starting Infrastructure (Docker)

```bash
cd ai_agent_system

# Start all services (requires Docker)
docker-compose up -d

# Or start only essential services
docker-compose up -d redis ollama

# Check status
docker-compose ps
```

**GPU Note:** The Ollama container in docker-compose requires NVIDIA GPU. For CPU-only:

```bash
# Install Ollama directly
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull phi3:mini
ollama pull mistral:7b
ollama pull tinyllama
```

---

## User Experience Guide

### Drone Detection Dashboard

When you open `http://localhost:3000`:

1. **Video Grid (Top)** - 6 camera feeds in a 2x3 grid
   - Each feed shows real-time object detection
   - Bounding boxes with class labels and confidence
   - Velocity vectors showing predicted movement
   - "→ Screen X" indicator for cross-screen predictions

2. **Live Map (Bottom Left)** - Leaflet map
   - Markers for each detected object
   - Color-coded by detection class
   - Track paths showing movement history
   - Click markers for detailed info

3. **AI Chat (Right)** - Query detection history
   - "What drones were detected today?"
   - "Show tracking patterns"
   - Requires Mistral API key in settings

4. **Metadata Panel** - Real-time statistics
   - Detection counts by class
   - Active tracks
   - Cross-screen movements

### Multi-Agent AI Dashboard

When you open `http://localhost:3001`:

1. **Space Void Background** - Animated stars and grid
   - Creates depth and futuristic atmosphere

2. **Glass Panels** - Triple-layer frosted glass effect
   - **Click any corner** to flip the panel
   - **Double-click corner** for quick flip
   - Back side shows live data visualization

3. **AI Chat Panel** - Talk to the agents
   - Natural language queries
   - Auto-routes to appropriate agent
   - Examples:
     - "Analyze the patterns in recent data"
     - "Generate an alert for high CPU usage"
     - "Search for documents about security"
     - "Create a shift log for today"

4. **Live Statistics** - Real-time metrics
   - Messages processed
   - Active connections
   - Documents ingested
   - Response times

5. **Agent Status** - Monitor all 5 agents
   - Online/offline status
   - Request counts
   - Model information

6. **Real-Time Map** - Node visualization
   - Agent nodes (blue)
   - Data nodes (green)
   - Connection lines showing relationships
   - Clustering for dense areas

### Example Interactions

**Alert Agent:**
```
User: "Check if there are any anomalies in the system metrics"
Agent: Analyzes data, returns structured alert with severity, 
       affected components, and recommended actions
```

**Analysis Agent:**
```
User: "Generate a weekly report on ingestion activity"
Agent: Creates comprehensive report with executive summary,
       key metrics, trends, and recommendations
```

**Task Agent:**
```
User: "Scrape the pricing table from example.com"
Agent: Generates Playwright automation, executes it,
       returns extracted data
```

**Data Agent:**
```
User: "Find all documents tagged with 'security' from last week"
Agent: Converts to OpenSearch query, executes, returns results
```

---

## Troubleshooting

### Devcontainer Issues

**Problem:** Build fails with package errors
**Solution:** The devcontainer uses Ubuntu 24.04. Some packages have been renamed:
- `libgl1-mesa-glx` → `libgl1`

**Problem:** Python/Node not found
**Solution:** Devcontainer features install these. Rebuild if needed:
```bash
# In Gitpod
gitpod env devcontainer rebuild
```

### Backend Issues

**Problem:** "Ollama not available"
**Solution:** Install and start Ollama:
```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Start
ollama serve

# Pull models
ollama pull phi3:mini
```

**Problem:** "OpenSearch connection refused"
**Solution:** OpenSearch is optional. The system works without it but search features will be limited.

### Frontend Issues

**Problem:** WebSocket disconnected
**Solution:** Ensure backend is running on the correct port (8000 for drone detection, 8001 for AI system)

**Problem:** Map not loading
**Solution:** Check browser console for Leaflet errors. May need to clear cache.

### Docker Issues

**Problem:** Ollama container fails (GPU required)
**Solution:** Use CPU-only Ollama installation instead of Docker:
```bash
# Remove from docker-compose
docker-compose up -d --scale ollama=0

# Install locally
curl -fsSL https://ollama.com/install.sh | sh
```

---

## API Reference

### Drone Detection API (Port 8000)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | System status |
| `/streams` | GET/POST | Manage video streams |
| `/detections` | GET | Current detections |
| `/tracks` | GET | Cross-screen tracks |
| `/map/markers` | GET | Map markers |
| `/chat` | POST | AI chat query |
| `/ws` | WebSocket | Real-time updates |

### Multi-Agent API (Port 8001)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/stats` | GET | System statistics |
| `/chat` | POST | Send message to agents |
| `/agents` | GET | List all agents |
| `/tasks` | POST | Execute multi-step task |
| `/search` | POST | Search indexed data |
| `/alerts` | GET/POST | Manage alerts |
| `/shift-logs` | GET/POST | Shift log management |
| `/ingest/data` | POST | Ingest structured data |
| `/ingest/file` | POST | Ingest file |
| `/ws` | WebSocket | Real-time updates |

---

## License

Apache 2.0 - See LICENSE file
