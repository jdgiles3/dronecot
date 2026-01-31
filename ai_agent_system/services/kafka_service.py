"""Kafka message broker service for async communication."""

import json
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
import uuid

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

import sys
sys.path.append('..')
from config import settings


class KafkaMessage:
    """Structured Kafka message with full metadata."""
    
    def __init__(
        self,
        topic: str,
        payload: Dict[str, Any],
        message_type: str,
        source: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = str(uuid.uuid4())
        self.topic = topic
        self.payload = payload
        self.message_type = message_type
        self.source = source
        self.tags = tags or []
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.version = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "type": self.message_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "version": self.version,
            "tags": self.tags,
            "metadata": self.metadata,
            "payload": self.payload
        }
    
    def to_json(self) -> bytes:
        return json.dumps(self.to_dict()).encode('utf-8')
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaMessage':
        msg = cls(
            topic=data.get("topic", ""),
            payload=data.get("payload", {}),
            message_type=data.get("type", "unknown"),
            source=data.get("source", "unknown"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class KafkaService:
    """Kafka service for message production and consumption."""
    
    def __init__(self):
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.topics = settings.KAFKA_TOPICS
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumers: Dict[str, AIOKafkaConsumer] = {}
        self.handlers: Dict[str, List[Callable]] = {}
        self._running = False
    
    async def start(self):
        """Start the Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        await self.producer.start()
        self._running = True
        print(f"Kafka producer started: {self.bootstrap_servers}")
    
    async def stop(self):
        """Stop all Kafka connections."""
        self._running = False
        
        if self.producer:
            await self.producer.stop()
        
        for consumer in self.consumers.values():
            await consumer.stop()
        
        print("Kafka service stopped")
    
    async def publish(
        self,
        topic_key: str,
        payload: Dict[str, Any],
        message_type: str,
        source: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        key: Optional[str] = None
    ) -> str:
        """Publish a message to a Kafka topic."""
        if not self.producer:
            raise RuntimeError("Kafka producer not started")
        
        topic = self.topics.get(topic_key, topic_key)
        
        message = KafkaMessage(
            topic=topic,
            payload=payload,
            message_type=message_type,
            source=source,
            tags=tags,
            metadata=metadata
        )
        
        try:
            await self.producer.send_and_wait(
                topic,
                value=message.to_dict(),
                key=key or message.id
            )
            return message.id
        except KafkaError as e:
            print(f"Kafka publish error: {e}")
            raise
    
    async def publish_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """Publish an alert message."""
        return await self.publish(
            topic_key="alerts",
            payload={
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "data": data or {}
            },
            message_type="alert",
            source=source,
            tags=tags or [alert_type, severity],
            metadata={"severity": severity}
        )
    
    async def publish_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        source: str,
        priority: int = 5,
        tags: Optional[List[str]] = None
    ) -> str:
        """Publish a task for execution."""
        return await self.publish(
            topic_key="tasks",
            payload={
                "task_type": task_type,
                "priority": priority,
                "data": task_data,
                "status": "pending"
            },
            message_type="task",
            source=source,
            tags=tags or [task_type],
            metadata={"priority": priority}
        )
    
    async def publish_ingest(
        self,
        data_type: str,
        content: Any,
        source: str,
        file_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publish data for ingestion."""
        return await self.publish(
            topic_key="ingest",
            payload={
                "data_type": data_type,
                "content": content,
                "file_path": file_path
            },
            message_type="ingest",
            source=source,
            tags=tags or [data_type],
            metadata=metadata
        )
    
    async def publish_log(
        self,
        log_level: str,
        message: str,
        source: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Publish a log entry."""
        return await self.publish(
            topic_key="logs",
            payload={
                "level": log_level,
                "message": message,
                "context": context or {}
            },
            message_type="log",
            source=source,
            tags=[log_level],
            metadata={"level": log_level}
        )
    
    def register_handler(self, topic_key: str, handler: Callable):
        """Register a message handler for a topic."""
        topic = self.topics.get(topic_key, topic_key)
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)
    
    async def start_consumer(self, topic_key: str, group_id: str):
        """Start consuming messages from a topic."""
        topic = self.topics.get(topic_key, topic_key)
        
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest'
        )
        
        await consumer.start()
        self.consumers[topic] = consumer
        
        asyncio.create_task(self._consume_loop(topic, consumer))
        print(f"Started consumer for topic: {topic}")
    
    async def _consume_loop(self, topic: str, consumer: AIOKafkaConsumer):
        """Internal consumption loop."""
        try:
            async for msg in consumer:
                if not self._running:
                    break
                
                handlers = self.handlers.get(topic, [])
                for handler in handlers:
                    try:
                        message = KafkaMessage.from_dict(msg.value)
                        await handler(message)
                    except Exception as e:
                        print(f"Handler error for {topic}: {e}")
        except Exception as e:
            print(f"Consumer error for {topic}: {e}")
    
    async def get_topic_stats(self) -> Dict[str, Any]:
        """Get statistics for all topics."""
        return {
            "bootstrap_servers": self.bootstrap_servers,
            "topics": list(self.topics.values()),
            "active_consumers": list(self.consumers.keys()),
            "registered_handlers": {k: len(v) for k, v in self.handlers.items()}
        }
