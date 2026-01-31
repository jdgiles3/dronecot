"""Analysis Agent for pattern recognition, insights, and report generation."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from .base_agent import BaseAgent

import sys
sys.path.append('..')
from config import settings


class AnalysisAgent(BaseAgent):
    """Agent specialized in data analysis, pattern recognition, and insights."""
    
    SYSTEM_PROMPT = """You are a Data Analysis Agent specialized in pattern recognition and generating insights.

Your responsibilities:
1. Analyze data to identify patterns, trends, and correlations
2. Generate actionable insights from complex datasets
3. Create comprehensive reports and summaries
4. Provide statistical analysis and predictions
5. Answer questions about data with supporting evidence

When analyzing data, consider:
- Temporal patterns (daily, weekly, seasonal)
- Correlations between variables
- Anomalies and outliers
- Trends and forecasts
- Statistical significance

Always provide:
- Clear, data-driven conclusions
- Confidence levels for predictions
- Supporting evidence for insights
- Actionable recommendations

Respond in structured JSON format when appropriate."""

    def __init__(self):
        super().__init__(
            agent_id="analysis-agent",
            model=settings.ANALYSIS_MODEL,
            system_prompt=self.SYSTEM_PROMPT,
            description="Data analysis, pattern recognition, and insights agent"
        )
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    async def analyze_patterns(
        self,
        data: List[Dict[str, Any]],
        focus_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze data for patterns and trends."""
        prompt = f"""Analyze the following dataset for patterns and trends:

Data ({len(data)} records):
{json.dumps(data[:50], indent=2)}  # First 50 records for context

{f'Focus on these fields: {focus_fields}' if focus_fields else ''}

Identify:
1. Temporal patterns
2. Correlations between fields
3. Unusual patterns or anomalies
4. Trends over time

Respond in JSON format with:
{{
    "patterns": [
        {{"type": "pattern type", "description": "...", "confidence": 0.0-1.0, "evidence": "..."}}
    ],
    "correlations": [
        {{"fields": ["field1", "field2"], "strength": 0.0-1.0, "direction": "positive/negative"}}
    ],
    "trends": [
        {{"field": "field_name", "direction": "increasing/decreasing/stable", "rate": "..."}}
    ],
    "anomalies": [
        {{"description": "...", "severity": "high/medium/low"}}
    ],
    "summary": "overall analysis summary"
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"summary": response, "patterns": [], "correlations": [], "trends": []}
        except json.JSONDecodeError:
            result = {"summary": response, "patterns": [], "correlations": [], "trends": []}
        
        result["analyzed_at"] = datetime.utcnow().isoformat()
        result["record_count"] = len(data)
        
        return result
    
    async def generate_insights(
        self,
        data: Dict[str, Any],
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate insights from data."""
        prompt = f"""Generate insights from the following data:

{json.dumps(data, indent=2)}

{f'Specific question: {question}' if question else 'Provide general insights.'}

Provide:
1. Key findings
2. Actionable insights
3. Recommendations
4. Areas requiring attention

Respond in JSON format with:
{{
    "key_findings": ["finding1", "finding2"],
    "insights": [
        {{"insight": "...", "importance": "high/medium/low", "action": "recommended action"}}
    ],
    "recommendations": ["rec1", "rec2"],
    "attention_areas": ["area1", "area2"],
    "confidence": 0.0-1.0
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"insights": [{"insight": response, "importance": "medium"}]}
        except json.JSONDecodeError:
            result = {"insights": [{"insight": response, "importance": "medium"}]}
        
        result["generated_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def generate_report(
        self,
        data: Dict[str, Any],
        report_type: str = "summary",
        include_charts: bool = False
    ) -> Dict[str, Any]:
        """Generate a comprehensive report."""
        prompt = f"""Generate a {report_type} report from the following data:

{json.dumps(data, indent=2)}

Create a professional report with:
1. Executive Summary
2. Key Metrics
3. Detailed Analysis
4. Trends and Patterns
5. Recommendations
6. Conclusion

Respond in JSON format with:
{{
    "title": "Report Title",
    "executive_summary": "...",
    "key_metrics": {{"metric": "value"}},
    "sections": [
        {{"title": "Section Title", "content": "...", "highlights": []}}
    ],
    "recommendations": ["rec1", "rec2"],
    "conclusion": "..."
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                report = json.loads(json_match.group())
            else:
                report = {
                    "title": f"{report_type.title()} Report",
                    "executive_summary": response,
                    "sections": []
                }
        except json.JSONDecodeError:
            report = {
                "title": f"{report_type.title()} Report",
                "executive_summary": response,
                "sections": []
            }
        
        report["report_type"] = report_type
        report["generated_at"] = datetime.utcnow().isoformat()
        report["agent_id"] = self.agent_id
        
        return report
    
    async def answer_question(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Answer a question about data."""
        prompt = f"""Answer the following question based on the provided data:

Question: {question}

Data Context:
{json.dumps(context, indent=2)}

Provide a clear, data-driven answer with:
1. Direct answer to the question
2. Supporting evidence from the data
3. Confidence level
4. Any caveats or limitations

Respond in JSON format with:
{{
    "answer": "direct answer",
    "evidence": ["evidence1", "evidence2"],
    "confidence": 0.0-1.0,
    "caveats": ["caveat1"],
    "related_insights": ["insight1"]
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"answer": response, "confidence": 0.7}
        except json.JSONDecodeError:
            result = {"answer": response, "confidence": 0.7}
        
        result["question"] = question
        result["answered_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def compare_datasets(
        self,
        dataset1: Dict[str, Any],
        dataset2: Dict[str, Any],
        comparison_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compare two datasets."""
        prompt = f"""Compare the following two datasets:

Dataset 1:
{json.dumps(dataset1, indent=2)}

Dataset 2:
{json.dumps(dataset2, indent=2)}

{f'Focus on comparing: {comparison_fields}' if comparison_fields else ''}

Provide:
1. Key differences
2. Similarities
3. Changes over time (if applicable)
4. Statistical comparison

Respond in JSON format with:
{{
    "differences": [{{"field": "...", "dataset1_value": "...", "dataset2_value": "...", "significance": "high/medium/low"}}],
    "similarities": ["similarity1", "similarity2"],
    "changes": [{{"field": "...", "change": "...", "percentage": 0.0}}],
    "summary": "overall comparison summary"
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"summary": response}
        except json.JSONDecodeError:
            result = {"summary": response}
        
        result["compared_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def forecast(
        self,
        historical_data: List[Dict[str, Any]],
        target_field: str,
        periods: int = 5
    ) -> Dict[str, Any]:
        """Generate forecasts based on historical data."""
        prompt = f"""Based on the following historical data, forecast the next {periods} periods for '{target_field}':

Historical Data:
{json.dumps(historical_data[-30:], indent=2)}  # Last 30 records

Provide:
1. Forecasted values
2. Confidence intervals
3. Trend analysis
4. Factors influencing the forecast

Respond in JSON format with:
{{
    "forecasts": [
        {{"period": 1, "value": 0.0, "lower_bound": 0.0, "upper_bound": 0.0}}
    ],
    "trend": "increasing/decreasing/stable",
    "trend_strength": 0.0-1.0,
    "influencing_factors": ["factor1", "factor2"],
    "confidence": 0.0-1.0,
    "methodology": "description of approach"
}}"""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"forecasts": [], "summary": response}
        except json.JSONDecodeError:
            result = {"forecasts": [], "summary": response}
        
        result["target_field"] = target_field
        result["periods_forecasted"] = periods
        result["generated_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis request."""
        action = input_data.get("action", "insights")
        
        if action == "patterns":
            return await self.analyze_patterns(
                input_data.get("data", []),
                input_data.get("focus_fields")
            )
        elif action == "insights":
            return await self.generate_insights(
                input_data.get("data", {}),
                input_data.get("question")
            )
        elif action == "report":
            return await self.generate_report(
                input_data.get("data", {}),
                input_data.get("report_type", "summary")
            )
        elif action == "question":
            return await self.answer_question(
                input_data.get("question", ""),
                input_data.get("context", {})
            )
        elif action == "compare":
            return await self.compare_datasets(
                input_data.get("dataset1", {}),
                input_data.get("dataset2", {}),
                input_data.get("comparison_fields")
            )
        elif action == "forecast":
            return await self.forecast(
                input_data.get("data", []),
                input_data.get("target_field", "value"),
                input_data.get("periods", 5)
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_capabilities(self) -> List[str]:
        return [
            "pattern_recognition",
            "trend_analysis",
            "insight_generation",
            "report_generation",
            "question_answering",
            "dataset_comparison",
            "forecasting",
            "correlation_analysis"
        ]
