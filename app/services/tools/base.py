"""Base framework for AI Tool Calling."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Type
from pydantic import BaseModel, Field


class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    name: str
    description: str
    
    @abstractmethod
    def get_parameters_schema(self) -> Dict[str, Any]:
        """Return the JSON schema for the tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with the given parameters."""
        pass
    
    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI tool schema format (used by Groq)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema()
            }
        }
