"""OpenSearch service for full-text search and vector storage."""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from opensearchpy import AsyncOpenSearch, helpers

import sys
sys.path.append('..')
from config import settings


class OpenSearchService:
    """OpenSearch service for indexing and searching data."""
    
    # Index names
    INDEX_DOCUMENTS = "documents"
    INDEX_ALERTS = "alerts"
    INDEX_LOGS = "logs"
    INDEX_EVENTS = "events"
    INDEX_SHIFT_LOGS = "shift-logs"
    INDEX_TASKS = "tasks"
    INDEX_VECTORS = "vectors"
    
    def __init__(self):
        self.hosts = settings.OPENSEARCH_HOSTS
        self.prefix = settings.OPENSEARCH_INDEX_PREFIX
        self.client: Optional[AsyncOpenSearch] = None
    
    async def connect(self):
        """Connect to OpenSearch."""
        self.client = AsyncOpenSearch(
            hosts=self.hosts,
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_show_warn=False
        )
        
        # Create indices
        await self._create_indices()
        print(f"OpenSearch connected: {self.hosts}")
    
    async def disconnect(self):
        """Disconnect from OpenSearch."""
        if self.client:
            await self.client.close()
            print("OpenSearch disconnected")
    
    def _index_name(self, index: str) -> str:
        """Get full index name with prefix."""
        return f"{self.prefix}-{index}"
    
    async def _create_indices(self):
        """Create required indices with mappings."""
        indices = {
            self.INDEX_DOCUMENTS: {
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "standard"},
                        "content": {"type": "text", "analyzer": "standard"},
                        "source": {"type": "keyword"},
                        "file_type": {"type": "keyword"},
                        "file_path": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "metadata": {"type": "object"},
                        "created_at": {"type": "date"},
                        "updated_at": {"type": "date"}
                    }
                }
            },
            self.INDEX_ALERTS: {
                "mappings": {
                    "properties": {
                        "alert_type": {"type": "keyword"},
                        "severity": {"type": "keyword"},
                        "message": {"type": "text"},
                        "source": {"type": "keyword"},
                        "tags": {"type": "keyword"},
                        "data": {"type": "object"},
                        "acknowledged": {"type": "boolean"},
                        "acknowledged_by": {"type": "keyword"},
                        "created_at": {"type": "date"}
                    }
                }
            },
            self.INDEX_LOGS: {
                "mappings": {
                    "properties": {
                        "level": {"type": "keyword"},
                        "message": {"type": "text"},
                        "source": {"type": "keyword"},
                        "agent": {"type": "keyword"},
                        "context": {"type": "object"},
                        "timestamp": {"type": "date"}
                    }
                }
            },
            self.INDEX_EVENTS: {
                "mappings": {
                    "properties": {
                        "event_type": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "actor": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "target": {"type": "keyword"},
                        "data": {"type": "object"},
                        "tags": {"type": "keyword"},
                        "timestamp": {"type": "date"}
                    }
                }
            },
            self.INDEX_SHIFT_LOGS: {
                "mappings": {
                    "properties": {
                        "shift_id": {"type": "keyword"},
                        "operator": {"type": "keyword"},
                        "start_time": {"type": "date"},
                        "end_time": {"type": "date"},
                        "status": {"type": "keyword"},
                        "summary": {"type": "text"},
                        "activities": {"type": "nested"},
                        "handoff_notes": {"type": "text"},
                        "tags": {"type": "keyword"}
                    }
                }
            },
            self.INDEX_TASKS: {
                "mappings": {
                    "properties": {
                        "task_type": {"type": "keyword"},
                        "status": {"type": "keyword"},
                        "priority": {"type": "integer"},
                        "assigned_agent": {"type": "keyword"},
                        "input": {"type": "object"},
                        "output": {"type": "object"},
                        "error": {"type": "text"},
                        "created_at": {"type": "date"},
                        "started_at": {"type": "date"},
                        "completed_at": {"type": "date"}
                    }
                }
            },
            self.INDEX_VECTORS: {
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 384,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        },
                        "source": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "metadata": {"type": "object"},
                        "created_at": {"type": "date"}
                    }
                },
                "settings": {
                    "index": {
                        "knn": True
                    }
                }
            }
        }
        
        for index, body in indices.items():
            full_name = self._index_name(index)
            try:
                exists = await self.client.indices.exists(index=full_name)
                if not exists:
                    await self.client.indices.create(index=full_name, body=body)
                    print(f"Created index: {full_name}")
            except Exception as e:
                print(f"Index creation error for {full_name}: {e}")
    
    # ==================== DOCUMENT OPERATIONS ====================
    
    async def index_document(
        self,
        index: str,
        document: Dict[str, Any],
        doc_id: Optional[str] = None
    ) -> str:
        """Index a document."""
        full_index = self._index_name(index)
        doc_id = doc_id or str(uuid.uuid4())
        
        if "created_at" not in document:
            document["created_at"] = datetime.utcnow().isoformat()
        
        await self.client.index(
            index=full_index,
            id=doc_id,
            body=document,
            refresh=True
        )
        return doc_id
    
    async def get_document(
        self,
        index: str,
        doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        full_index = self._index_name(index)
        try:
            result = await self.client.get(index=full_index, id=doc_id)
            doc = result["_source"]
            doc["_id"] = result["_id"]
            return doc
        except Exception:
            return None
    
    async def update_document(
        self,
        index: str,
        doc_id: str,
        updates: Dict[str, Any]
    ):
        """Update a document."""
        full_index = self._index_name(index)
        updates["updated_at"] = datetime.utcnow().isoformat()
        await self.client.update(
            index=full_index,
            id=doc_id,
            body={"doc": updates},
            refresh=True
        )
    
    async def delete_document(self, index: str, doc_id: str):
        """Delete a document."""
        full_index = self._index_name(index)
        await self.client.delete(index=full_index, id=doc_id, refresh=True)
    
    async def bulk_index(
        self,
        index: str,
        documents: List[Dict[str, Any]]
    ) -> int:
        """Bulk index documents."""
        full_index = self._index_name(index)
        
        actions = []
        for doc in documents:
            doc_id = doc.pop("_id", str(uuid.uuid4()))
            if "created_at" not in doc:
                doc["created_at"] = datetime.utcnow().isoformat()
            
            actions.append({
                "_index": full_index,
                "_id": doc_id,
                "_source": doc
            })
        
        success, _ = await helpers.async_bulk(self.client, actions)
        return success
    
    # ==================== SEARCH OPERATIONS ====================
    
    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Search documents."""
        full_index = self._index_name(index)
        
        body = {
            "query": query,
            "size": size,
            "from": from_
        }
        
        if sort:
            body["sort"] = sort
        
        result = await self.client.search(index=full_index, body=body)
        
        hits = []
        for hit in result["hits"]["hits"]:
            doc = hit["_source"]
            doc["_id"] = hit["_id"]
            doc["_score"] = hit["_score"]
            hits.append(doc)
        
        return {
            "total": result["hits"]["total"]["value"],
            "hits": hits
        }
    
    async def full_text_search(
        self,
        index: str,
        query_text: str,
        fields: List[str],
        size: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Full-text search across fields."""
        must = [
            {
                "multi_match": {
                    "query": query_text,
                    "fields": fields,
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    must.append({"terms": {field: value}})
                else:
                    must.append({"term": {field: value}})
        
        return await self.search(
            index=index,
            query={"bool": {"must": must}},
            size=size
        )
    
    async def vector_search(
        self,
        embedding: List[float],
        size: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Vector similarity search."""
        query = {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": size
                }
            }
        }
        
        if filters:
            query = {
                "bool": {
                    "must": [query],
                    "filter": [{"term": {k: v}} for k, v in filters.items()]
                }
            }
        
        return await self.search(
            index=self.INDEX_VECTORS,
            query=query,
            size=size
        )
    
    # ==================== SPECIALIZED QUERIES ====================
    
    async def get_alerts(
        self,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get alerts with filters."""
        must = []
        
        if severity:
            must.append({"term": {"severity": severity}})
        if acknowledged is not None:
            must.append({"term": {"acknowledged": acknowledged}})
        
        query = {"bool": {"must": must}} if must else {"match_all": {}}
        
        result = await self.search(
            index=self.INDEX_ALERTS,
            query=query,
            size=limit,
            sort=[{"created_at": {"order": "desc"}}]
        )
        return result["hits"]
    
    async def get_shift_logs(
        self,
        operator: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get shift logs with filters."""
        must = []
        
        if operator:
            must.append({"term": {"operator": operator}})
        if status:
            must.append({"term": {"status": status}})
        if start_date or end_date:
            range_query = {"start_time": {}}
            if start_date:
                range_query["start_time"]["gte"] = start_date
            if end_date:
                range_query["start_time"]["lte"] = end_date
            must.append({"range": range_query})
        
        query = {"bool": {"must": must}} if must else {"match_all": {}}
        
        result = await self.search(
            index=self.INDEX_SHIFT_LOGS,
            query=query,
            size=limit,
            sort=[{"start_time": {"order": "desc"}}]
        )
        return result["hits"]
    
    async def get_recent_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent events."""
        must = [
            {
                "range": {
                    "timestamp": {
                        "gte": f"now-{hours}h"
                    }
                }
            }
        ]
        
        if event_type:
            must.append({"term": {"event_type": event_type}})
        if source:
            must.append({"term": {"source": source}})
        
        result = await self.search(
            index=self.INDEX_EVENTS,
            query={"bool": {"must": must}},
            size=limit,
            sort=[{"timestamp": {"order": "desc"}}]
        )
        return result["hits"]
    
    async def aggregate_by_field(
        self,
        index: str,
        field: str,
        size: int = 10
    ) -> List[Dict[str, Any]]:
        """Aggregate documents by a field."""
        full_index = self._index_name(index)
        
        body = {
            "size": 0,
            "aggs": {
                "by_field": {
                    "terms": {
                        "field": field,
                        "size": size
                    }
                }
            }
        }
        
        result = await self.client.search(index=full_index, body=body)
        return result["aggregations"]["by_field"]["buckets"]
    
    # ==================== STATS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get OpenSearch statistics."""
        indices = await self.client.cat.indices(format="json")
        
        return {
            "cluster_health": await self.client.cluster.health(),
            "indices": [
                {
                    "name": idx["index"],
                    "docs": idx["docs.count"],
                    "size": idx["store.size"]
                }
                for idx in indices
                if idx["index"].startswith(self.prefix)
            ]
        }
