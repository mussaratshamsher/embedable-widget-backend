"""Lead model for captured leads."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSON
from datetime import datetime, timezone
import uuid

from app.db.base import Base


class Lead(Base):
    """Lead entity - represents a qualified lead extracted from conversation."""
    
    __tablename__ = "leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Lead contact information
    name = Column(String(255))
    email = Column(String(255), index=True)
    phone = Column(String(20))
    company = Column(String(255))
    # Lead classification
    status = Column(String(50), default="new", nullable=False, index=True)
    # new, contacted, qualified, converted, lost
    project_type = Column(String(100))
    budget = Column(String(50))
    timeline = Column(String(100))
    # AI qualification score (0-100)
    intent_score = Column(Integer, default=0)
    is_qualified = Column(Boolean, default=False, nullable=False)
    # Raw extracted data from LLM
    extraction_data = Column(JSON, default={}, nullable=False)
    # Custom lead fields
    extra_metadata = Column("metadata", JSON, default={}, nullable=False)
    notes = Column(Text)
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
    last_contacted_at = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Lead(id={self.id}, email={self.email}, status={self.status})>"
