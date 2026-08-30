"""LLM Factory for managing multiple providers."""
from typing import Any
from app.services.llm.base import LLMProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.core.exceptions import ServiceUnavailableException

class LLMFactory:
    """Factory to retrieve and fallback between LLM providers."""
    
    def __init__(self, primary_llm: str = "groq"):
        self.groq = GroqProvider()
        self.gemini = GeminiProvider()
        
        if primary_llm.lower() == "gemini":
            self.primary_provider = self.gemini
            self.secondary_provider = self.groq
        else:
            self.primary_provider = self.groq
            self.secondary_provider = self.gemini
        
    async def get_response_with_fallback(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: list[dict] = None,
    ) -> Any:
        """Attempt primary, fallback to secondary if service is unavailable."""
        try:
            return await self.primary_provider.generate_response(
                messages, system_prompt, max_tokens, temperature, tools
            )
        except ServiceUnavailableException:
            # Fallback to secondary
            return await self.secondary_provider.generate_response(
                messages, system_prompt, max_tokens, temperature, tools
            )
            
    async def stream_response_with_fallback(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ):
        """Attempt primary, fallback to secondary if service is unavailable."""
        try:
            # We must test the primary before returning a generator
            # The streaming method itself returns an async generator immediately,
            # so error usually happens on first yield. 
            # To properly handle it, we attempt the generator.
            generator = self.primary_provider.stream_response(
                messages, system_prompt, max_tokens, temperature
            )
            
            # Try to get the first chunk to catch rate limit errors early
            # Python async generators don't easily allow peeking, so we just
            # iterate and yield. If it fails on the first element, we fallback.
            
            first_chunk_received = False
            async for chunk in generator:
                first_chunk_received = True
                yield chunk
                
        except ServiceUnavailableException:
            if not first_chunk_received:
                # Fallback to secondary
                generator = self.secondary_provider.stream_response(
                    messages, system_prompt, max_tokens, temperature
                )
                async for chunk in generator:
                    yield chunk
            else:
                # If we already started yielding, we can't easily fallback in the middle
                raise

    async def extract_structured_output_with_fallback(
        self,
        messages: list[dict],
        schema: dict,
        system_prompt: str = None,
    ) -> dict:
        """Attempt primary, fallback to secondary if service is unavailable."""
        try:
            return await self.primary_provider.extract_structured_output(
                messages, schema, system_prompt
            )
        except ServiceUnavailableException:
            # Fallback to secondary
            return await self.secondary_provider.extract_structured_output(
                messages, schema, system_prompt
            )
