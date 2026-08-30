"""Gemini API provider implementation (via native Google GenAI SDK)."""
import json
from typing import AsyncIterator
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableException, ValidationException
from app.services.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini API LLM provider (using google-genai)."""
    
    def __init__(self):
        """Initialize Google GenAI client."""
        key = getattr(settings, "gemini_api_key", "")
        self.client = genai.Client(api_key=key)
        # Standard fast model
        self.model_name = "gemini-1.5-flash"
    
    def _convert_messages(self, messages: list[dict], system_prompt: str = None) -> list[types.Content]:
        """Convert standard messages to Gemini format."""
        gemini_messages = []
        
        # If there's a system prompt, we can prepend it as a user message,
        # or handle it via system_instruction in config.
        # But we'll format conversation history here.
        for msg in messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            gemini_messages.append(
                types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
            )
        return gemini_messages

    async def generate_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        tools: list[dict] = None,
    ) -> str | tuple[str, list[dict]]:
        try:
            config_kwargs = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if system_prompt:
                config_kwargs["system_instruction"] = system_prompt
                
            config = types.GenerateContentConfig(**config_kwargs)
            
            formatted_messages = self._convert_messages(messages)

            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=formatted_messages,
                config=config,
            )
            return response.text
        except Exception as e:
            if "429" in str(e):
                raise ServiceUnavailableException("Gemini API - Rate limited")
            raise ServiceUnavailableException(f"Gemini API Error: {str(e)}")
            
    async def stream_response(
        self,
        messages: list[dict],
        system_prompt: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        try:
            config_kwargs = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if system_prompt:
                config_kwargs["system_instruction"] = system_prompt
                
            config = types.GenerateContentConfig(**config_kwargs)
            
            formatted_messages = self._convert_messages(messages)

            stream = await self.client.aio.models.generate_content_stream(
                model=self.model_name,
                contents=formatted_messages,
                config=config,
            )
            
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            if "429" in str(e):
                raise ServiceUnavailableException("Gemini API - Rate limited")
            raise ServiceUnavailableException(f"Gemini API Error: {str(e)}")

    async def extract_structured_output(
        self,
        messages: list[dict],
        schema: dict,
        system_prompt: str = None,
    ) -> dict:
        try:
            config_kwargs = {
                "temperature": 0.2,
                "max_output_tokens": 1000,
                "response_mime_type": "application/json",
            }
            
            # Combine system prompt and schema request
            full_system = f"{system_prompt or ''}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema)}"
            config_kwargs["system_instruction"] = full_system
            
            config = types.GenerateContentConfig(**config_kwargs)
            formatted_messages = self._convert_messages(messages)
            
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=formatted_messages,
                config=config,
            )
            
            response_text = response.text
            
            # Simple JSON extraction
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            raise ValidationException("Failed to parse structured output from LLM")
        except Exception as e:
            raise ValidationException(f"Structured output extraction failed: {str(e)}")
