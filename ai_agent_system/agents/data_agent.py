"""Data Agent for database queries, data retrieval, and management."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from .base_agent import BaseAgent

import sys
sys.path.append('..')
from config import settings


class DataAgent(BaseAgent):
    """Agent specialized in data queries, retrieval, and management."""
    
    SYSTEM_PROMPT = """You are a Data Management Agent specialized in database queries and data operations.

Your responsibilities:
1. Translate natural language queries into structured queries
2. Retrieve and format data from various sources
3. Generate data summaries and statistics
4. Manage shift logs and activity records
5. Search and sort data based on user requests

When generating queries, consider:
- OpenSearch query DSL for search operations
- Proper field names and data types
- Pagination and sorting requirements
- Aggregations for statistics

Available data sources:
- documents: Ingested documents with content and metadata
- alerts: System alerts with severity and status
- logs: Application and agent logs
- events: System events and activities
- shift-logs: Operator shift records
- tasks: Automated task records

Respond in JSON format with structured queries and results."""

    def __init__(self, opensearch_service=None, redis_service=None):
        super().__init__(
            agent_id="data-agent",
            model=settings.DATA_MODEL,
            system_prompt=self.SYSTEM_PROMPT,
            description="Data queries, retrieval, and management agent"
        )
        self.opensearch = opensearch_service
        self.redis = redis_service
    
    def set_services(self, opensearch_service, redis_service):
        """Set service dependencies."""
        self.opensearch = opensearch_service
        self.redis = redis_service
    
    async def natural_language_query(
        self,
        query: str,
        index: str = "documents"
    ) -> Dict[str, Any]:
        """Convert natural language to OpenSearch query and execute."""
        prompt = f"""Convert this natural language query to an OpenSearch query:

Query: "{query}"
Index: {index}

Generate an OpenSearch query DSL in JSON format.
Include appropriate:
- match or multi_match for text search
- term/terms for exact matches
- range for date/number ranges
- bool for combining conditions
- sort for ordering
- size for limiting results

Respond with just the query JSON."""

        response = await self.generate(prompt)
        
        # Extract JSON query
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                query_dsl = json.loads(json_match.group())
            else:
                # Fallback to simple match query
                query_dsl = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["*"],
                            "fuzziness": "AUTO"
                        }
                    }
                }
        except json.JSONDecodeError:
            query_dsl = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["*"],
                        "fuzziness": "AUTO"
                    }
                }
            }
        
        # Execute query if OpenSearch is available
        results = None
        if self.opensearch:
            try:
                results = await self.opensearch.search(
                    index=index,
                    query=query_dsl.get("query", query_dsl),
                    size=query_dsl.get("size", 10),
                    sort=query_dsl.get("sort")
                )
            except Exception as e:
                results = {"error": str(e)}
        
        return {
            "original_query": query,
            "generated_query": query_dsl,
            "results": results,
            "executed_at": datetime.utcnow().isoformat()
        }
    
    async def get_shift_log(
        self,
        shift_id: Optional[str] = None,
        operator: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve shift log information."""
        if self.opensearch:
            results = await self.opensearch.get_shift_logs(
                operator=operator,
                start_date=date
            )
            
            if shift_id:
                results = [r for r in results if r.get("shift_id") == shift_id]
            
            return {
                "shift_logs": results,
                "count": len(results),
                "retrieved_at": datetime.utcnow().isoformat()
            }
        
        return {"error": "OpenSearch not available", "shift_logs": []}
    
    async def create_shift_log(
        self,
        operator: str,
        summary: str,
        activities: List[Dict[str, Any]],
        handoff_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new shift log entry."""
        shift_log = {
            "shift_id": f"shift-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "operator": operator,
            "start_time": datetime.utcnow().isoformat(),
            "status": "active",
            "summary": summary,
            "activities": activities,
            "handoff_notes": handoff_notes or ""
        }
        
        if self.opensearch:
            doc_id = await self.opensearch.index_document(
                index="shift-logs",
                document=shift_log
            )
            shift_log["_id"] = doc_id
        
        return shift_log
    
    async def end_shift_log(
        self,
        shift_id: str,
        final_summary: str,
        handoff_notes: str
    ) -> Dict[str, Any]:
        """End a shift log."""
        if self.opensearch:
            await self.opensearch.update_document(
                index="shift-logs",
                doc_id=shift_id,
                updates={
                    "status": "completed",
                    "end_time": datetime.utcnow().isoformat(),
                    "final_summary": final_summary,
                    "handoff_notes": handoff_notes
                }
            )
            
            return await self.opensearch.get_document("shift-logs", shift_id)
        
        return {"error": "OpenSearch not available"}
    
    async def search_data(
        self,
        query: str,
        index: str = "documents",
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "desc",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search data with filters and sorting."""
        if self.opensearch:
            # Build sort
            sort = None
            if sort_by:
                sort = [{sort_by: {"order": sort_order}}]
            
            results = await self.opensearch.full_text_search(
                index=index,
                query_text=query,
                fields=["*"],
                size=limit,
                filters=filters
            )
            
            return {
                "query": query,
                "filters": filters,
                "results": results.get("hits", []),
                "total": results.get("total", 0),
                "searched_at": datetime.utcnow().isoformat()
            }
        
        return {"error": "OpenSearch not available", "results": []}
    
    async def get_statistics(
        self,
        index: str,
        field: str,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics for a field."""
        if self.opensearch:
            aggregations = await self.opensearch.aggregate_by_field(
                index=index,
                field=field
            )
            
            return {
                "index": index,
                "field": field,
                "aggregations": aggregations,
                "generated_at": datetime.utcnow().isoformat()
            }
        
        return {"error": "OpenSearch not available"}
    
    async def generate_data_summary(
        self,
        data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a summary of data."""
        prompt = f"""Summarize the following data:

{json.dumps(data[:20], indent=2)}  # First 20 records

Provide:
1. Overview of the data
2. Key statistics
3. Notable patterns
4. Data quality observations

Respond in JSON format."""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                summary = json.loads(json_match.group())
            else:
                summary = {"summary": response}
        except json.JSONDecodeError:
            summary = {"summary": response}
        
        summary["record_count"] = len(data)
        summary["generated_at"] = datetime.utcnow().isoformat()
        
        return summary
    
    async def answer_data_question(
        self,
        question: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Answer a question about data."""
        # First, try to understand what data is needed
        prompt = f"""Answer this question about the data:

Question: {question}
{f'Context: {context}' if context else ''}

If you need to query data, specify:
1. Which index to query (documents, alerts, logs, events, shift-logs, tasks)
2. What search terms or filters to use
3. How to interpret the results

Provide a helpful answer based on available information."""

        response = await self.generate(prompt)
        
        return {
            "question": question,
            "answer": response,
            "answered_at": datetime.utcnow().isoformat()
        }
    
    async def ingest_data(
        self,
        data: Dict[str, Any],
        index: str = "documents",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Ingest data into the system."""
        document = {
            **data,
            "tags": tags or [],
            "ingested_at": datetime.utcnow().isoformat(),
            "ingested_by": self.agent_id
        }
        
        if self.opensearch:
            doc_id = await self.opensearch.index_document(
                index=index,
                document=document
            )
            
            return {
                "success": True,
                "document_id": doc_id,
                "index": index,
                "ingested_at": document["ingested_at"]
            }
        
        return {"success": False, "error": "OpenSearch not available"}
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data request."""
        action = input_data.get("action", "query")
        
        if action == "query":
            return await self.natural_language_query(
                input_data.get("query", ""),
                input_data.get("index", "documents")
            )
        elif action == "search":
            return await self.search_data(
                input_data.get("query", ""),
                input_data.get("index", "documents"),
                input_data.get("filters"),
                input_data.get("sort_by"),
                input_data.get("sort_order", "desc"),
                input_data.get("limit", 10)
            )
        elif action == "shift_log":
            if input_data.get("create"):
                return await self.create_shift_log(
                    input_data.get("operator", ""),
                    input_data.get("summary", ""),
                    input_data.get("activities", []),
                    input_data.get("handoff_notes")
                )
            elif input_data.get("end"):
                return await self.end_shift_log(
                    input_data.get("shift_id", ""),
                    input_data.get("final_summary", ""),
                    input_data.get("handoff_notes", "")
                )
            else:
                return await self.get_shift_log(
                    input_data.get("shift_id"),
                    input_data.get("operator"),
                    input_data.get("date")
                )
        elif action == "statistics":
            return await self.get_statistics(
                input_data.get("index", "documents"),
                input_data.get("field", "tags")
            )
        elif action == "summarize":
            return await self.generate_data_summary(
                input_data.get("data", [])
            )
        elif action == "question":
            return await self.answer_data_question(
                input_data.get("question", ""),
                input_data.get("context")
            )
        elif action == "ingest":
            return await self.ingest_data(
                input_data.get("data", {}),
                input_data.get("index", "documents"),
                input_data.get("tags")
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_capabilities(self) -> List[str]:
        return [
            "natural_language_query",
            "data_search",
            "shift_log_management",
            "statistics_generation",
            "data_summarization",
            "question_answering",
            "data_ingestion",
            "data_sorting",
            "data_filtering"
        ]
