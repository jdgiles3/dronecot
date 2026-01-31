"""Task Agent for code generation and Playwright automation."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import re
import asyncio

from .base_agent import BaseAgent

import sys
sys.path.append('..')
from config import settings


class PlaywrightExecutor:
    """Execute Playwright automation tasks."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
    
    async def initialize(self):
        """Initialize Playwright browser."""
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()
            return True
        except Exception as e:
            print(f"Playwright initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown Playwright."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        try:
            response = await self.page.goto(url, wait_until="networkidle")
            return {
                "success": True,
                "url": self.page.url,
                "status": response.status if response else None,
                "title": await self.page.title()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element."""
        try:
            await self.page.click(selector)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """Fill a form field."""
        try:
            await self.page.fill(selector, value)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_text(self, selector: str) -> Dict[str, Any]:
        """Get text content of an element."""
        try:
            text = await self.page.text_content(selector)
            return {"success": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def screenshot(self, path: str = None) -> Dict[str, Any]:
        """Take a screenshot."""
        try:
            screenshot = await self.page.screenshot(path=path, full_page=True)
            return {
                "success": True,
                "path": path,
                "size": len(screenshot) if screenshot else 0
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def evaluate(self, script: str) -> Dict[str, Any]:
        """Evaluate JavaScript."""
        try:
            result = await self.page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def wait_for_selector(self, selector: str, timeout: int = 30000) -> Dict[str, Any]:
        """Wait for an element."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_page_content(self) -> Dict[str, Any]:
        """Get page HTML content."""
        try:
            content = await self.page.content()
            return {
                "success": True,
                "content": content[:10000],  # Limit size
                "url": self.page.url,
                "title": await self.page.title()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class TaskAgent(BaseAgent):
    """Agent specialized in code generation and task automation."""
    
    SYSTEM_PROMPT = """You are a Task Automation Agent specialized in code generation and browser automation.

Your responsibilities:
1. Generate code to accomplish tasks
2. Create Playwright automation scripts
3. Execute browser-based tasks autonomously
4. Parse and extract data from web pages
5. Automate repetitive workflows

When generating automation scripts, use this format:
{
    "steps": [
        {"action": "navigate", "url": "https://example.com"},
        {"action": "wait", "selector": "#element"},
        {"action": "click", "selector": "#button"},
        {"action": "fill", "selector": "#input", "value": "text"},
        {"action": "screenshot", "path": "result.png"},
        {"action": "extract", "selector": ".data", "attribute": "text"}
    ],
    "description": "What this automation does",
    "expected_result": "What should happen"
}

Available actions:
- navigate: Go to a URL
- click: Click an element
- fill: Fill a form field
- wait: Wait for an element
- screenshot: Take a screenshot
- extract: Extract data from elements
- evaluate: Run JavaScript
- scroll: Scroll the page

Be precise with selectors and handle errors gracefully."""

    def __init__(self):
        super().__init__(
            agent_id="task-agent",
            model=settings.TASK_MODEL,
            system_prompt=self.SYSTEM_PROMPT,
            description="Code generation and browser automation agent"
        )
        self.executor: Optional[PlaywrightExecutor] = None
        self.task_history: List[Dict[str, Any]] = []
    
    async def initialize(self) -> bool:
        """Initialize agent and Playwright."""
        base_init = await super().initialize()
        
        self.executor = PlaywrightExecutor(headless=settings.PLAYWRIGHT_HEADLESS)
        playwright_init = await self.executor.initialize()
        
        return base_init and playwright_init
    
    async def shutdown(self):
        """Shutdown agent and Playwright."""
        if self.executor:
            await self.executor.shutdown()
        await super().shutdown()
    
    async def generate_automation(
        self,
        task_description: str,
        target_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate automation steps for a task."""
        prompt = f"""Generate Playwright automation steps for the following task:

Task: {task_description}
{f'Target URL: {target_url}' if target_url else ''}

Create a step-by-step automation script in JSON format.
Include error handling and validation steps.
Be specific with CSS selectors."""

        response = await self.generate(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                automation = json.loads(json_match.group())
            else:
                automation = {
                    "steps": [],
                    "description": task_description,
                    "raw_response": response
                }
        except json.JSONDecodeError:
            automation = {
                "steps": [],
                "description": task_description,
                "raw_response": response
            }
        
        automation["generated_at"] = datetime.utcnow().isoformat()
        automation["task_description"] = task_description
        
        return automation
    
    async def execute_automation(
        self,
        steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute automation steps."""
        if not self.executor:
            return {"success": False, "error": "Playwright not initialized"}
        
        results = []
        success = True
        
        for i, step in enumerate(steps):
            action = step.get("action")
            step_result = {"step": i + 1, "action": action}
            
            try:
                if action == "navigate":
                    result = await self.executor.navigate(step["url"])
                elif action == "click":
                    result = await self.executor.click(step["selector"])
                elif action == "fill":
                    result = await self.executor.fill(step["selector"], step["value"])
                elif action == "wait":
                    result = await self.executor.wait_for_selector(
                        step["selector"],
                        step.get("timeout", 30000)
                    )
                elif action == "screenshot":
                    result = await self.executor.screenshot(step.get("path"))
                elif action == "extract":
                    result = await self.executor.get_text(step["selector"])
                elif action == "evaluate":
                    result = await self.executor.evaluate(step["script"])
                elif action == "get_content":
                    result = await self.executor.get_page_content()
                else:
                    result = {"success": False, "error": f"Unknown action: {action}"}
                
                step_result.update(result)
                
                if not result.get("success", True):
                    success = False
                    if step.get("required", True):
                        break
                        
            except Exception as e:
                step_result["success"] = False
                step_result["error"] = str(e)
                success = False
                if step.get("required", True):
                    break
            
            results.append(step_result)
        
        execution_result = {
            "success": success,
            "steps_executed": len(results),
            "total_steps": len(steps),
            "results": results,
            "executed_at": datetime.utcnow().isoformat()
        }
        
        self.task_history.append(execution_result)
        return execution_result
    
    async def execute_task(
        self,
        task_description: str,
        target_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate and execute automation for a task."""
        # Generate automation
        automation = await self.generate_automation(task_description, target_url)
        
        if not automation.get("steps"):
            return {
                "success": False,
                "error": "Failed to generate automation steps",
                "automation": automation
            }
        
        # Execute automation
        execution = await self.execute_automation(automation["steps"])
        
        return {
            "task_description": task_description,
            "automation": automation,
            "execution": execution,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    async def generate_code(
        self,
        description: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """Generate code for a task."""
        prompt = f"""Generate {language} code for the following task:

Task: {description}

Requirements:
1. Write clean, well-documented code
2. Include error handling
3. Follow best practices for {language}
4. Add comments explaining the logic

Respond with the code in a code block."""

        response = await self.generate(prompt)
        
        # Extract code from response
        code_match = re.search(r'```(?:\w+)?\n([\s\S]*?)```', response)
        code = code_match.group(1) if code_match else response
        
        return {
            "code": code,
            "language": language,
            "description": description,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def scrape_data(
        self,
        url: str,
        selectors: Dict[str, str]
    ) -> Dict[str, Any]:
        """Scrape data from a webpage."""
        if not self.executor:
            return {"success": False, "error": "Playwright not initialized"}
        
        # Navigate to URL
        nav_result = await self.executor.navigate(url)
        if not nav_result.get("success"):
            return nav_result
        
        # Extract data
        data = {}
        for key, selector in selectors.items():
            result = await self.executor.get_text(selector)
            data[key] = result.get("text") if result.get("success") else None
        
        return {
            "success": True,
            "url": url,
            "data": data,
            "scraped_at": datetime.utcnow().isoformat()
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process task request."""
        action = input_data.get("action", "execute")
        
        if action == "generate":
            return await self.generate_automation(
                input_data.get("task", ""),
                input_data.get("url")
            )
        elif action == "execute":
            if "steps" in input_data:
                return await self.execute_automation(input_data["steps"])
            else:
                return await self.execute_task(
                    input_data.get("task", ""),
                    input_data.get("url")
                )
        elif action == "code":
            return await self.generate_code(
                input_data.get("description", ""),
                input_data.get("language", "python")
            )
        elif action == "scrape":
            return await self.scrape_data(
                input_data.get("url", ""),
                input_data.get("selectors", {})
            )
        else:
            return {"error": f"Unknown action: {action}"}
    
    def get_capabilities(self) -> List[str]:
        return [
            "automation_generation",
            "browser_automation",
            "code_generation",
            "web_scraping",
            "form_filling",
            "screenshot_capture",
            "data_extraction",
            "workflow_automation"
        ]
