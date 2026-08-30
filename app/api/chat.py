"""Chat API endpoints with AI responses."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import json

from app.db.database import get_db
from app.api.widget import verify_domain_access
from app.services.conversation_service import ConversationService
from app.services.project_service import ProjectService
from app.services.visitor_service import VisitorService
from app.services.llm import LLMService
from app.schemas.chat import ChatMessageRequest, ChatResponse, AIQualificationResponse
from app.schemas.conversation import MessageRole
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    AuthenticationException,
)


router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "/send",
    summary="Send message to AI",
    description="Send user message and get AI response via Server-Sent Events",
)
async def send_chat_message(
    request: Request,
    conversation_id: UUID,
    message_request: ChatMessageRequest,
    project_api_key: str = Query(..., description="Project API key"),
    db: AsyncSession = Depends(get_db),
):
    """Send a message and get AI response via Server-Sent Events (SSE).
    
    Query parameters:
    - **project_api_key**: Project API key for validation
    
    Response uses Server-Sent Events format. Client should listen to event stream.
    Events are JSON objects with format: {"chunk": "...", "is_final": false}
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
            
        verify_domain_access(request, project)
        
        if conversation.status != "active":
            raise ValidationException("Conversation is not active")
        
        # Save user message
        user_message = await ConversationService.add_message(
            conversation_id,
            MessageRole.USER,
            message_request.content,
            db,
        )
        
        # Get conversation history for context
        _, messages = await ConversationService.get_conversation_context(
            conversation_id, db, max_messages=10
        )
        
        # Format messages for LLM (exclude user message we just added if not needed)
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Initialize LLMService with project preference
        llm_service = LLMService(primary_llm=project.primary_llm)
        
        # Generate streaming response
        async def event_generator():
            """Generate SSE events with AI response chunks."""
            full_response = ""
            
            try:
                # Stream from LLM
                async for chunk in llm_service.stream_ai_response(
                    conversation_history=formatted_messages,
                    project_ai_instructions=project.ai_instructions,
                    enabled_tools=project.enabled_tools,
                ):
                    full_response += chunk
                    
                    # Send chunk as SSE event
                    event_data = {
                        "chunk": chunk,
                        "is_final": False,
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Save full response as assistant message
                assistant_message = await ConversationService.add_message(
                    conversation_id,
                    MessageRole.ASSISTANT,
                    full_response,
                    db,
                )
                
                # Send final event
                final_event = {
                    "chunk": "",
                    "is_final": True,
                    "message_id": str(assistant_message.id),
                }
                yield f"data: {json.dumps(final_event)}\n\n"
                
            except Exception as e:
                # Send error event
                error_event = {
                    "error": str(e),
                    "is_final": True,
                }
                yield f"data: {json.dumps(error_event)}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    
    except (NotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )


@router.post(
    "/qualify",
    response_model=AIQualificationResponse,
    summary="Qualify lead from conversation",
    description="Extract and qualify lead information from conversation",
)
async def qualify_lead(
    request: Request,
    conversation_id: UUID,
    project_api_key: str = Query(..., description="Project API key"),
    db: AsyncSession = Depends(get_db),
):
    """Analyze conversation and extract lead qualification data.
    
    Query parameters:
    - **project_api_key**: Project API key for validation
    
    Uses AI to extract contact info and qualification score from conversation.
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
            
        verify_domain_access(request, project)
        
        # Get conversation messages for analysis
        _, messages = await ConversationService.get_conversation_context(
            conversation_id, db, max_messages=20
        )
        
        if not messages:
            return AIQualificationResponse()
        
        # Format messages for LLM
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # Extract lead data using LLM
        llm_service = LLMService(primary_llm=project.primary_llm)
        lead_data = await llm_service.extract_lead_data(
            conversation_history=formatted_messages,
        )
        
        # Save lead to database
        from app.services.lead_service import LeadService
        from app.services.webhook_service import WebhookService
        import asyncio
        
        # We only save if there's actually some data extracted (e.g. name or email)
        # But for now, let's save the qualification data regardless or if it's qualified
        if lead_data.get("name") or lead_data.get("email") or lead_data.get("qualified"):
            saved_lead = await LeadService.create_or_update_lead(
                project_id=project.id,
                conversation_id=conversation_id,
                visitor_id=conversation.visitor_id,
                lead_data=lead_data,
                db=db,
            )
            
            # Update the conversation to reference the lead_id
            conversation.lead_id = saved_lead.id
            db.add(conversation)
            await db.commit()
            
            # Fire webhook in background
            # We must use a new session for the background task to avoid DB session conflicts
            # Or just fire HTTP requests which doesn't need DB if we fetch the URLs now
            
            # Let's fetch webhooks now using the current DB session
            webhooks = await WebhookService.get_webhooks_by_project(project.id, db)
            active_webhooks = [w for w in webhooks if w.is_active]
            
            if active_webhooks:
                # Simple fire-and-forget for httpx
                import httpx
                import logging
                logger = logging.getLogger(__name__)
                
                async def fire_webhooks(webhooks_list, data):
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        for webhook in webhooks_list:
                            try:
                                logger.info(f"Dispatching lead to webhook {webhook.url}")
                                await client.post(webhook.url, json={"event": "lead.qualified", "data": data})
                            except Exception as e:
                                logger.error(f"Webhook failed for {webhook.url}: {str(e)}")
                                
                # Create a background task
                asyncio.create_task(fire_webhooks(active_webhooks, lead_data))
        
        return AIQualificationResponse(**lead_data)
    
    except (NotFoundException, ValidationException) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
    except Exception as e:
        # Return empty qualification on extraction failure
        return AIQualificationResponse()
