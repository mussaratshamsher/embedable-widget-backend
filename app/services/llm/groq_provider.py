"""Groq API provider implementation."""
import json
from typing import AsyncIterator, Any
from groq import Groq
import asyncio

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException, ValidationException
from app.services.llm.base import LLMProvider


class GroqProvider(LLMProvider):
    """Groq API LLM provider."""
    
    def __init__(self):
        """Initialize Groq client."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "qwen/qwen3.6-27b"
    
    async def generate_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: list[dict] = None,
    ) -> str | tuple[str, list[dict]]:
        """Generate a response from Groq.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system message to set context
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            tools: Optional list of tools formatted for OpenAI/Groq schema
            
        Returns:
            Generated response text, or if tools were called, a tuple of (text, tool_calls)
            
        Raises:
            ServiceUnavailableException: If Groq API fails
        """
        try:
            # Prepare messages with system prompt
            formatted_messages = []
            
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt,
                })
            
            formatted_messages.extend(messages)
            
            # Call Groq API
            response = await asyncio.to_thread(
                self._call_groq_api,
                formatted_messages,
                max_tokens,
                temperature,
                False,  # not streaming
                tools,
            )
            
            if not response:
                raise ValidationException("Empty response from Groq")
            
            # response is a tuple of (text, tool_calls) if tool_calls exist, else just string
            return response
        except Exception as e:
            if "429" in str(e):
                raise ServiceUnavailableException("Groq API - Rate limited")
            elif "503" in str(e):
                raise ServiceUnavailableException("Groq API - Service unavailable")
            else:
                raise ServiceUnavailableException("Groq API")
    
    async def stream_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream response chunks from Groq.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system message to set context
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            
        Yields:
            Response text chunks
        """
        try:
            # Prepare messages with system prompt
            formatted_messages = []
            
            if system_prompt:
                formatted_messages.append({
                    "role": "system",
                    "content": system_prompt,
                })
            
            formatted_messages.extend(messages)
            
            # Stream from Groq API
            async for chunk in self._stream_groq_api(
                formatted_messages,
                max_tokens,
                temperature,
            ):
                yield chunk
        except Exception as e:
            if "429" in str(e):
                raise ServiceUnavailableException("Groq API - Rate limited")
            elif "503" in str(e):
                raise ServiceUnavailableException("Groq API - Service unavailable")
            else:
                raise ServiceUnavailableException("Groq API")
    
    async def extract_structured_output(
        self,
        messages: list[dict],
        schema: dict,
        system_prompt: str = None,
    ) -> dict:
        """Extract structured output from Groq using JSON mode.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            schema: JSON schema for expected output
            system_prompt: Optional system message to set context
            
        Returns:
            Parsed structured output
            
        Raises:
            ValidationException: If output doesn't match schema
        """
        try:
            # Add schema to system prompt
            schema_prompt = f"{system_prompt or ''}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"
            
            # Get structured response
            response_text = await self.generate_response(
                messages,
                system_prompt=schema_prompt,
                max_tokens=1000,
                temperature=0.2,  # Lower temperature for structured output
            )
            
            # Parse JSON from response
            parsed = self._extract_json(response_text)
            
            if not parsed:
                raise ValidationException("Failed to parse structured output from LLM")
            
            return parsed
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Structured output extraction failed: {str(e)}")
    
    def _call_groq_api(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
        stream: bool,
        tools: list[dict] = None,
    ) -> Any:
        """Call Groq API synchronously (to be run in thread pool).
        
        Args:
            messages: Formatted messages
            max_tokens: Maximum tokens
            temperature: Temperature
            stream: Whether to stream
            tools: Optional tools list
            
        Returns:
            Response text or empty if stream=True
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        
        if stream:
            return ""
        else:
            msg = response.choices[0].message
            if getattr(msg, "tool_calls", None):
                # Return tuple of text and tool calls
                tool_calls = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } 
                    for tc in msg.tool_calls
                ]
                return (msg.content or "", tool_calls)
            return msg.content or ""
    
    async def _stream_groq_api(
        self,
        messages: list[dict],
        max_tokens: int,
        temperature: float,
    ) -> AsyncIterator[str]:
        """Stream from Groq API.
        
        Args:
            messages: Formatted messages
            max_tokens: Maximum tokens
            temperature: Temperature
            
        Yields:
            Response chunks
        """
        # Run in thread pool since Groq client is synchronous
        loop = asyncio.get_event_loop()
        
        def get_stream():
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
        
        stream = await loop.run_in_executor(None, get_stream)
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract JSON object from text.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Parsed JSON dict or None
        """
        try:
            # Try parsing entire text
            return json.loads(text)
        except json.JSONDecodeError:
            # Try finding JSON in text
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        return None
