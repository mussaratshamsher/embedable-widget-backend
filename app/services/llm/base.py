"""Base LLM provider interface."""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        """Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system message to set context
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream response chunks from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system message to set context
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            
        Yields:
            Response text chunks
        """
        pass
    
    @abstractmethod
    async def extract_structured_output(
        self,
        messages: list[dict],
        schema: dict,
        system_prompt: str = None,
    ) -> dict:
        """Extract structured output matching a schema.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: JSON schema for expected output
            system_prompt: Optional system message to set context
            
        Returns:
            Parsed structured output
        """
        pass
