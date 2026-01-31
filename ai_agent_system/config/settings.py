"""Configuration settings for the multi-agent AI system."""

import os
from typing import Optional, List, Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    DEBUG: bool = True
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:29092"
    KAFKA_TOPICS: Dict[str, str] = {
        "alerts": "ai-alerts",
        "tasks": "ai-tasks",
        "ingest": "ai-ingest",
        "results": "ai-results",
        "logs": "ai-logs",
        "events": "ai-events"
    }
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600
    
    # OpenSearch
    OPENSEARCH_HOSTS: List[str] = ["http://localhost:9200"]
    OPENSEARCH_INDEX_PREFIX: str = "ai-agent"
    
    # SeaweedFS
    SEAWEEDFS_MASTER: str = "http://localhost:9333"
    SEAWEEDFS_FILER: str = "http://localhost:8888"
    
    # Tika
    TIKA_SERVER: str = "http://localhost:9998"
    
    # Ollama (Local LLMs)
    OLLAMA_HOST: str = "http://localhost:11434"
    
    # Agent Models
    ALERT_MODEL: str = "phi3:mini"
    ANALYSIS_MODEL: str = "mistral:7b"
    TASK_MODEL: str = "codellama:7b"
    VISION_MODEL: str = "llava:7b"
    DATA_MODEL: str = "tinyllama:latest"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # External APIs (optional)
    OPENAI_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    
    # Alert Thresholds
    ALERT_ANOMALY_THRESHOLD: float = 0.8
    ALERT_CHECK_INTERVAL: int = 60
    
    # Task Execution
    PLAYWRIGHT_HEADLESS: bool = True
    TASK_TIMEOUT: int = 300
    
    # Data Retention
    LOG_RETENTION_DAYS: int = 30
    CACHE_MAX_SIZE: int = 10000
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
