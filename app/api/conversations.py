"""Conversations API endpoints for authenticated users."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.database import get_db
from app.services.conversation_service import ConversationService
from app.services.project_service import ProjectService
from app.services.organization_service import OrganizationService
from app.schemas.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)
from app.core.exceptions import NotFoundException
from app.dependencies.auth import get_current_user


router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


@router.get(
    "",
    response_model=list[ConversationResponse],
    summary="List project conversations",
    description="Get all conversations in a project",
)
async def list_conversations(
    project_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get all conversations in a project.
    
    Query parameters:
    - **project_id**: Project ID (user must have access)
    - **limit**: Number of results (default 50, max 100)
    - **offset**: Results to skip (default 0)
    
    User must be a member of the project's organization.
    """
    try:
        # Get project
        project = await ProjectService.get_project_by_id(project_id, db)
        
        # Verify user has access to organization
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )
        
        conversations = await ConversationService.get_project_conversations(
            project_id, db, limit=limit, offset=offset
        )
        
        return [ConversationResponse.model_validate(conv) for conv in conversations]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details",
    description="Get conversation with message count",
)
async def get_conversation(
    conversation_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details.
    
    User must be a member of the project's organization.
    """
    try:
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify user has access to organization
        project = await ProjectService.get_project_by_id(conversation.project_id, db)
        
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation",
            )
        
        return ConversationDetailResponse.model_validate(conversation)
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
    summary="Get conversation messages",
    description="Get message history from a conversation",
)
async def get_conversation_messages(
    conversation_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """Get message history from a conversation.
    
    Query parameter:
    - **limit**: Maximum number of messages (default 50, max 200)
    
    User must be a member of the project's organization.
    """
    try:
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Verify user has access to organization
        project = await ProjectService.get_project_by_id(conversation.project_id, db)
        
        has_access = await OrganizationService.verify_user_organization_access(
            current_user.id, project.organization_id, db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation",
            )
        
        messages = await ConversationService.get_conversation_messages(
            conversation_id, db, limit=limit
        )
        
        return [MessageResponse.model_validate(msg) for msg in messages]
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
