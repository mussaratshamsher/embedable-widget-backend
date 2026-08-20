"""Widget API endpoints for public widget interactions."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.project_service import ProjectService
from app.services.visitor_service import VisitorService
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    VisitorCreate,
    VisitorResponse,
    ConversationCreate,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreate,
    MessageResponse,
    MessageRole,
)
from app.core.exceptions import NotFoundException, ValidationException, AuthenticationException


router = APIRouter(prefix="/api/widget", tags=["Widget"])


@router.post(
    "/session",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create widget session",
    description="Initialize a visitor session and conversation for the widget",
)
async def create_widget_session(
    session_create: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new visitor session and conversation.
    
    This endpoint is called by the embedded widget to:
    1. Validate the project API key
    2. Create or get a visitor
    3. Create a new conversation
    
    Returns safe identifiers for client-side tracking.
    """
    try:
        # Get project by API key
        project = await ProjectService.get_project_by_api_key(
            session_create.project_api_key, db
        )
        
        if not project:
            raise AuthenticationException("Invalid API key")
        
        if not project.is_active:
            raise ValidationException("Project is not active")
        
        # Get or create visitor
        visitor = await VisitorService.get_visitor_by_identifier(
            session_create.visitor_identifier, db
        )
        
        if visitor is None:
            # Create new visitor with the provided identifier
            visitor = await VisitorService.get_or_create_visitor(
                project.id,
                visitor_identifier=session_create.visitor_identifier,
                db=db
            )
        else:
            # Update last seen
            visitor = await VisitorService.update_visitor_last_seen(visitor.id, db)
        
        # Create conversation
        conversation = await ConversationService.create_conversation(
            project.id, visitor.id, db
        )
        
        return {
            "visitor_id": str(visitor.id),
            "visitor_identifier": visitor.visitor_identifier,
            "conversation_id": str(conversation.id),
            "created_at": conversation.created_at.isoformat(),
        }
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
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
    description="Send a user message to the conversation",
)
async def send_message(
    conversation_id: UUID,
    message_create: MessageCreate,
    project_api_key: str = Query(..., description="Project API key"),
    db: AsyncSession = Depends(get_db),
):
    """Send a user message to a conversation.
    
    Query parameter:
    - **project_api_key**: Project API key for validation
    
    The message will be processed by the AI in a separate endpoint.
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key matches
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
        
        if conversation.status != "active":
            raise ValidationException("Conversation is not active")
        
        # Add user message
        message = await ConversationService.add_message(
            conversation_id,
            MessageRole.USER,
            message_create.content,
            db,
        )
        
        return MessageResponse.model_validate(message)
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


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get conversation messages",
    description="Retrieve message history from a conversation",
)
async def get_messages(
    conversation_id: UUID,
    project_api_key: str = Query(..., description="Project API key"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get message history from a conversation.
    
    Query parameters:
    - **project_api_key**: Project API key for validation
    - **limit**: Maximum number of messages to return (1-100, default 20)
    """
    try:
        # Get conversation
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify project API key matches
        project = await ProjectService.get_project_by_api_key(project_api_key, db)
        
        if not project or project.id != conversation.project_id:
            raise AuthenticationException("Invalid API key for this conversation")
        
        # Get messages
        messages = await ConversationService.get_conversation_messages(
            conversation_id, db, limit=limit
        )
        
        return [MessageResponse.model_validate(msg) for msg in messages]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
    except AuthenticationException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        )
