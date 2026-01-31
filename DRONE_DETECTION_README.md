# Drone Detection System

YOLO-powered drone object detection with cross-screen tracking, Leaflet mapping, and RAG-based AI assistant.

## Features

- **6-Camera Grid Display**: Glassmorphism UI with 2x3 video player grid
- **YOLO Object Detection**: Real-time detection using YOLOv8
- **Cross-Screen Tracking**: Predicts object movement across camera gaps
- **Live Leaflet Map**: GPS coordinates with track visualization
- **Mistral AI Chat**: RAG-based query system for detection history
- **Metadata Streaming**: Live JSON feed of detection data

## Architecture

```
drone_detection_backend/     # FastAPI backend
├── app/
│   ├── main.py             # FastAPI application
│   ├── config.py           # Configuration settings
│   ├── models.py           # Pydantic models
│   ├── yolo_detector.py    # YOLO detection + cross-screen tracking
│   ├── video_processor.py  # Multi-stream video processing
│   ├── rag_engine.py       # ChromaDB RAG storage
│   ├── mistral_agent.py    # Mistral AI integration
│   └── train_yolo.py       # Model training script
├── models/                 # Trained YOLO models
└── requirements.txt

drone_detection_frontend/    # React + Vite frontend
├── src/
│   ├── App.jsx             # Main application
│   └── components/
│       ├── VideoGrid.jsx   # 6-camera grid
│       ├── ChatPanel.jsx   # AI chat interface
│       ├── MapPanel.jsx    # Leaflet map
│       ├── MetadataPanel.jsx
│       ├── SettingsModal.jsx
│       └── StatusBar.jsx
├── package.json
└── vite.config.js
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Option 1: Automated Start

```bash
./start.sh
```

This will:
1. Set up Python virtual environment
2. Install all dependencies
3. Start backend on http://localhost:8000
4. Start frontend on http://localhost:3000

### Option 2: Manual Start

**Backend:**
```bash
cd drone_detection_backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend:**
```bash
cd drone_detection_frontend
npm install
npm run dev
```

## Configuration

Edit `drone_detection_backend/.env`:

```env
# Mistral AI (required for chat)
MISTRAL_API_KEY=your_api_key_here

# YOLO settings
YOLO_CONFIDENCE_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45

# Cross-screen tracking
VELOCITY_PREDICTION_ENABLED=true
TRACKING_MEMORY_FRAMES=30
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | System status |
| `/streams` | GET/POST | Manage video streams |
| `/detections` | GET | Current detections |
| `/tracks` | GET | Cross-screen tracks |
| `/map/markers` | GET | Map markers |
| `/chat` | POST | AI chat query |
| `/settings/mistral` | GET/POST | Mistral API config |
| `/ws` | WebSocket | Real-time updates |

## Cross-Screen Tracking

The system predicts object movement across camera gaps:

1. **Velocity Calculation**: Tracks object velocity over time
2. **Exit Prediction**: Determines which edge object will exit
3. **Entry Prediction**: Calculates entry point on adjacent screen
4. **Track Continuity**: Maintains track ID across screens

```
┌─────────┐  ┌─────────┐  ┌─────────┐
│  Cam 1  │  │  Cam 2  │  │  Cam 3  │
│    ●────┼──┼────●────┼──┼────●    │
└─────────┘  └─────────┘  └─────────┘
     Track ID: 42 (predicted path)
```

## Training Custom Model

Generate synthetic data and train:

```bash
./train_model.sh        # Quick training (100 images, 10 epochs)
./train_model.sh --full # Full training (1000 images, 50 epochs)
```

## WebSocket Events

Connect to `ws://localhost:8000/ws` for real-time updates:

```json
{
  "type": "detection_update",
  "timestamp": "2024-01-31T12:00:00Z",
  "frames": {"0": "base64...", "1": "base64..."},
  "detections": [...],
  "map_markers": [...],
  "cross_tracks": [...]
}
```

## Frontend Features

### Glassmorphism UI
- Frosted glass effect with backdrop blur
- Gradient backgrounds
- Smooth animations

### Video Grid
- 2x3 layout with small gaps
- Detection overlays
- Cross-screen prediction indicators
- Click to select/focus stream

### Map Panel
- Dark theme Leaflet map
- Color-coded markers by class
- Track path visualization
- Detection radius circles

### Chat Panel
- Mistral AI integration
- RAG-based context retrieval
- Conversation history
- Suggested queries

## License

Apache 2.0 - See LICENSE file
