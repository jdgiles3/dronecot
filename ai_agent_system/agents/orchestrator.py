"""Agent Orchestrator for intelligent task routing and multi-agent coordination."""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import asyncio
import json
import re

from .base_agent import BaseAgent, OllamaClient
from .alert_agent import AlertAgent
from .analysis_agent import AnalysisAgent
from .task_agent import TaskAgent
from .vision_agent import VisionAgent
from .data_agent import DataAgent

import sys
sys.path.append('..')
from config import settings


class AgentOrchestrator:
    """Orchestrates multiple AI agents for complex task execution."""
    
    # Intent classification keywords
    INTENT_KEYWORDS = {
        "alert": ["alert", "warning", "anomaly", "threshold", "monitor", "detect", "notify"],
        "analysis": ["analyze", "pattern", "trend", "insight", "report", "forecast", "compare", "statistics"],
        "task": ["automate", "execute", "browser", "scrape", "click", "fill", "navigate", "code", "script"],
        "vision": ["image", "screenshot", "picture", "visual", "see", "look", "photo", "ocr"],
        "data": ["search", "find", "query", "database", "shift", "log", "retrieve", "sort", "filter", "ingest"]
    }
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.ollama = OllamaClient()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.results_cache: Dict[str, Dict[str, Any]] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.is_running = False
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "requests_by_agent": {},
            "average_response_time": 0,
            "errors": 0
        }
    
    async def initialize(self):
        """Initialize all agents."""
        print("Initializing Agent Orchestrator...")
        
        # Create agents
        self.agents = {
            "alert": AlertAgent(),
            "analysis": AnalysisAgent(),
            "task": TaskAgent(),
            "vision": VisionAgent(),
            "data": DataAgent()
        }
        
        # Initialize each agent
        for name, agent in self.agents.items():
            try:
                success = await agent.initialize()
                if success:
                    print(f"  ✓ {name.title()} Agent initialized")
                else:
                    print(f"  ✗ {name.title()} Agent failed to initialize")
            except Exception as e:
                print(f"  ✗ {name.title()} Agent error: {e}")
        
        self.is_running = True
        print("Agent Orchestrator ready")
    
    async def shutdown(self):
        """Shutdown all agents."""
        self.is_running = False
        
        for agent in self.agents.values():
            await agent.shutdown()
        
        await self.ollama.close()
        print("Agent Orchestrator shutdown complete")
    
    def set_services(self, opensearch_service, redis_service):
        """Set service dependencies for agents that need them."""
        if "data" in self.agents:
            self.agents["data"].set_services(opensearch_service, redis_service)
    
    def _classify_intent(self, message: str) -> Tuple[str, float]:
        """Classify the intent of a message to route to appropriate agent."""
        message_lower = message.lower()
        scores = {}
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            scores[intent] = score
        
        if max(scores.values()) == 0:
            return "analysis", 0.5  # Default to analysis agent
        
        best_intent = max(scores, key=scores.get)
        confidence = scores[best_intent] / len(self.INTENT_KEYWORDS[best_intent])
        
        return best_intent, min(confidence, 1.0)
    
    async def _smart_route(self, message: str, context: Optional[Dict] = None) -> Tuple[str, Dict[str, Any]]:
        """Use LLM to intelligently route the request."""
        prompt = f"""Analyze this user request and determine the best agent to handle it:

Request: "{message}"

Available agents:
1. alert - Anomaly detection, threshold monitoring, alert generation
2. analysis - Pattern recognition, insights, reports, forecasting
3. task - Browser automation, code generation, web scraping
4. vision - Image analysis, OCR, visual understanding
5. data - Database queries, search, shift logs, data management

Respond in JSON format:
{{
    "agent": "agent_name",
    "confidence": 0.0-1.0,
    "action": "specific action for the agent",
    "parameters": {{}},
    "reasoning": "why this agent"
}}"""

        try:
            response = await self.ollama.generate(
                model=settings.DATA_MODEL,  # Use fast model for routing
                prompt=prompt,
                options={"temperature": 0.3, "num_predict": 256}
            )
            
            json_match = re.search(r'\{[\s\S]*\}', response["response"])
            if json_match:
                routing = json.loads(json_match.group())
                return routing.get("agent", "analysis"), routing
        except:
            pass
        
        # Fallback to keyword-based routing
        intent, confidence = self._classify_intent(message)
        return intent, {"agent": intent, "confidence": confidence, "action": "process"}
    
    async def process_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        force_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a user message and route to appropriate agent."""
        start_time = datetime.utcnow()
        self.stats["total_requests"] += 1
        
        # Determine which agent to use
        if force_agent and force_agent in self.agents:
            agent_name = force_agent
            routing = {"agent": force_agent, "confidence": 1.0}
        else:
            agent_name, routing = await self._smart_route(message, context)
        
        # Track stats
        self.stats["requests_by_agent"][agent_name] = \
            self.stats["requests_by_agent"].get(agent_name, 0) + 1
        
        # Get the agent
        agent = self.agents.get(agent_name)
        if not agent:
            return {
                "error": f"Agent '{agent_name}' not found",
                "available_agents": list(self.agents.keys())
            }
        
        # Prepare input for agent
        input_data = {
            "message": message,
            "context": context,
            "routing": routing,
            **(routing.get("parameters", {}))
        }
        
        # Add action if specified
        if "action" in routing:
            input_data["action"] = routing["action"]
        
        # Process with agent
        try:
            # For simple queries, use generate
            if routing.get("action") == "process" or not routing.get("action"):
                response = await agent.generate(message)
                result = {
                    "response": response,
                    "agent": agent_name
                }
            else:
                result = await agent.process(input_data)
                result["agent"] = agent_name
            
            result["routing"] = routing
            result["success"] = True
            
        except Exception as e:
            self.stats["errors"] += 1
            result = {
                "error": str(e),
                "agent": agent_name,
                "success": False
            }
        
        # Calculate response time
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds()
        result["response_time"] = response_time
        result["timestamp"] = end_time.isoformat()
        
        # Update average response time
        total = self.stats["total_requests"]
        avg = self.stats["average_response_time"]
        self.stats["average_response_time"] = (avg * (total - 1) + response_time) / total
        
        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": start_time.isoformat()
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": result.get("response", json.dumps(result)),
            "agent": agent_name,
            "timestamp": end_time.isoformat()
        })
        
        # Keep history manageable
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
        
        return result
    
    async def execute_multi_agent_task(
        self,
        task_description: str,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a task that requires multiple agents."""
        results = []
        context = {"task": task_description}
        
        for i, step in enumerate(steps):
            agent_name = step.get("agent")
            action = step.get("action")
            params = step.get("parameters", {})
            
            # Add previous results to context
            if results:
                context["previous_results"] = results[-1]
            
            agent = self.agents.get(agent_name)
            if not agent:
                results.append({
                    "step": i + 1,
                    "error": f"Agent '{agent_name}' not found"
                })
                continue
            
            try:
                input_data = {
                    "action": action,
                    "context": context,
                    **params
                }
                
                result = await agent.process(input_data)
                result["step"] = i + 1
                result["agent"] = agent_name
                results.append(result)
                
                # Check if step failed and is required
                if not result.get("success", True) and step.get("required", True):
                    break
                    
            except Exception as e:
                results.append({
                    "step": i + 1,
                    "agent": agent_name,
                    "error": str(e)
                })
                if step.get("required", True):
                    break
        
        return {
            "task": task_description,
            "total_steps": len(steps),
            "completed_steps": len(results),
            "results": results,
            "success": all(r.get("success", True) for r in results),
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def get_agent_status(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get status of one or all agents."""
        if agent_name:
            agent = self.agents.get(agent_name)
            if agent:
                return agent.get_status()
            return {"error": f"Agent '{agent_name}' not found"}
        
        return {
            agent_name: agent.get_status()
            for agent_name, agent in self.agents.items()
        }
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all agents."""
        return {
            agent_name: agent.get_capabilities()
            for agent_name, agent in self.agents.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            **self.stats,
            "active_agents": len([a for a in self.agents.values() if a.is_ready]),
            "total_agents": len(self.agents),
            "conversation_length": len(self.conversation_history)
        }
    
    def get_conversation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        return self.conversation_history[-limit:]
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        for agent in self.agents.values():
            agent.clear_history()
