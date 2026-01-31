"""Redis cache service for session management and hot data."""

import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import hashlib

import redis.asyncio as redis

import sys
sys.path.append('..')
from config import settings


class RedisService:
    """Redis service for caching, sessions, and rate limiting."""
    
    # Key prefixes for organization
    PREFIX_CACHE = "cache:"
    PREFIX_SESSION = "session:"
    PREFIX_RATE = "rate:"
    PREFIX_LOCK = "lock:"
    PREFIX_QUEUE = "queue:"
    PREFIX_AGENT = "agent:"
    PREFIX_ALERT = "alert:"
    
    def __init__(self):
        self.url = settings.REDIS_URL
        self.default_ttl = settings.REDIS_CACHE_TTL
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        self.client = redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True
        )
        await self.client.ping()
        print(f"Redis connected: {self.url}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            print("Redis disconnected")
    
    # ==================== CACHING ====================
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get a cached value."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        value = await self.client.get(full_key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set a cached value."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.client.set(full_key, value, ex=ttl or self.default_ttl)
    
    async def cache_delete(self, key: str):
        """Delete a cached value."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        await self.client.delete(full_key)
    
    async def cache_exists(self, key: str) -> bool:
        """Check if a cache key exists."""
        full_key = f"{self.PREFIX_CACHE}{key}"
        return await self.client.exists(full_key) > 0
    
    def cache_key(self, *args) -> str:
        """Generate a cache key from arguments."""
        key_str = ":".join(str(a) for a in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    # ==================== SESSIONS ====================
    
    async def session_create(
        self,
        session_id: str,
        data: Dict[str, Any],
        ttl: int = 86400
    ):
        """Create a new session."""
        full_key = f"{self.PREFIX_SESSION}{session_id}"
        data["created_at"] = datetime.utcnow().isoformat()
        data["last_activity"] = datetime.utcnow().isoformat()
        await self.client.set(full_key, json.dumps(data), ex=ttl)
    
    async def session_get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        full_key = f"{self.PREFIX_SESSION}{session_id}"
        value = await self.client.get(full_key)
        if value:
            return json.loads(value)
        return None
    
    async def session_update(
        self,
        session_id: str,
        data: Dict[str, Any],
        extend_ttl: bool = True
    ):
        """Update session data."""
        full_key = f"{self.PREFIX_SESSION}{session_id}"
        existing = await self.session_get(session_id)
        if existing:
            existing.update(data)
            existing["last_activity"] = datetime.utcnow().isoformat()
            ttl = await self.client.ttl(full_key) if extend_ttl else None
            await self.client.set(full_key, json.dumps(existing), ex=ttl or 86400)
    
    async def session_delete(self, session_id: str):
        """Delete a session."""
        full_key = f"{self.PREFIX_SESSION}{session_id}"
        await self.client.delete(full_key)
    
    # ==================== RATE LIMITING ====================
    
    async def rate_limit_check(
        self,
        identifier: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """Check rate limit. Returns (allowed, remaining)."""
        full_key = f"{self.PREFIX_RATE}{identifier}"
        
        current = await self.client.get(full_key)
        if current is None:
            await self.client.set(full_key, 1, ex=window_seconds)
            return True, limit - 1
        
        count = int(current)
        if count >= limit:
            return False, 0
        
        await self.client.incr(full_key)
        return True, limit - count - 1
    
    async def rate_limit_reset(self, identifier: str):
        """Reset rate limit for an identifier."""
        full_key = f"{self.PREFIX_RATE}{identifier}"
        await self.client.delete(full_key)
    
    # ==================== DISTRIBUTED LOCKS ====================
    
    async def lock_acquire(
        self,
        lock_name: str,
        ttl: int = 30
    ) -> bool:
        """Acquire a distributed lock."""
        full_key = f"{self.PREFIX_LOCK}{lock_name}"
        return await self.client.set(full_key, "1", nx=True, ex=ttl)
    
    async def lock_release(self, lock_name: str):
        """Release a distributed lock."""
        full_key = f"{self.PREFIX_LOCK}{lock_name}"
        await self.client.delete(full_key)
    
    async def lock_extend(self, lock_name: str, ttl: int = 30) -> bool:
        """Extend a lock's TTL."""
        full_key = f"{self.PREFIX_LOCK}{lock_name}"
        return await self.client.expire(full_key, ttl)
    
    # ==================== QUEUES ====================
    
    async def queue_push(self, queue_name: str, item: Any):
        """Push an item to a queue."""
        full_key = f"{self.PREFIX_QUEUE}{queue_name}"
        if isinstance(item, (dict, list)):
            item = json.dumps(item)
        await self.client.rpush(full_key, item)
    
    async def queue_pop(self, queue_name: str, timeout: int = 0) -> Optional[Any]:
        """Pop an item from a queue (blocking)."""
        full_key = f"{self.PREFIX_QUEUE}{queue_name}"
        if timeout > 0:
            result = await self.client.blpop(full_key, timeout=timeout)
            if result:
                _, value = result
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        else:
            value = await self.client.lpop(full_key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
        return None
    
    async def queue_length(self, queue_name: str) -> int:
        """Get queue length."""
        full_key = f"{self.PREFIX_QUEUE}{queue_name}"
        return await self.client.llen(full_key)
    
    # ==================== AGENT STATE ====================
    
    async def agent_set_state(
        self,
        agent_id: str,
        state: Dict[str, Any]
    ):
        """Set agent state."""
        full_key = f"{self.PREFIX_AGENT}{agent_id}:state"
        state["updated_at"] = datetime.utcnow().isoformat()
        await self.client.set(full_key, json.dumps(state))
    
    async def agent_get_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state."""
        full_key = f"{self.PREFIX_AGENT}{agent_id}:state"
        value = await self.client.get(full_key)
        if value:
            return json.loads(value)
        return None
    
    async def agent_add_history(
        self,
        agent_id: str,
        entry: Dict[str, Any],
        max_entries: int = 100
    ):
        """Add to agent conversation history."""
        full_key = f"{self.PREFIX_AGENT}{agent_id}:history"
        entry["timestamp"] = datetime.utcnow().isoformat()
        await self.client.rpush(full_key, json.dumps(entry))
        await self.client.ltrim(full_key, -max_entries, -1)
    
    async def agent_get_history(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get agent conversation history."""
        full_key = f"{self.PREFIX_AGENT}{agent_id}:history"
        entries = await self.client.lrange(full_key, -limit, -1)
        return [json.loads(e) for e in entries]
    
    # ==================== ALERTS ====================
    
    async def alert_store(
        self,
        alert_id: str,
        alert_data: Dict[str, Any],
        ttl: int = 86400
    ):
        """Store an alert."""
        full_key = f"{self.PREFIX_ALERT}{alert_id}"
        alert_data["stored_at"] = datetime.utcnow().isoformat()
        await self.client.set(full_key, json.dumps(alert_data), ex=ttl)
        
        # Add to active alerts set
        await self.client.sadd(f"{self.PREFIX_ALERT}active", alert_id)
    
    async def alert_get(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get an alert."""
        full_key = f"{self.PREFIX_ALERT}{alert_id}"
        value = await self.client.get(full_key)
        if value:
            return json.loads(value)
        return None
    
    async def alert_acknowledge(self, alert_id: str, user: str):
        """Acknowledge an alert."""
        alert = await self.alert_get(alert_id)
        if alert:
            alert["acknowledged"] = True
            alert["acknowledged_by"] = user
            alert["acknowledged_at"] = datetime.utcnow().isoformat()
            await self.client.set(
                f"{self.PREFIX_ALERT}{alert_id}",
                json.dumps(alert)
            )
            await self.client.srem(f"{self.PREFIX_ALERT}active", alert_id)
    
    async def alert_get_active(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        alert_ids = await self.client.smembers(f"{self.PREFIX_ALERT}active")
        alerts = []
        for aid in alert_ids:
            alert = await self.alert_get(aid)
            if alert:
                alert["id"] = aid
                alerts.append(alert)
        return alerts
    
    # ==================== STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        info = await self.client.info()
        return {
            "connected_clients": info.get("connected_clients"),
            "used_memory": info.get("used_memory_human"),
            "total_keys": await self.client.dbsize(),
            "uptime_seconds": info.get("uptime_in_seconds")
        }
