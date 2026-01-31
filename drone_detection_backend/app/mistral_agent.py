"""Mistral AI agent for RAG-based query answering."""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from .config import settings
from .models import ChatMessage, RAGResponse


class MistralAgent:
    """Mistral AI agent for answering queries about drone detections."""
    
    SYSTEM_PROMPT = """You are an AI assistant specialized in drone detection and surveillance analysis. 
You have access to a database of drone detection events from a multi-camera surveillance system.

Your capabilities:
- Analyze detection patterns and trends
- Provide insights about detected objects (drones, aircraft, birds, etc.)
- Answer questions about specific detection events
- Help interpret tracking data across multiple camera feeds
- Explain cross-screen tracking predictions

When answering:
- Be concise and technical
- Reference specific detection events when relevant
- Provide coordinates and timestamps when available
- Explain confidence levels and tracking IDs
- Note any cross-screen tracking patterns

If you don't have enough information to answer a question, say so clearly."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.MISTRAL_API_KEY
        self.model = settings.MISTRAL_MODEL
        self.base_url = "https://api.mistral.ai/v1"
        self.conversation_history: List[ChatMessage] = []
        self._connected = False
        
        if self.api_key:
            self._test_connection()
    
    def _test_connection(self):
        """Test connection to Mistral API."""
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )
                self._connected = response.status_code == 200
        except Exception:
            self._connected = False
    
    def set_api_key(self, api_key: str):
        """Set or update the API key."""
        self.api_key = api_key
        self._test_connection()
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Mistral API."""
        return self._connected and self.api_key is not None
    
    async def query(
        self,
        user_query: str,
        context: str,
        include_history: bool = True
    ) -> RAGResponse:
        """Query the Mistral agent with RAG context."""
        if not self.api_key:
            return RAGResponse(
                answer="Mistral API key not configured. Please add your API key in settings.",
                sources=[],
                confidence=0.0
            )
        
        # Build messages
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        
        # Add conversation history if requested
        if include_history:
            for msg in self.conversation_history[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add context and user query
        augmented_query = f"""Context from detection database:
{context}

User question: {user_query}

Please answer based on the provided context. If the context doesn't contain relevant information, say so."""
        
        messages.append({"role": "user", "content": augmented_query})
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1000
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    return RAGResponse(
                        answer=f"API error: {response.status_code} - {response.text}",
                        sources=[],
                        confidence=0.0
                    )
                
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                
                # Store in history
                self.conversation_history.append(ChatMessage(
                    role="user",
                    content=user_query
                ))
                self.conversation_history.append(ChatMessage(
                    role="assistant",
                    content=answer
                ))
                
                return RAGResponse(
                    answer=answer,
                    sources=[{"context": context}],
                    confidence=0.85  # Estimated confidence
                )
                
        except httpx.TimeoutException:
            return RAGResponse(
                answer="Request timed out. Please try again.",
                sources=[],
                confidence=0.0
            )
        except Exception as e:
            return RAGResponse(
                answer=f"Error: {str(e)}",
                sources=[],
                confidence=0.0
            )
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in self.conversation_history
        ]


class CrossScreenAnalyzer:
    """AI-assisted cross-screen tracking analysis."""
    
    def __init__(self, mistral_agent: MistralAgent):
        self.agent = mistral_agent
    
    async def analyze_track(
        self,
        track_data: Dict[str, Any],
        detection_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a cross-screen track using AI."""
        if not self.agent.is_connected:
            return self._rule_based_analysis(track_data)
        
        # Format track data for AI
        context = f"""Track Analysis Request:
Track ID: {track_data.get('track_id')}
Current Screen: {track_data.get('current_screen')}
Screens Crossed: {track_data.get('total_screens_crossed', 0)}
Velocity: {track_data.get('velocity_vector', {})}
Predicted Next Screens: {track_data.get('predicted_screens', [])}

Recent Detection History:
"""
        for det in detection_history[-5:]:
            context += f"- {det.get('timestamp')}: Screen {det.get('stream_id')}, Class: {det.get('class_name')}\n"
        
        query = "Analyze this track and predict its likely behavior. Is it following a pattern? Where might it go next?"
        
        response = await self.agent.query(query, context, include_history=False)
        
        return {
            "track_id": track_data.get("track_id"),
            "ai_analysis": response.answer,
            "confidence": response.confidence,
            "rule_based": self._rule_based_analysis(track_data)
        }
    
    def _rule_based_analysis(self, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based analysis when AI is unavailable."""
        velocity = track_data.get("velocity_vector", {})
        vx = velocity.get("vx", 0)
        vy = velocity.get("vy", 0)
        
        # Determine movement direction
        direction = "stationary"
        if abs(vx) > 5 or abs(vy) > 5:
            if abs(vx) > abs(vy):
                direction = "right" if vx > 0 else "left"
            else:
                direction = "down" if vy > 0 else "up"
        
        # Estimate behavior
        screens_crossed = track_data.get("total_screens_crossed", 0)
        behavior = "new_detection"
        if screens_crossed > 2:
            behavior = "traversing_area"
        elif screens_crossed > 0:
            behavior = "moving_between_zones"
        
        return {
            "direction": direction,
            "behavior": behavior,
            "speed": (vx**2 + vy**2)**0.5,
            "predicted_screens": track_data.get("predicted_screens", [])
        }
