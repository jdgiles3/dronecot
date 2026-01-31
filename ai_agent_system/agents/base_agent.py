"""Base agent class with Ollama integration for local LLMs."""

import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import json
import uuid

import sys
sys.path.append('..')
from config import settings


class OllamaClient:
    """Async client for Ollama API."""
    
    def __init__(self, host: str = None):
        self.host = host or settings.OLLAMA_HOST
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Generate a completion."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        
        if system:
            payload["system"] = system
        if context:
            payload["context"] = context
        if options:
            payload["options"] = options
        
        if stream:
            return self._stream_generate(payload)
        
        response = await self.client.post(
            f"{self.host}/api/generate",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def _stream_generate(self, payload: Dict) -> AsyncGenerator[str, None]:
        """Stream generation responses."""
        async with self.client.stream(
            "POST",
            f"{self.host}/api/generate",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        
        if options:
            payload["options"] = options
        
        response = await self.client.post(
            f"{self.host}/api/chat",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def embeddings(
        self,
        model: str,
        prompt: str
    ) -> List[float]:
        """Generate embeddings."""
        response = await self.client.post(
            f"{self.host}/api/embeddings",
            json={"model": model, "prompt": prompt}
        )
        response.raise_for_status()
        return response.json()["embedding"]
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        response = await self.client.get(f"{self.host}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])
    
    async def pull_model(self, model: str) -> bool:
        """Pull a model if not available."""
        try:
            response = await self.client.post(
                f"{self.host}/api/pull",
                json={"name": model},
                timeout=600.0
            )
            return response.status_code == 200
        except Exception:
            return False
    
    async def is_model_available(self, model: str) -> bool:
        """Check if a model is available."""
        models = await self.list_models()
        return any(m["name"].startswith(model.split(":")[0]) for m in models)
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


class AgentMessage:
    """Structured message for agent communication."""
    
    def __init__(
        self,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.role = role
        self.content = content
        self.agent_id = agent_id
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "agent_id": self.agent_id,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    def to_ollama_format(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(
        self,
        agent_id: str,
        model: str,
        system_prompt: str,
        description: str = ""
    ):
        self.agent_id = agent_id
        self.model = model
        self.system_prompt = system_prompt
        self.description = description
        self.ollama = OllamaClient()
        self.conversation_history: List[AgentMessage] = []
        self.context: Optional[List[int]] = None
        self.is_ready = False
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0
        }
    
    async def initialize(self) -> bool:
        """Initialize the agent and ensure model is available."""
        try:
            if not await self.ollama.is_model_available(self.model):
                print(f"Pulling model {self.model}...")
                await self.ollama.pull_model(self.model)
            
            self.is_ready = True
            print(f"Agent {self.agent_id} initialized with model {self.model}")
            return True
        except Exception as e:
            print(f"Agent {self.agent_id} initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the agent."""
        await self.ollama.close()
        self.is_ready = False
    
    def add_to_history(self, message: AgentMessage):
        """Add a message to conversation history."""
        self.conversation_history.append(message)
        # Keep last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
        self.context = None
    
    async def generate(
        self,
        prompt: str,
        use_history: bool = True,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a response."""
        self.stats["total_requests"] += 1
        
        try:
            # Build full prompt with history
            full_prompt = prompt
            if use_history and self.conversation_history:
                history_text = "\n".join([
                    f"{m.role}: {m.content}"
                    for m in self.conversation_history[-5:]
                ])
                full_prompt = f"Previous conversation:\n{history_text}\n\nCurrent request: {prompt}"
            
            response = await self.ollama.generate(
                model=self.model,
                prompt=full_prompt,
                system=self.system_prompt,
                context=self.context,
                options=options or {"temperature": 0.7, "num_predict": 1024}
            )
            
            # Update context for continuity
            if "context" in response:
                self.context = response["context"]
            
            # Track stats
            self.stats["successful_requests"] += 1
            if "eval_count" in response:
                self.stats["total_tokens"] += response["eval_count"]
            
            # Add to history
            self.add_to_history(AgentMessage("user", prompt, self.agent_id))
            self.add_to_history(AgentMessage("assistant", response["response"], self.agent_id))
            
            return response["response"]
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            raise e
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Chat completion with message history."""
        self.stats["total_requests"] += 1
        
        try:
            # Prepend system message
            full_messages = [{"role": "system", "content": self.system_prompt}]
            full_messages.extend(messages)
            
            response = await self.ollama.chat(
                model=self.model,
                messages=full_messages,
                options=options or {"temperature": 0.7}
            )
            
            self.stats["successful_requests"] += 1
            return response["message"]["content"]
            
        except Exception as e:
            self.stats["failed_requests"] += 1
            raise e
    
    async def get_embeddings(self, text: str) -> List[float]:
        """Get embeddings for text."""
        return await self.ollama.embeddings(
            model=settings.EMBEDDING_MODEL,
            prompt=text
        )
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return result. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "model": self.model,
            "is_ready": self.is_ready,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "stats": self.stats,
            "history_length": len(self.conversation_history)
        }
