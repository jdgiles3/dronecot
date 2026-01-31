"""FastAPI main application for drone detection backend."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import settings
from .models import (
    StreamConfig, Detection, MapMarker, RAGQuery, RAGResponse,
    DetectionEvent, SystemStatus, CrossScreenTrack
)
from .yolo_detector import DroneDetector
from .video_processor import MultiStreamProcessor
from .rag_engine import RAGEngine
from .mistral_agent import MistralAgent, CrossScreenAnalyzer


# Global instances
detector: Optional[DroneDetector] = None
processor: Optional[MultiStreamProcessor] = None
rag_engine: Optional[RAGEngine] = None
mistral_agent: Optional[MistralAgent] = None
cross_analyzer: Optional[CrossScreenAnalyzer] = None

# WebSocket connections
active_connections: Dict[str, WebSocket] = {}

# Detection event buffer for RAG
detection_buffer: List[DetectionEvent] = []
BUFFER_FLUSH_SIZE = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global detector, processor, rag_engine, mistral_agent, cross_analyzer
    
    print("Initializing drone detection system...")
    
    # Initialize components
    detector = DroneDetector()
    processor = MultiStreamProcessor(detector)
    rag_engine = RAGEngine()
    mistral_agent = MistralAgent()
    cross_analyzer = CrossScreenAnalyzer(mistral_agent)
    
    # Initialize simulated streams
    processor.initialize_simulated_streams()
    
    # Start processing task
    processing_task = asyncio.create_task(processor.process_streams())
    broadcast_task = asyncio.create_task(broadcast_detections())
    
    print("System initialized successfully")
    
    yield
    
    # Cleanup
    print("Shutting down...")
    processor.stop()
    processing_task.cancel()
    broadcast_task.cancel()


app = FastAPI(
    title="Drone Detection API",
    description="YOLO-based drone detection with cross-screen tracking and RAG query",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_detections():
    """Broadcast detection updates to all connected WebSocket clients."""
    global detection_buffer
    
    while True:
        await asyncio.sleep(0.1)  # 10 FPS update rate
        
        if not processor or not active_connections:
            continue
        
        # Gather all current data
        frames_data = {}
        all_detections = []
        map_markers = []
        
        for stream_id in range(6):
            frame_b64 = processor.get_frame_base64(stream_id)
            if frame_b64:
                frames_data[stream_id] = frame_b64
            
            detections = processor.latest_detections.get(stream_id, [])
            all_detections.extend(detections)
            
            # Create map markers
            for det in detections:
                if det.latitude and det.longitude:
                    marker = MapMarker(
                        id=det.id,
                        latitude=det.latitude,
                        longitude=det.longitude,
                        label=f"{det.bounding_box.class_name} (ID: {det.bounding_box.track_id})",
                        detection_class=det.bounding_box.class_name,
                        confidence=det.bounding_box.confidence,
                        track_id=det.bounding_box.track_id,
                        timestamp=det.timestamp,
                        metadata={
                            "stream_id": det.stream_id,
                            "velocity": det.velocity,
                            "predicted_next_screen": det.predicted_next_screen
                        }
                    )
                    map_markers.append(marker)
        
        # Get cross-screen tracks
        cross_tracks = detector.get_cross_screen_tracks() if detector else []
        
        # Store detections for RAG
        for det in all_detections:
            event = DetectionEvent(
                id=det.id,
                timestamp=det.timestamp,
                stream_id=det.stream_id,
                detection_class=det.bounding_box.class_name,
                confidence=det.bounding_box.confidence,
                latitude=det.latitude,
                longitude=det.longitude,
                description=f"Detected {det.bounding_box.class_name} on stream {det.stream_id}",
                raw_metadata={
                    "track_id": det.bounding_box.track_id,
                    "velocity": det.velocity,
                    "predicted_next_screen": det.predicted_next_screen
                }
            )
            detection_buffer.append(event)
        
        # Flush buffer to RAG
        if len(detection_buffer) >= BUFFER_FLUSH_SIZE and rag_engine:
            rag_engine.add_events_batch(detection_buffer[:BUFFER_FLUSH_SIZE])
            detection_buffer = detection_buffer[BUFFER_FLUSH_SIZE:]
        
        # Prepare broadcast message
        message = {
            "type": "detection_update",
            "timestamp": datetime.utcnow().isoformat(),
            "frames": frames_data,
            "detections": [det.model_dump() for det in all_detections],
            "map_markers": [m.model_dump() for m in map_markers],
            "cross_tracks": [
                {
                    "track_id": t.track_id,
                    "current_screen": t.current_screen,
                    "predicted_screens": t.predicted_screens,
                    "velocity": t.velocity_vector,
                    "screens_crossed": t.total_screens_crossed
                }
                for t in cross_tracks
            ]
        }
        
        # Broadcast to all clients
        disconnected = []
        for client_id, ws in active_connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(client_id)
        
        # Remove disconnected clients
        for client_id in disconnected:
            del active_connections[client_id]


# REST API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Drone Detection API", "version": "1.0.0"}


@app.get("/status", response_model=SystemStatus)
async def get_status():
    """Get system status."""
    return SystemStatus(
        active_streams=len(processor.streams) if processor else 0,
        total_detections=detector.detection_count if detector else 0,
        active_tracks=len(detector.tracker.tracks) if detector else 0,
        model_loaded=detector.is_loaded if detector else False,
        mistral_connected=mistral_agent.is_connected if mistral_agent else False,
        rag_documents=rag_engine.collection.count() if rag_engine else 0
    )


@app.get("/streams")
async def get_streams():
    """Get all stream configurations."""
    if not processor:
        return []
    
    return [
        {
            "stream_id": s.config.stream_id,
            "name": s.config.name,
            "source": s.config.source,
            "active": s.config.active,
            "position": s.config.position
        }
        for s in processor.streams.values()
    ]


@app.post("/streams")
async def add_stream(config: StreamConfig):
    """Add a new video stream."""
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    success = processor.add_stream(config)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add stream")
    
    return {"message": "Stream added", "stream_id": config.stream_id}


@app.delete("/streams/{stream_id}")
async def remove_stream(stream_id: int):
    """Remove a video stream."""
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    processor.remove_stream(stream_id)
    return {"message": "Stream removed", "stream_id": stream_id}


@app.get("/detections")
async def get_detections():
    """Get current detections from all streams."""
    if not processor:
        return []
    
    return [det.model_dump() for det in processor.get_all_detections()]


@app.get("/tracks")
async def get_tracks():
    """Get all active cross-screen tracks."""
    if not detector:
        return []
    
    tracks = detector.get_cross_screen_tracks()
    return [
        {
            "track_id": t.track_id,
            "current_screen": t.current_screen,
            "predicted_screens": t.predicted_screens,
            "velocity": t.velocity_vector,
            "screens_crossed": t.total_screens_crossed,
            "last_seen": t.last_seen.isoformat(),
            "detection_count": len(t.detections)
        }
        for t in tracks
    ]


@app.get("/map/markers")
async def get_map_markers():
    """Get all map markers for Leaflet."""
    if not processor:
        return []
    
    markers = []
    for stream_id, detections in processor.latest_detections.items():
        for det in detections:
            if det.latitude and det.longitude:
                markers.append({
                    "id": det.id,
                    "lat": det.latitude,
                    "lng": det.longitude,
                    "label": f"{det.bounding_box.class_name}",
                    "track_id": det.bounding_box.track_id,
                    "confidence": det.bounding_box.confidence,
                    "stream_id": stream_id
                })
    
    return markers


# RAG and Chat Endpoints

class ChatRequest(BaseModel):
    message: str
    include_history: bool = True


@app.post("/chat")
async def chat(request: ChatRequest):
    """Chat with the AI agent about detections."""
    if not rag_engine or not mistral_agent:
        raise HTTPException(status_code=500, detail="RAG or Mistral not initialized")
    
    # Get relevant context from RAG
    context = rag_engine.get_context_for_query(request.message)
    
    # Query Mistral
    response = await mistral_agent.query(
        request.message,
        context,
        include_history=request.include_history
    )
    
    return {
        "answer": response.answer,
        "confidence": response.confidence,
        "sources": response.sources
    }


@app.get("/chat/history")
async def get_chat_history():
    """Get chat history."""
    if not mistral_agent:
        return []
    
    return mistral_agent.get_history()


@app.delete("/chat/history")
async def clear_chat_history():
    """Clear chat history."""
    if mistral_agent:
        mistral_agent.clear_history()
    return {"message": "History cleared"}


@app.get("/rag/stats")
async def get_rag_stats():
    """Get RAG engine statistics."""
    if not rag_engine:
        return {}
    
    return rag_engine.get_stats()


@app.get("/rag/recent")
async def get_recent_events(limit: int = 10):
    """Get recent detection events from RAG."""
    if not rag_engine:
        return []
    
    return rag_engine.get_recent_events(limit)


# Settings Endpoints

class MistralSettings(BaseModel):
    api_key: str


@app.post("/settings/mistral")
async def update_mistral_settings(settings_data: MistralSettings):
    """Update Mistral API key."""
    if not mistral_agent:
        raise HTTPException(status_code=500, detail="Mistral agent not initialized")
    
    mistral_agent.set_api_key(settings_data.api_key)
    
    return {
        "message": "API key updated",
        "connected": mistral_agent.is_connected
    }


@app.get("/settings/mistral")
async def get_mistral_settings():
    """Get Mistral connection status."""
    return {
        "connected": mistral_agent.is_connected if mistral_agent else False,
        "model": settings.MISTRAL_MODEL
    }


# WebSocket Endpoint

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "message": "Connected to drone detection stream"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                # Handle client messages
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif data.get("type") == "chat":
                    # Handle chat through WebSocket
                    if rag_engine and mistral_agent:
                        context = rag_engine.get_context_for_query(data.get("message", ""))
                        response = await mistral_agent.query(
                            data.get("message", ""),
                            context
                        )
                        await websocket.send_json({
                            "type": "chat_response",
                            "answer": response.answer,
                            "confidence": response.confidence
                        })
                        
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    finally:
        if client_id in active_connections:
            del active_connections[client_id]


# Video Upload Endpoint

@app.post("/upload/video")
async def upload_video(
    file: UploadFile = File(...),
    stream_id: int = Form(...)
):
    """Upload a video file for processing."""
    if not processor:
        raise HTTPException(status_code=500, detail="Processor not initialized")
    
    # Save uploaded file
    import tempfile
    import os
    
    suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    # Create stream config
    config = StreamConfig(
        stream_id=stream_id,
        source=tmp_path,
        name=f"Uploaded: {file.filename}",
        position={"row": stream_id // 3, "col": stream_id % 3},
        active=True
    )
    
    success = processor.add_stream(config)
    if not success:
        os.unlink(tmp_path)
        raise HTTPException(status_code=400, detail="Failed to process video")
    
    return {
        "message": "Video uploaded and processing",
        "stream_id": stream_id,
        "filename": file.filename
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
