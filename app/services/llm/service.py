"""LLM service for high-level AI interactions."""
from typing import AsyncIterator
from app.services.llm.factory import LLMFactory
from app.core.exceptions import ValidationException


from app.services.tools.registry import get_all_tools, get_tool
import json

class LLMService:
    """Service for managing LLM interactions."""
    
    def __init__(self, primary_llm: str = "groq"):
        """Initialize LLM service with LLMFactory."""
        self.factory = LLMFactory(primary_llm=primary_llm)
    
    async def get_ai_response(
        self,
        conversation_history: list[dict],
        project_ai_instructions: str = None,
        max_tokens: int = 500,
        enabled_tools: list[str] = None,
    ) -> str:
        """Get AI response for a conversation.
        
        Args:
            conversation_history: List of {role, content} dicts
            project_ai_instructions: Custom AI instructions from project
            max_tokens: Maximum tokens in response
            enabled_tools: List of enabled tool names for this project
            
        Returns:
            AI response text
        """
        system_prompt = self._build_system_prompt(project_ai_instructions)
        
        # Prepare tools
        all_tools = get_all_tools()
        if enabled_tools is not None:
            all_tools = [t for t in all_tools if t.name in enabled_tools]
            
        openai_tools = [t.to_openai_schema() for t in all_tools] if all_tools else None
        
        response = await self.factory.get_response_with_fallback(
            messages=conversation_history,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=0.7,
            tools=openai_tools,
        )
        
        # If response is a tuple, it means tools were called
        if isinstance(response, tuple):
            text_response, tool_calls = response
            
            # Execute tools
            tool_messages = []
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                args = json.loads(tc["function"]["arguments"])
                try:
                    tool_instance = get_tool(tool_name)
                    result = await tool_instance.execute(**args)
                    # Convert dicts/objects to string for the LLM
                    if not isinstance(result, str):
                        result = json.dumps(result)
                except Exception as e:
                    result = f"Error executing tool {tool_name}: {str(e)}"
                    
                tool_messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tc["id"],
                    "name": tool_name
                })
                
            # Append tool calls to history
            history_with_tools = conversation_history.copy()
            # Note: A real implementation would also append the assistant's tool call message
            # For simplicity with some providers, we'll just add the assistant message and tool responses
            history_with_tools.append({
                "role": "assistant",
                "content": text_response or "",
                "tool_calls": tool_calls
            })
            history_with_tools.extend(tool_messages)
            
            # Request follow-up response
            final_response = await self.factory.get_response_with_fallback(
                messages=history_with_tools,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=0.7,
                # We don't pass tools here to prevent infinite loops for now
            )
            # if it's a tuple again somehow (shouldn't be), just return text
            if isinstance(final_response, tuple):
                return final_response[0]
            return final_response
            
        return response
    
    async def stream_ai_response(
        self,
        conversation_history: list[dict],
        project_ai_instructions: str = None,
        max_tokens: int = 500,
        enabled_tools: list[str] = None,
    ) -> AsyncIterator[str]:
        """Stream AI response for a conversation.
        
        Note: Currently streaming does not support tool execution midway in this simple setup.
        We will just use get_ai_response under the hood if tools are enabled, and yield it.
        Otherwise, stream normally.
        """
        system_prompt = self._build_system_prompt(project_ai_instructions)
        
        if enabled_tools:
            # If tools are enabled, we do not stream the first pass because we need to parse JSON arguments
            final_text = await self.get_ai_response(
                conversation_history, project_ai_instructions, max_tokens, enabled_tools
            )
            yield final_text
            return
            
        async for chunk in self.factory.stream_response_with_fallback(
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
        
        return await self.factory.extract_structured_output_with_fallback(
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
Ask clarifying questions when needed to better understand their needs.

CRITICAL INSTRUCTIONS:
- Keep your responses VERY brief and conversational, exactly like a human chatting in a widget (max 2-3 short sentences).
- NEVER output internal thought processes, planning steps, or <think> tags. Give only the final response.
- Do NOT output long checklists, tables, or essays. 
- If you need more information to complete a task (like scheduling a meeting), ask only 1 or 2 most relevant questions at a time."""
        
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
