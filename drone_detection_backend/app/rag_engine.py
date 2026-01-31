"""RAG engine for detection event storage and querying."""

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid
import os

from .config import settings
from .models import DetectionEvent, RAGQuery, RAGResponse


class RAGEngine:
    """RAG engine for storing and querying detection events."""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
        
        # Initialize ChromaDB with persistent storage
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(path=persist_dir)
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="detection_events",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.event_count = 0
    
    def _create_document(self, event: DetectionEvent) -> str:
        """Create a searchable document from detection event."""
        doc_parts = [
            f"Detection event at {event.timestamp.isoformat()}",
            f"Stream {event.stream_id}",
            f"Detected: {event.detection_class}",
            f"Confidence: {event.confidence:.2%}",
            event.description
        ]
        
        if event.latitude and event.longitude:
            doc_parts.append(f"Location: {event.latitude:.6f}, {event.longitude:.6f}")
        
        # Add metadata as searchable text
        for key, value in event.raw_metadata.items():
            if isinstance(value, (str, int, float)):
                doc_parts.append(f"{key}: {value}")
        
        return " | ".join(doc_parts)
    
    def add_event(self, event: DetectionEvent):
        """Add a detection event to the RAG store."""
        document = self._create_document(event)
        embedding = self.embedding_model.encode(document).tolist()
        
        metadata = {
            "timestamp": event.timestamp.isoformat(),
            "stream_id": event.stream_id,
            "detection_class": event.detection_class,
            "confidence": event.confidence,
            "latitude": event.latitude or 0,
            "longitude": event.longitude or 0,
        }
        
        self.collection.add(
            ids=[event.id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )
        
        self.event_count += 1
    
    def add_events_batch(self, events: List[DetectionEvent]):
        """Add multiple events in batch."""
        if not events:
            return
        
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for event in events:
            document = self._create_document(event)
            embedding = self.embedding_model.encode(document).tolist()
            
            ids.append(event.id)
            embeddings.append(embedding)
            documents.append(document)
            metadatas.append({
                "timestamp": event.timestamp.isoformat(),
                "stream_id": event.stream_id,
                "detection_class": event.detection_class,
                "confidence": event.confidence,
                "latitude": event.latitude or 0,
                "longitude": event.longitude or 0,
            })
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        self.event_count += len(events)
    
    def query(self, query: RAGQuery) -> List[Dict[str, Any]]:
        """Query the RAG store for relevant events."""
        query_embedding = self.embedding_model.encode(query.query).tolist()
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=query.context_limit,
            include=["documents", "metadatas", "distances"]
        )
        
        sources = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                sources.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0
                })
        
        return sources
    
    def get_context_for_query(self, query: str, limit: int = 5) -> str:
        """Get formatted context string for AI query."""
        rag_query = RAGQuery(query=query, context_limit=limit)
        sources = self.query(rag_query)
        
        if not sources:
            return "No relevant detection events found in the database."
        
        context_parts = ["Relevant detection events:"]
        for i, source in enumerate(sources, 1):
            context_parts.append(f"\n{i}. {source['document']}")
        
        return "\n".join(context_parts)
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent events."""
        # ChromaDB doesn't support sorting, so we get all and sort
        results = self.collection.get(
            include=["documents", "metadatas"]
        )
        
        events = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                events.append({
                    "id": results["ids"][i],
                    "document": doc,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
        
        # Sort by timestamp descending
        events.sort(
            key=lambda x: x["metadata"].get("timestamp", ""),
            reverse=True
        )
        
        return events[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG store statistics."""
        return {
            "total_documents": self.collection.count(),
            "embedding_model": settings.EMBEDDING_MODEL,
            "persist_directory": settings.CHROMA_PERSIST_DIR
        }
    
    def clear(self):
        """Clear all events from the store."""
        # Delete and recreate collection
        try:
            self.chroma_client.delete_collection("detection_events")
        except Exception:
            pass
        self.collection = self.chroma_client.get_or_create_collection(
            name="detection_events",
            metadata={"hnsw:space": "cosine"}
        )
        self.event_count = 0
