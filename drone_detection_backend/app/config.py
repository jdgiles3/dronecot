"""Configuration settings for the drone detection backend."""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # YOLO Model
    YOLO_MODEL_PATH: str = "models/drone_yolov8.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.5
    YOLO_IOU_THRESHOLD: float = 0.45
    
    # Video Processing
    MAX_VIDEO_STREAMS: int = 6
    FRAME_SKIP: int = 2
    
    # Cross-screen tracking
    SCREEN_GAP_PIXELS: int = 20
    TRACKING_MEMORY_FRAMES: int = 30
    VELOCITY_PREDICTION_ENABLED: bool = True
    
    # Mistral AI
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = "mistral-small-latest"
    
    # RAG Storage
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Simulated drone coordinates (San Francisco area)
    DEFAULT_LAT: float = 37.7749
    DEFAULT_LON: float = -122.4194
    COORDINATE_VARIANCE: float = 0.01
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
