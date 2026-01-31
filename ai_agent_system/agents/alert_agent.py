"""Alert Agent for anomaly detection and threshold monitoring."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re

from .base_agent import BaseAgent

import sys
sys.path.append('..')
from config import settings


class AlertAgent(BaseAgent):
    """Agent specialized in anomaly detection and alert generation."""
    
    SYSTEM_PROMPT = """You are an Alert Analysis Agent specialized in detecting anomalies and generating alerts.

Your responsibilities:
1. Analyze incoming data for anomalies and unusual patterns
2. Evaluate metrics against thresholds
3. Generate clear, actionable alerts with severity levels
4. Provide context and recommended actions

Alert Severity Levels:
- CRITICAL: Immediate action required, system failure imminent
- HIGH: Urgent attention needed, significant impact
- MEDIUM: Should be addressed soon, moderate impact
- LOW: Informational, minor impact
- INFO: For tracking purposes only

When analyzing data, always respond in this JSON format:
{
    "is_anomaly": true/false,
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "alert_type": "type of alert",
    "title": "brief alert title",
    "description": "detailed description",
    "affected_components": ["list", "of", "components"],
    "recommended_actions": ["action1", "action2"],
    "confidence": 0.0-1.0,
    "metrics": {"relevant": "metrics"}
}

Be precise, technical, and actionable in your analysis."""

    def __init__(self):
        super().__init__(
            agent_id="alert-agent",
            model=settings.ALERT_MODEL,
            system_prompt=self.SYSTEM_PROMPT,
            description="Anomaly detection and alert generation agent"
        )
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.alert_history: List[Dict[str, Any]] = []
    
    def set_threshold(
        self,
        metric_name: str,
        warning: float,
        critical: float,
        comparison: str = "gt"  # gt, lt, eq
    ):
        """Set threshold for a metric."""
        self.thresholds[metric_name] = {
            "warning": warning,
            "critical": critical,
            "comparison": comparison
        }
    
    def check_threshold(
        self,
        metric_name: str,
        value: float
    ) -> Optional[Dict[str, Any]]:
        """Check if a value exceeds thresholds."""
        if metric_name not in self.thresholds:
            return None
        
        threshold = self.thresholds[metric_name]
        comparison = threshold["comparison"]
        
        severity = None
        if comparison == "gt":
            if value >= threshold["critical"]:
                severity = "CRITICAL"
            elif value >= threshold["warning"]:
                severity = "HIGH"
        elif comparison == "lt":
            if value <= threshold["critical"]:
                severity = "CRITICAL"
            elif value <= threshold["warning"]:
                severity = "HIGH"
        
        if severity:
            return {
                "metric": metric_name,
                "value": value,
                "threshold": threshold,
                "severity": severity
            }
        return None
    
    async def analyze_metrics(
        self,
        metrics: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Analyze multiple metrics for threshold violations."""
        alerts = []
        for metric_name, value in metrics.items():
            result = self.check_threshold(metric_name, value)
            if result:
                alerts.append(result)
        return alerts
    
    async def detect_anomaly(
        self,
        data: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Use LLM to detect anomalies in data."""
        prompt = f"""Analyze the following data for anomalies:

Data:
{json.dumps(data, indent=2)}

{f'Context: {context}' if context else ''}

Identify any anomalies, unusual patterns, or concerning values.
Respond with a JSON analysis."""

        response = await self.generate(prompt)
        
        # Parse JSON from response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "is_anomaly": False,
                    "severity": "INFO",
                    "description": response,
                    "confidence": 0.5
                }
        except json.JSONDecodeError:
            result = {
                "is_anomaly": False,
                "severity": "INFO",
                "description": response,
                "confidence": 0.5
            }
        
        result["timestamp"] = datetime.utcnow().isoformat()
        result["agent_id"] = self.agent_id
        
        if result.get("is_anomaly"):
            self.alert_history.append(result)
        
        return result
    
    async def generate_alert(
        self,
        alert_type: str,
        data: Dict[str, Any],
        severity: str = "MEDIUM"
    ) -> Dict[str, Any]:
        """Generate a detailed alert."""
        prompt = f"""Generate a detailed alert for the following situation:

Alert Type: {alert_type}
Severity: {severity}
Data:
{json.dumps(data, indent=2)}

Provide a comprehensive alert with title, description, affected components, and recommended actions.
Respond in JSON format."""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                alert = json.loads(json_match.group())
            else:
                alert = {
                    "title": f"{alert_type} Alert",
                    "description": response
                }
        except json.JSONDecodeError:
            alert = {
                "title": f"{alert_type} Alert",
                "description": response
            }
        
        alert.update({
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "raw_data": data
        })
        
        self.alert_history.append(alert)
        return alert
    
    async def summarize_alerts(
        self,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Summarize recent alerts."""
        recent_alerts = self.alert_history[-100:]  # Last 100 alerts
        
        if not recent_alerts:
            return {
                "summary": "No alerts in the specified time range",
                "total_alerts": 0,
                "by_severity": {},
                "by_type": {}
            }
        
        prompt = f"""Summarize the following alerts:

{json.dumps(recent_alerts, indent=2)}

Provide:
1. Overall summary
2. Key patterns or trends
3. Most critical issues
4. Recommended priorities

Respond in JSON format with 'summary', 'patterns', 'critical_issues', and 'priorities' fields."""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                summary = json.loads(json_match.group())
            else:
                summary = {"summary": response}
        except json.JSONDecodeError:
            summary = {"summary": response}
        
        # Add statistics
        by_severity = {}
        by_type = {}
        for alert in recent_alerts:
            sev = alert.get("severity", "UNKNOWN")
            typ = alert.get("alert_type", "UNKNOWN")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            by_type[typ] = by_type.get(typ, 0) + 1
        
        summary["total_alerts"] = len(recent_alerts)
        summary["by_severity"] = by_severity
        summary["by_type"] = by_type
        
        return summary
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and generate alerts."""
        action = input_data.get("action", "detect")
        
        if action == "detect":
            return await self.detect_anomaly(
                input_data.get("data", {}),
                input_data.get("context")
            )
        elif action == "generate":
            return await self.generate_alert(
                input_data.get("alert_type", "general"),
                input_data.get("data", {}),
                input_data.get("severity", "MEDIUM")
            )
        elif action == "check_metrics":
            return {
                "alerts": await self.analyze_metrics(input_data.get("metrics", {}))
            }
        elif action == "summarize":
            return await self.summarize_alerts(
                input_data.get("hours", 24)
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_capabilities(self) -> List[str]:
        return [
            "anomaly_detection",
            "threshold_monitoring",
            "alert_generation",
            "pattern_analysis",
            "alert_summarization",
            "metric_evaluation"
        ]
