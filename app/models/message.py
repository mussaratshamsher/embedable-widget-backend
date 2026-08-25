"""Message model for conversation messages."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid

from app.db.base import Base


class MessageRole(str, PyEnum):
    """Role of message sender."""
    
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(Base):
    """Message entity - represents a single message in a conversation."""
    
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        Enum(MessageRole, name="message_role", create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )  # user, assistant, system
    content = Column(Text, nullable=False)
    # Track if this message triggered lead extraction
    led_to_lead = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    tokens_used = Column(String(50))  # For tracking LLM usage
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    
    def __repr__(self):
        return (
            f"<Message(id={self.id}, conversation_id={self.conversation_id}, "
            f"role={self.role})>"
        )
