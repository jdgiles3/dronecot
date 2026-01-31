"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DetectionClass(str, Enum):
    """Object detection classes."""
    DRONE = "drone"
    PERSON = "person"
    VEHICLE = "vehicle"
    AIRCRAFT = "aircraft"
    BIRD = "bird"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str
    track_id: Optional[int] = None


class Detection(BaseModel):
    """Single detection result."""
    id: str
    timestamp: datetime
    stream_id: int
    bounding_box: BoundingBox
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    velocity: Optional[Dict[str, float]] = None
    predicted_next_screen: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StreamConfig(BaseModel):
    """Video stream configuration."""
    stream_id: int
    source: str  # URL, file path, or "webcam"
    name: str
    position: Dict[str, int]  # row, col in grid
    active: bool = True


class CrossScreenTrack(BaseModel):
    """Track that spans multiple screens."""
    track_id: int
    detections: List[Detection]
    current_screen: int
    predicted_screens: List[int]
    velocity_vector: Dict[str, float]
    last_seen: datetime
    total_screens_crossed: int = 0


class MapMarker(BaseModel):
    """Marker for Leaflet map."""
    id: str
    latitude: float
    longitude: float
    label: str
    detection_class: str
    confidence: float
    track_id: Optional[int] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    """Chat message for RAG query."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RAGQuery(BaseModel):
    """RAG query request."""
    query: str
    context_limit: int = 5


class RAGResponse(BaseModel):
    """RAG query response."""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float


class DetectionEvent(BaseModel):
    """Detection event for storage and RAG."""
    id: str
    timestamp: datetime
    stream_id: int
    detection_class: str
    confidence: float
    latitude: Optional[float]
    longitude: Optional[float]
    description: str
    raw_metadata: Dict[str, Any]


class SystemStatus(BaseModel):
    """System status response."""
    active_streams: int
    total_detections: int
    active_tracks: int
    model_loaded: bool
    mistral_connected: bool
    rag_documents: int
