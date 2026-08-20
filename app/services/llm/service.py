"""LLM service for high-level AI interactions."""
from typing import AsyncIterator
from app.services.llm.groq_provider import GroqProvider
from app.core.exceptions import ValidationException


class LLMService:
    """Service for managing LLM interactions."""
    
    def __init__(self):
        """Initialize LLM service with Groq provider."""
        self.provider = GroqProvider()
    
    async def get_ai_response(
        self,
        conversation_history: list[dict],
        project_ai_instructions: str = None,
        max_tokens: int = 500,
    ) -> str:
        """Get AI response for a conversation.
        
        Args:
            conversation_history: List of {role, content} dicts
            project_ai_instructions: Custom AI instructions from project
            max_tokens: Maximum tokens in response
            
        Returns:
            AI response text
        """
        # Build system prompt from instructions
        system_prompt = self._build_system_prompt(project_ai_instructions)
        
        return await self.provider.generate_response(
            messages=conversation_history,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.7,
        )
    
    async def stream_ai_response(
        self,
        conversation_history: list[dict],
        project_ai_instructions: str = None,
        max_tokens: int = 500,
    ) -> AsyncIterator[str]:
        """Stream AI response for a conversation.
        
        Args:
            conversation_history: List of {role, content} dicts
            project_ai_instructions: Custom AI instructions from project
            max_tokens: Maximum tokens in response
            
        Yields:
            Response text chunks
        """
        system_prompt = self._build_system_prompt(project_ai_instructions)
        
        async for chunk in self.provider.stream_response(
            messages=conversation_history,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.7,
        ):
            yield chunk
    
    async def extract_lead_data(
        self,
        conversation_history: list[dict],
        lead_extraction_schema: dict = None,
    ) -> dict:
        """Extract structured lead data from conversation.
        
        Args:
            conversation_history: List of {role, content} dicts
            lead_extraction_schema: Custom schema for lead extraction
            
        Returns:
            Extracted lead data
        """
        schema = lead_extraction_schema or self._get_default_lead_schema()
        
        system_prompt = """You are a sales lead extraction specialist. 
Extract contact and qualification information from the conversation.
Return ONLY valid JSON matching the provided schema."""
        
        return await self.provider.extract_structured_output(
            messages=conversation_history,
            schema=schema,
            system_prompt=system_prompt,
        )
    
    @staticmethod
    def _build_system_prompt(custom_instructions: str = None) -> str:
        """Build system prompt for AI interactions.
        
        Args:
            custom_instructions: Optional custom instructions from project
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful AI assistant for a business.
Your role is to help visitors with their inquiries and qualify them as potential leads.
Be professional, friendly, and helpful.
Ask clarifying questions when needed to better understand their needs."""
        
        if custom_instructions:
            return f"{base_prompt}\n\nAdditional instructions:\n{custom_instructions}"
        
        return base_prompt
    
    @staticmethod
    def _get_default_lead_schema() -> dict:
        """Get default lead extraction schema.
        
        Returns:
            JSON schema for lead extraction
        """
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Contact name",
                },
                "email": {
                    "type": "string",
                    "description": "Email address",
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number",
                },
                "company": {
                    "type": "string",
                    "description": "Company name",
                },
                "project_type": {
                    "type": "string",
                    "description": "Type of project or service interested in",
                },
                "budget": {
                    "type": "string",
                    "description": "Budget range if mentioned",
                },
                "timeline": {
                    "type": "string",
                    "description": "Project timeline if mentioned",
                },
                "intent_score": {
                    "type": "integer",
                    "description": "Lead qualification score (0-100)",
                    "minimum": 0,
                    "maximum": 100,
                },
                "qualified": {
                    "type": "boolean",
                    "description": "Whether this is a qualified lead",
                },
            },
            "required": ["intent_score", "qualified"],
        }
