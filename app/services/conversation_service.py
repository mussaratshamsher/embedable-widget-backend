"""Conversation service for managing chat sessions."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timezone
import uuid

from app.models import Conversation, Message, Project, Visitor
from app.core.exceptions import NotFoundException, ValidationException
from app.schemas.conversation import ConversationStatus, MessageRole


class ConversationService:
    """Service for conversation operations."""
    
    @staticmethod
    async def create_conversation(
        project_id: uuid.UUID,
        visitor_id: uuid.UUID,
        db: AsyncSession,
    ) -> Conversation:
        """Create a new conversation.
        
        Args:
            project_id: Project ID
            visitor_id: Visitor ID
            db: Database session
            
        Returns:
            Created conversation
            
        Raises:
            NotFoundException: If project or visitor not found
        """
        # Verify project and visitor exist
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundException("Project", project_id)
        
        stmt = select(Visitor).where(Visitor.id == visitor_id)
        result = await db.execute(stmt)
        visitor = result.scalar_one_or_none()
        
        if not visitor:
            raise NotFoundException("Visitor", visitor_id)
        
        # Verify visitor belongs to project
        if visitor.project_id != project_id:
            raise ValidationException("Visitor does not belong to this project")
        
        # Create conversation
        conversation = Conversation(
            id=uuid.uuid4(),
            project_id=project_id,
            visitor_id=visitor_id,
            status=ConversationStatus.ACTIVE,
        )
        
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    async def get_conversation_by_id(
        conversation_id: uuid.UUID,
        db: AsyncSession,
    ) -> Conversation:
        """Get conversation by ID.
        
        Args:
            conversation_id: Conversation ID
            db: Database session
            
        Returns:
            Conversation
            
        Raises:
            NotFoundException: If conversation not found
        """
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)
        
        return conversation
    
    @staticmethod
    async def get_visitor_conversations(
        visitor_id: uuid.UUID,
        project_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[Conversation]:
        """Get all conversations for a visitor in a project.
        
        Args:
            visitor_id: Visitor ID
            project_id: Project ID
            db: Database session
            
        Returns:
            List of conversations
        """
        stmt = (
            select(Conversation)
            .where(
                (Conversation.visitor_id == visitor_id)
                & (Conversation.project_id == project_id)
            )
            .order_by(Conversation.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_project_conversations(
        project_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        """Get conversations in a project with pagination.
        
        Args:
            project_id: Project ID
            db: Database session
            limit: Number of results to return
            offset: Number of results to skip
            
        Returns:
            List of conversations
        """
        stmt = (
            select(Conversation)
            .where(Conversation.project_id == project_id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def close_conversation(
        conversation_id: uuid.UUID,
        db: AsyncSession,
    ) -> Conversation:
        """Close a conversation.
        
        Args:
            conversation_id: Conversation ID
            db: Database session
            
        Returns:
            Updated conversation
        """
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        conversation.status = ConversationStatus.CLOSED
        conversation.closed_at = datetime.now(timezone.utc)
        conversation.updated_at = datetime.now(timezone.utc)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation
    
    @staticmethod
    async def add_message(
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        db: AsyncSession,
    ) -> Message:
        """Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
            db: Database session
            
        Returns:
            Created message
            
        Raises:
            NotFoundException: If conversation not found
        """
        # Verify conversation exists
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        
        # Create message
        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            role=role.value,
            content=content,
        )
        
        # Update conversation updated_at
        conversation.updated_at = datetime.now(timezone.utc)
        
        db.add(message)
        db.add(conversation)
        await db.commit()
        await db.refresh(message)
        
        return message
    
    @staticmethod
    async def get_conversation_messages(
        conversation_id: uuid.UUID,
        db: AsyncSession,
        limit: int = 100,
    ) -> list[Message]:
        """Get messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Maximum number of messages to return
            
        Returns:
            List of messages in chronological order
        """
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()
    
    @staticmethod
    async def get_conversation_context(
        conversation_id: uuid.UUID,
        db: AsyncSession,
        max_messages: int = 20,
    ) -> tuple[Conversation, list[Message]]:
        """Get conversation with its recent messages for context.
        
        Args:
            conversation_id: Conversation ID
            db: Database session
            max_messages: Maximum recent messages to fetch
            
        Returns:
            Tuple of (conversation, messages)
        """
        conversation = await ConversationService.get_conversation_by_id(
            conversation_id, db
        )
        messages = await ConversationService.get_conversation_messages(
            conversation_id, db, limit=max_messages
        )
        return conversation, messages
