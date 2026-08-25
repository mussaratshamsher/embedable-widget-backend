"""Conversation model for chat sessions."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid

from app.db.base import Base


class ConversationStatus(str, PyEnum):
    """Status of a conversation."""
    
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Conversation(Base):
    """Conversation entity - represents a chat session between visitor and AI."""
    
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Track if a lead was generated from this conversation
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    status = Column(
        Enum(ConversationStatus, name="conversation_status", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=ConversationStatus.ACTIVE,
        nullable=False,
    )
    title = Column(String(255))
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return (
            f"<Conversation(id={self.id}, project_id={self.project_id}, "
            f"visitor_id={self.visitor_id})>"
        )
