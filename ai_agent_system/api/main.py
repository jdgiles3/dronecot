"""FastAPI main application for multi-agent AI system."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import sys
sys.path.append('..')
from config import settings
from services.kafka_service import KafkaService
from services.redis_service import RedisService
from services.opensearch_service import OpenSearchService
from services.seaweedfs_service import SeaweedFSService
from services.tika_service import TikaService
from services.ingestion_service import IngestionPipeline
from agents.orchestrator import AgentOrchestrator


# Global instances
kafka: Optional[KafkaService] = None
redis: Optional[RedisService] = None
opensearch: Optional[OpenSearchService] = None
seaweedfs: Optional[SeaweedFSService] = None
tika: Optional[TikaService] = None
ingestion: Optional[IngestionPipeline] = None
orchestrator: Optional[AgentOrchestrator] = None

# WebSocket connections
ws_connections: Dict[str, WebSocket] = {}

# Real-time stats
realtime_stats = {
    "messages_processed": 0,
    "active_connections": 0,
    "ingestions_today": 0,
    "alerts_today": 0,
    "events_per_minute": [],
    "last_updated": None
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global kafka, redis, opensearch, seaweedfs, tika, ingestion, orchestrator
    
    print("=" * 60)
    print("  MULTI-AGENT AI SYSTEM - INITIALIZING")
    print("=" * 60)
    
    # Initialize services
    print("\n[1/7] Initializing Kafka...")
    kafka = KafkaService()
    try:
        await kafka.start()
    except Exception as e:
        print(f"  Kafka not available: {e}")
    
    print("[2/7] Initializing Redis...")
    redis = RedisService()
    try:
        await redis.connect()
    except Exception as e:
        print(f"  Redis not available: {e}")
    
    print("[3/7] Initializing OpenSearch...")
    opensearch = OpenSearchService()
    try:
        await opensearch.connect()
    except Exception as e:
        print(f"  OpenSearch not available: {e}")
    
    print("[4/7] Initializing SeaweedFS...")
    seaweedfs = SeaweedFSService()
    try:
        await seaweedfs.connect()
    except Exception as e:
        print(f"  SeaweedFS not available: {e}")
    
    print("[5/7] Initializing Tika...")
    tika = TikaService()
    try:
        await tika.connect()
    except Exception as e:
        print(f"  Tika not available: {e}")
    
    print("[6/7] Initializing Ingestion Pipeline...")
    ingestion = IngestionPipeline(kafka, opensearch, seaweedfs, tika, redis)
    
    print("[7/7] Initializing Agent Orchestrator...")
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize()
    orchestrator.set_services(opensearch, redis)
    
    # Start background tasks
    stats_task = asyncio.create_task(update_realtime_stats())
    broadcast_task = asyncio.create_task(broadcast_updates())
    
    print("\n" + "=" * 60)
    print("  SYSTEM READY")
    print(f"  API: http://localhost:{settings.PORT}")
    print(f"  Docs: http://localhost:{settings.PORT}/docs")
    print("=" * 60 + "\n")
    
    yield
    
    # Cleanup
    print("\nShutting down...")
    stats_task.cancel()
    broadcast_task.cancel()
    
    await orchestrator.shutdown()
    if kafka:
        await kafka.stop()
    if redis:
        await redis.disconnect()
    if opensearch:
        await opensearch.disconnect()
    if seaweedfs:
        await seaweedfs.disconnect()
    if tika:
        await tika.disconnect()
    
    print("Shutdown complete")


app = FastAPI(
    title="Multi-Agent AI System",
    description="Orchestrated small language models with full data pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def update_realtime_stats():
    """Update real-time statistics."""
    while True:
        try:
            realtime_stats["active_connections"] = len(ws_connections)
            realtime_stats["last_updated"] = datetime.utcnow().isoformat()
            
            # Track events per minute
            realtime_stats["events_per_minute"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "count": realtime_stats["messages_processed"]
            })
            
            # Keep last 60 minutes
            if len(realtime_stats["events_per_minute"]) > 60:
                realtime_stats["events_per_minute"] = realtime_stats["events_per_minute"][-60:]
            
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Stats update error: {e}")
            await asyncio.sleep(60)


async def broadcast_updates():
    """Broadcast updates to all WebSocket clients."""
    while True:
        try:
            if ws_connections:
                message = {
                    "type": "stats_update",
                    "timestamp": datetime.utcnow().isoformat(),
                    "stats": realtime_stats,
                    "orchestrator_stats": orchestrator.get_stats() if orchestrator else {},
                    "ingestion_stats": ingestion.get_stats() if ingestion else {}
                }
                
                disconnected = []
                for client_id, ws in ws_connections.items():
                    try:
                        await ws.send_json(message)
                    except:
                        disconnected.append(client_id)
                
                for client_id in disconnected:
                    del ws_connections[client_id]
            
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Broadcast error: {e}")
            await asyncio.sleep(2)


# ==================== PYDANTIC MODELS ====================

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    force_agent: Optional[str] = None


class TaskRequest(BaseModel):
    description: str
    steps: Optional[List[Dict[str, Any]]] = None


class SearchRequest(BaseModel):
    query: str
    index: str = "documents"
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    limit: int = 10


class ShiftLogRequest(BaseModel):
    operator: str
    summary: str
    activities: List[Dict[str, Any]] = []
    handoff_notes: Optional[str] = None


class IngestDataRequest(BaseModel):
    data: Dict[str, Any]
    data_type: str = "generic"
    source: str = "api"
    tags: Optional[List[str]] = None


class AlertRequest(BaseModel):
    alert_type: str
    severity: str = "MEDIUM"
    data: Dict[str, Any] = {}


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Multi-Agent AI System",
        "version": "1.0.0",
        "status": "running",
        "agents": list(orchestrator.agents.keys()) if orchestrator else []
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "kafka": kafka is not None,
            "redis": redis is not None,
            "opensearch": opensearch is not None,
            "seaweedfs": seaweedfs is not None,
            "tika": tika is not None,
            "orchestrator": orchestrator is not None and orchestrator.is_running
        }
    }


@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    return {
        "realtime": realtime_stats,
        "orchestrator": orchestrator.get_stats() if orchestrator else {},
        "ingestion": ingestion.get_stats() if ingestion else {},
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== CHAT ENDPOINTS ====================

@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a message to the AI agent system."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    realtime_stats["messages_processed"] += 1
    
    result = await orchestrator.process_message(
        message=request.message,
        context=request.context,
        force_agent=request.force_agent
    )
    
    # Broadcast to WebSocket clients
    await broadcast_chat_message(request.message, result)
    
    return result


@app.get("/chat/history")
async def get_chat_history(limit: int = 50):
    """Get conversation history."""
    if not orchestrator:
        return []
    return orchestrator.get_conversation_history(limit)


@app.delete("/chat/history")
async def clear_chat_history():
    """Clear conversation history."""
    if orchestrator:
        orchestrator.clear_conversation()
    return {"message": "History cleared"}


async def broadcast_chat_message(user_message: str, result: Dict[str, Any]):
    """Broadcast chat message to WebSocket clients."""
    message = {
        "type": "chat_message",
        "user_message": user_message,
        "result": result,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    for ws in ws_connections.values():
        try:
            await ws.send_json(message)
        except:
            pass


# ==================== AGENT ENDPOINTS ====================

@app.get("/agents")
async def get_agents():
    """Get all agents and their status."""
    if not orchestrator:
        return {}
    return await orchestrator.get_agent_status()


@app.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    """Get specific agent status."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    return await orchestrator.get_agent_status(agent_name)


@app.get("/agents/capabilities")
async def get_capabilities():
    """Get all agent capabilities."""
    if not orchestrator:
        return {}
    return orchestrator.get_capabilities()


# ==================== TASK ENDPOINTS ====================

@app.post("/tasks")
async def create_task(request: TaskRequest):
    """Create and execute a task."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    if request.steps:
        result = await orchestrator.execute_multi_agent_task(
            request.description,
            request.steps
        )
    else:
        result = await orchestrator.process_message(
            message=request.description,
            force_agent="task"
        )
    
    return result


# ==================== SEARCH ENDPOINTS ====================

@app.post("/search")
async def search(request: SearchRequest):
    """Search indexed data."""
    if not opensearch:
        raise HTTPException(status_code=503, detail="OpenSearch not available")
    
    result = await opensearch.full_text_search(
        index=request.index,
        query_text=request.query,
        fields=["*"],
        size=request.limit,
        filters=request.filters
    )
    
    return result


@app.get("/search/recent")
async def get_recent(
    index: str = "events",
    hours: int = 24,
    limit: int = 100
):
    """Get recent items from an index."""
    if not opensearch:
        raise HTTPException(status_code=503, detail="OpenSearch not available")
    
    return await opensearch.get_recent_events(
        event_type=None,
        source=None,
        hours=hours,
        limit=limit
    )


# ==================== ALERT ENDPOINTS ====================

@app.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50
):
    """Get alerts."""
    if not opensearch:
        raise HTTPException(status_code=503, detail="OpenSearch not available")
    
    return await opensearch.get_alerts(severity, acknowledged, limit)


@app.post("/alerts")
async def create_alert(request: AlertRequest):
    """Create an alert."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    result = await orchestrator.process_message(
        message=f"Generate alert: {request.alert_type}",
        context={"data": request.data, "severity": request.severity},
        force_agent="alert"
    )
    
    realtime_stats["alerts_today"] += 1
    
    return result


@app.get("/alerts/active")
async def get_active_alerts():
    """Get active (unacknowledged) alerts."""
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    return await redis.alert_get_active()


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: str = "system"):
    """Acknowledge an alert."""
    if not redis:
        raise HTTPException(status_code=503, detail="Redis not available")
    
    await redis.alert_acknowledge(alert_id, user)
    return {"message": "Alert acknowledged", "alert_id": alert_id}


# ==================== SHIFT LOG ENDPOINTS ====================

@app.get("/shift-logs")
async def get_shift_logs(
    operator: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get shift logs."""
    if not opensearch:
        raise HTTPException(status_code=503, detail="OpenSearch not available")
    
    return await opensearch.get_shift_logs(operator, status, limit=limit)


@app.post("/shift-logs")
async def create_shift_log(request: ShiftLogRequest):
    """Create a new shift log."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    result = await orchestrator.agents["data"].create_shift_log(
        operator=request.operator,
        summary=request.summary,
        activities=request.activities,
        handoff_notes=request.handoff_notes
    )
    
    return result


@app.post("/shift-logs/{shift_id}/end")
async def end_shift_log(
    shift_id: str,
    final_summary: str = "",
    handoff_notes: str = ""
):
    """End a shift log."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not available")
    
    return await orchestrator.agents["data"].end_shift_log(
        shift_id, final_summary, handoff_notes
    )


# ==================== INGESTION ENDPOINTS ====================

@app.post("/ingest/data")
async def ingest_data(request: IngestDataRequest):
    """Ingest structured data."""
    if not ingestion:
        raise HTTPException(status_code=503, detail="Ingestion not available")
    
    result = await ingestion.ingest_data(
        data=request.data,
        data_type=request.data_type,
        source=request.source,
        tags=request.tags
    )
    
    realtime_stats["ingestions_today"] += 1
    
    return result


@app.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    source: str = Form("upload"),
    tags: str = Form("")
):
    """Ingest a file."""
    if not ingestion:
        raise HTTPException(status_code=503, detail="Ingestion not available")
    
    content = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    result = await ingestion.ingest_file(
        file_content=content,
        filename=file.filename,
        source=source,
        tags=tag_list
    )
    
    realtime_stats["ingestions_today"] += 1
    
    return result


@app.get("/ingest/stats")
async def get_ingestion_stats():
    """Get ingestion statistics."""
    if not ingestion:
        return {}
    return ingestion.get_stats()


# ==================== WEBSOCKET ENDPOINT ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    client_id = str(uuid.uuid4())
    ws_connections[client_id] = websocket
    
    realtime_stats["active_connections"] = len(ws_connections)
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "stats": realtime_stats,
            "agents": list(orchestrator.agents.keys()) if orchestrator else []
        })
        
        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif data.get("type") == "chat":
                    if orchestrator:
                        result = await orchestrator.process_message(
                            message=data.get("message", ""),
                            context=data.get("context")
                        )
                        await websocket.send_json({
                            "type": "chat_response",
                            "result": result
                        })
                        
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    finally:
        if client_id in ws_connections:
            del ws_connections[client_id]
        realtime_stats["active_connections"] = len(ws_connections)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
