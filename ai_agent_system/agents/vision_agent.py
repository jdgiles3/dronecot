"""Vision Agent for image analysis and visual task execution."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
import base64
import io

from .base_agent import BaseAgent

import sys
sys.path.append('..')
from config import settings


class VisionAgent(BaseAgent):
    """Agent specialized in image analysis and visual understanding."""
    
    SYSTEM_PROMPT = """You are a Vision Analysis Agent specialized in image understanding and visual task execution.

Your responsibilities:
1. Analyze images to extract information
2. Describe visual content in detail
3. Identify objects, text, and patterns in images
4. Answer questions about visual content
5. Guide visual automation tasks

When analyzing images, provide:
1. Detailed description of what you see
2. Identified objects and their locations
3. Any text visible in the image (OCR)
4. Relevant patterns or anomalies
5. Confidence levels for identifications

Respond in structured JSON format when appropriate."""

    def __init__(self):
        super().__init__(
            agent_id="vision-agent",
            model=settings.VISION_MODEL,
            system_prompt=self.SYSTEM_PROMPT,
            description="Image analysis and visual understanding agent"
        )
    
    async def analyze_image(
        self,
        image_data: bytes,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze an image using vision model."""
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        prompt = question or "Describe this image in detail. Identify all objects, text, and notable features."
        
        try:
            # Use Ollama's vision capability
            response = await self.ollama.client.post(
                f"{self.ollama.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            
            analysis = {
                "description": result.get("response", ""),
                "model": self.model,
                "analyzed_at": datetime.utcnow().isoformat()
            }
            
            # Try to extract structured data
            if question:
                analysis["question"] = question
            
            return analysis
            
        except Exception as e:
            return {
                "error": str(e),
                "analyzed_at": datetime.utcnow().isoformat()
            }
    
    async def analyze_image_from_path(
        self,
        image_path: str,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze an image from file path."""
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        result = await self.analyze_image(image_data, question)
        result["image_path"] = image_path
        return result
    
    async def analyze_image_from_url(
        self,
        image_url: str,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze an image from URL."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            image_data = response.content
        
        result = await self.analyze_image(image_data, question)
        result["image_url"] = image_url
        return result
    
    async def extract_text(
        self,
        image_data: bytes
    ) -> Dict[str, Any]:
        """Extract text from an image (OCR)."""
        return await self.analyze_image(
            image_data,
            "Extract all text visible in this image. List each text element separately."
        )
    
    async def identify_objects(
        self,
        image_data: bytes
    ) -> Dict[str, Any]:
        """Identify objects in an image."""
        result = await self.analyze_image(
            image_data,
            """Identify all objects in this image. For each object provide:
            1. Object name
            2. Approximate location (top-left, center, bottom-right, etc.)
            3. Confidence level (high, medium, low)
            
            Respond in JSON format with an 'objects' array."""
        )
        
        # Try to parse objects from response
        try:
            json_match = re.search(r'\{[\s\S]*\}', result.get("description", ""))
            if json_match:
                objects_data = json.loads(json_match.group())
                result["objects"] = objects_data.get("objects", [])
        except:
            pass
        
        return result
    
    async def compare_images(
        self,
        image1_data: bytes,
        image2_data: bytes
    ) -> Dict[str, Any]:
        """Compare two images."""
        # Analyze both images
        analysis1 = await self.analyze_image(image1_data, "Describe this image in detail.")
        analysis2 = await self.analyze_image(image2_data, "Describe this image in detail.")
        
        # Use text model to compare
        comparison_prompt = f"""Compare these two image descriptions:

Image 1: {analysis1.get('description', '')}

Image 2: {analysis2.get('description', '')}

Identify:
1. Similarities
2. Differences
3. Changes (if they appear to be the same scene)

Respond in JSON format."""

        comparison = await self.generate(comparison_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', comparison)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"comparison": comparison}
        except:
            result = {"comparison": comparison}
        
        result["image1_analysis"] = analysis1
        result["image2_analysis"] = analysis2
        result["compared_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def analyze_screenshot(
        self,
        screenshot_data: bytes,
        task_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze a screenshot for automation guidance."""
        question = "Analyze this screenshot. Identify:"
        question += "\n1. All interactive elements (buttons, links, inputs)"
        question += "\n2. Current page state"
        question += "\n3. Any error messages or notifications"
        
        if task_context:
            question += f"\n\nTask context: {task_context}"
            question += "\nProvide guidance on how to proceed with the task."
        
        return await self.analyze_image(screenshot_data, question)
    
    async def guide_visual_task(
        self,
        screenshot_data: bytes,
        task_description: str,
        previous_actions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Guide a visual automation task."""
        question = f"""Task: {task_description}

Analyze this screenshot and provide the next action to take.

{f'Previous actions taken: {previous_actions}' if previous_actions else ''}

Respond with:
1. Current state assessment
2. Next recommended action
3. Element to interact with (describe location and appearance)
4. Expected result of the action

Respond in JSON format with 'assessment', 'next_action', 'target_element', and 'expected_result' fields."""

        result = await self.analyze_image(screenshot_data, question)
        
        # Try to parse structured guidance
        try:
            json_match = re.search(r'\{[\s\S]*\}', result.get("description", ""))
            if json_match:
                guidance = json.loads(json_match.group())
                result.update(guidance)
        except:
            pass
        
        result["task_description"] = task_description
        return result
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process vision request."""
        action = input_data.get("action", "analyze")
        
        # Get image data
        image_data = None
        if "image_data" in input_data:
            if isinstance(input_data["image_data"], str):
                image_data = base64.b64decode(input_data["image_data"])
            else:
                image_data = input_data["image_data"]
        elif "image_path" in input_data:
            with open(input_data["image_path"], 'rb') as f:
                image_data = f.read()
        elif "image_url" in input_data:
            return await self.analyze_image_from_url(
                input_data["image_url"],
                input_data.get("question")
            )
        
        if not image_data and action != "compare":
            return {"error": "No image data provided"}
        
        if action == "analyze":
            return await self.analyze_image(
                image_data,
                input_data.get("question")
            )
        elif action == "ocr":
            return await self.extract_text(image_data)
        elif action == "objects":
            return await self.identify_objects(image_data)
        elif action == "compare":
            image2_data = input_data.get("image2_data")
            if isinstance(image2_data, str):
                image2_data = base64.b64decode(image2_data)
            return await self.compare_images(image_data, image2_data)
        elif action == "screenshot":
            return await self.analyze_screenshot(
                image_data,
                input_data.get("task_context")
            )
        elif action == "guide":
            return await self.guide_visual_task(
                image_data,
                input_data.get("task", ""),
                input_data.get("previous_actions")
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_capabilities(self) -> List[str]:
        return [
            "image_analysis",
            "object_detection",
            "text_extraction",
            "image_comparison",
            "screenshot_analysis",
            "visual_task_guidance",
            "scene_understanding"
        ]
