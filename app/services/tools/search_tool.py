"""Web search tool."""
from typing import Any, Dict
from app.services.tools.base import BaseTool


class SearchTool(BaseTool):
    """Tool for searching the web."""
    
    name = "search_web"
    description = "Search the web for real-time information, news, or facts."
    
    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the internet."
                }
            },
            "required": ["query"]
        }
        
    async def execute(self, query: str, **kwargs) -> Any:
        # For this prototype, we'll return a mock response. 
        # In production, integrate Tavily, DuckDuckGo, or Google Search.
        return f"Mock Search Result for '{query}': AI has made significant advancements recently, particularly in function calling and agentic workflows."
